from __future__ import annotations

import argparse
import json
import struct
import tempfile
import zlib
from pathlib import Path
from typing import Any

from validate_wechat_article import validate_article


REVIEW_KEYS = {
    "facts",
    "source_traceability",
    "sensitivity",
    "compliance",
    "title_body_cover",
    "output_schema",
}
SENSITIVE_KEYS = {"appid", "app_secret", "secret", "token", "cookie", "access_token"}


def find_sensitive_keys(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key.lower() in SENSITIVE_KEYS:
                findings.append(child_path)
            findings.extend(find_sensitive_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(find_sensitive_keys(child, f"{path}[{index}]"))
    return findings


def png_dimensions(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", header[16:24])


def is_valid_source_ref(value: Any) -> bool:
    if (
        not isinstance(value, str)
        or not value.startswith("[[300-Wiki/")
        or not value.endswith("]]")
        or "|" in value
    ):
        return False
    return any(
        value.startswith(f"[[300-Wiki/{directory}/")
        for directory in ("01-Professional", "02-General", "03-Synthesis", "04-Sources")
    )


def validate_claim_evidence(value: Any, source_refs: list[str]) -> tuple[list[str], set[int]]:
    errors: list[str] = []
    verified_lines: set[int] = set()
    if not isinstance(value, list):
        return ["claim_evidence must be a list"], verified_lines

    for index, item in enumerate(value):
        prefix = f"claim_evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue

        line = item.get("line")
        if not isinstance(line, int) or isinstance(line, bool) or line < 1:
            errors.append(f"{prefix}.line must be a positive integer")
        claim = item.get("claim")
        if not isinstance(claim, str) or not claim.strip():
            errors.append(f"{prefix}.claim must be a non-empty string")
        source_ref = item.get("source_ref")
        if not is_valid_source_ref(source_ref):
            errors.append(f"{prefix}.source_ref must be a valid 300-Wiki link without an alias")
        elif source_ref not in source_refs:
            errors.append(f"{prefix}.source_ref must also appear in source_refs")
        support = item.get("support")
        if not isinstance(support, str) or not support.strip():
            errors.append(f"{prefix}.support must be a non-empty string")
        if item.get("status") != "verified":
            errors.append(f"{prefix}.status must be verified")
        elif isinstance(line, int) and not isinstance(line, bool) and line >= 1:
            verified_lines.add(line)

    return errors, verified_lines


def validate_manifest(data: Any, root: Path, check_files: bool = True) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["manifest root must be an object"]

    required = {
        "schema_version",
        "status",
        "output_profile",
        "title",
        "summary",
        "body_path",
        "cover",
        "source_refs",
        "claim_evidence",
        "review",
        "publisher",
    }
    for key in sorted(required - data.keys()):
        errors.append(f"missing required field: {key}")

    if data.get("schema_version") != 2:
        errors.append("schema_version must be 2")
    if data.get("status") != "ready":
        errors.append("status must be ready")
    if data.get("output_profile") != "publish_article":
        errors.append("output_profile must be publish_article")
    if not isinstance(data.get("title"), str) or not data.get("title", "").strip():
        errors.append("title must be a non-empty string")
    if not isinstance(data.get("summary"), str) or not data.get("summary", "").strip():
        errors.append("summary must be a non-empty string")

    source_refs = data.get("source_refs")
    if not isinstance(source_refs, list) or not source_refs:
        errors.append("source_refs must be a non-empty list")
    elif not all(is_valid_source_ref(item) for item in source_refs):
        errors.append("source_refs must contain only valid 300-Wiki links without aliases")

    evidence_errors, verified_claim_lines = validate_claim_evidence(
        data.get("claim_evidence"), source_refs if isinstance(source_refs, list) else []
    )
    errors.extend(evidence_errors)

    review = data.get("review")
    if not isinstance(review, dict):
        errors.append("review must be an object")
    else:
        missing_reviews = REVIEW_KEYS - review.keys()
        if missing_reviews:
            errors.append(f"review is missing: {', '.join(sorted(missing_reviews))}")
        failed_reviews = [key for key in REVIEW_KEYS if review.get(key) != "pass"]
        if failed_reviews:
            errors.append(f"review checks must pass: {', '.join(sorted(failed_reviews))}")

    publisher = data.get("publisher")
    if not isinstance(publisher, dict):
        errors.append("publisher must be an object")
    else:
        if publisher.get("mode") != "manual":
            errors.append("publisher.mode must be manual")
        if publisher.get("enabled") is not False:
            errors.append("publisher.enabled must be false")
        if publisher.get("action") != "none":
            errors.append("publisher.action must be none")
        if publisher.get("adapter") is not None:
            errors.append("publisher.adapter must be null while publishing is disabled")

    for location in find_sensitive_keys(data):
        errors.append(f"credential-like field is forbidden: {location}")

    body_path = data.get("body_path")
    cover = data.get("cover")
    if not isinstance(body_path, str) or not body_path.strip():
        errors.append("body_path must be a non-empty relative path")
    elif Path(body_path).is_absolute() or ".." in Path(body_path).parts:
        errors.append("body_path must stay within the vault root")
    elif check_files:
        body_file = root / body_path
        if not body_file.is_file():
            errors.append(f"body file not found: {body_path}")
        else:
            article_result = validate_article(body_file)
            for item in article_result["fatal"]:
                errors.append(f"body gate [{item['code']}] line {item['line']}: {item['message']}")
            for item in article_result["technical_claims"]:
                if item["line"] not in verified_claim_lines:
                    errors.append(
                        f"claim_evidence missing for technical claim at line {item['line']}: {item['text']}"
                    )

    if not isinstance(cover, dict):
        errors.append("cover must be an object")
    else:
        if cover.get("width") != 2350 or cover.get("height") != 1000:
            errors.append("cover dimensions must be declared as 2350 x 1000")
        cover_path = cover.get("path")
        if not isinstance(cover_path, str) or not cover_path.strip():
            errors.append("cover.path must be a non-empty relative path")
        elif Path(cover_path).is_absolute() or ".." in Path(cover_path).parts:
            errors.append("cover.path must stay within the vault root")
        elif check_files:
            cover_file = root / cover_path
            if not cover_file.is_file():
                errors.append(f"cover file not found: {cover_path}")
            else:
                dimensions = png_dimensions(cover_file)
                if dimensions != (2350, 1000):
                    errors.append(f"cover PNG dimensions must be 2350 x 1000, got {dimensions}")

    return errors


def write_test_png(path: Path, width: int, height: int) -> None:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))

    raw = b"".join(b"\x00" + (b"\x00\x00\x00" * width) for _ in range(height))
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def sample_manifest() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "status": "ready",
        "output_profile": "publish_article",
        "title": "Test title",
        "summary": "Test summary",
        "body_path": "article.md",
        "cover": {"path": "cover.png", "width": 2350, "height": 1000},
        "source_refs": ["[[300-Wiki/01-Professional/Test]]"],
        "claim_evidence": [],
        "review": {key: "pass" for key in REVIEW_KEYS},
        "publisher": {"mode": "manual", "enabled": False, "adapter": None, "action": "none"},
    }


def self_test() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / "article.md").write_text("test", encoding="utf-8")
        write_test_png(root / "cover.png", 2350, 1000)

        valid = sample_manifest()
        assert validate_manifest(valid, root) == []

        invalid_status = sample_manifest()
        invalid_status["status"] = "draft"
        assert "status must be ready" in validate_manifest(invalid_status, root)

        invalid_source = sample_manifest()
        invalid_source["source_refs"] = ["https://example.com"]
        assert any("source_refs" in item for item in validate_manifest(invalid_source, root))

        invalid_alias = sample_manifest()
        invalid_alias["source_refs"] = ["[[300-Wiki/01-Professional/Test|Alias]]"]
        assert any("source_refs" in item for item in validate_manifest(invalid_alias, root))

        enabled_publisher = sample_manifest()
        enabled_publisher["publisher"]["enabled"] = True
        assert "publisher.enabled must be false" in validate_manifest(enabled_publisher, root)

        credential_leak = sample_manifest()
        credential_leak["publisher"]["app_secret"] = "do-not-store"
        assert any("credential-like field" in item for item in validate_manifest(credential_leak, root))

        path_escape = sample_manifest()
        path_escape["body_path"] = "../article.md"
        assert "body_path must stay within the vault root" in validate_manifest(path_escape, root)

        (root / "article.md").write_text("联系电话：123456", encoding="utf-8")
        assert any("body gate [contact_info]" in item for item in validate_manifest(sample_manifest(), root))

        (root / "article.md").write_text("监测值超过 10 mm 必须停工。", encoding="utf-8")
        technical_claim = sample_manifest()
        assert any("claim_evidence missing" in item for item in validate_manifest(technical_claim, root))

        technical_claim["claim_evidence"] = [{
            "line": 1,
            "claim": "监测值超过 10 mm 必须停工",
            "source_ref": "[[300-Wiki/01-Professional/Test]]",
            "support": "test source support",
            "status": "verified",
        }]
        assert validate_manifest(technical_claim, root) == []

    print("self-test: 10 passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a WeChat publish manifest.")
    parser.add_argument("manifest", nargs="?", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.manifest is None:
        parser.error("manifest is required unless --self-test is used")

    data = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    errors = validate_manifest(data, args.root.resolve())
    result = {"manifest": str(args.manifest), "fatal": len(errors), "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
