from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


FATAL_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "contact_info",
        re.compile(r"微信号|联系微信|加(?:我|小编)?微信|手机号|联系电话|电话\s*[:：]"),
        "公开正文包含联系方式",
    ),
    (
        "offsite_redirect",
        re.compile(
            r"扫码|二维码|回复.{0,10}(?:领取|获取)|私信.{0,10}(?:领取|获取)|"
            r"点击.{0,10}(?:链接|名片)|移步.{0,10}(?:公众号|视频号|小程序)"
        ),
        "公开正文包含离页导流动作",
    ),
    (
        "cross_content_prompt",
        re.compile(r"建议先看|再回来(?:读|看)"),
        "公开正文包含跨内容跳转提示",
    ),
    (
        "obsidian_wikilink",
        re.compile(r"\[\[[^\]]+\]\]"),
        "公开正文包含 Obsidian 双链",
    ),
    (
        "external_link",
        re.compile(r"https?://"),
        "公开正文包含外部链接",
    ),
    (
        "placeholder",
        re.compile(r"\bTODO\b|\bTBD\b|待补充|待核实|待确认|占位符", re.IGNORECASE),
        "公开正文包含占位符或待办标记",
    ),
)

TECHNICAL_NUMBER = re.compile(
    r"(?:\d+(?:\.\d+)?\s*(?:%|％|天|小时|分钟|次|m|mm|cm|kN|MPa|kPa|级))",
    re.IGNORECASE,
)
TECHNICAL_ACTION = re.compile(
    r"必须|应当|不得|立即|停止|停工|撤出|启动|阈值|预警|超限|超过|"
    r"不低于|不少于|至少|最多|严禁"
)


def ensure_utf8_stdio() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def article_body_lines(text: str) -> Iterable[tuple[int, str]]:
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                start = index + 1
                break

    in_fence = False
    for index in range(start, len(lines)):
        line = lines[index]
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield index + 1, line


def issue(code: str, line: int, message: str, text: str) -> dict[str, Any]:
    return {
        "code": code,
        "line": line,
        "message": message,
        "text": text.strip(),
    }


def scan_article_text(text: str) -> dict[str, list[dict[str, Any]]]:
    fatal: list[dict[str, Any]] = []
    warning: list[dict[str, Any]] = []
    technical_claims: list[dict[str, Any]] = []

    for line_number, line in article_body_lines(text):
        if re.match(r"^#\s+", line):
            fatal.append(issue("h1_heading", line_number, "公众号正文不得使用一级标题", line))

        for code, pattern, message in FATAL_PATTERNS:
            if pattern.search(line):
                fatal.append(issue(code, line_number, message, line))

        if TECHNICAL_NUMBER.search(line) and TECHNICAL_ACTION.search(line):
            claim = issue(
                "technical_claim",
                line_number,
                "专业数字或行动阈值需要 claim_evidence",
                line,
            )
            warning.append(claim)
            technical_claims.append(claim)

    return {
        "fatal": fatal,
        "warning": warning,
        "technical_claims": technical_claims,
    }


def validate_article(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    result: dict[str, Any] = {"file": str(path)}
    result.update(scan_article_text(text))
    return result


def main() -> int:
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Validate a public WeChat article body")
    parser.add_argument("article", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="专业数字 claim 未提供发布清单证据时也返回非零；发布清单校验时由 claim_evidence 处理",
    )
    args = parser.parse_args()

    if not args.article.is_file():
        print(json.dumps({"file": str(args.article), "fatal": 1, "errors": ["article not found"]}, ensure_ascii=False))
        return 2

    result = validate_article(args.article)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["fatal"]:
        return 1
    if args.strict and result["warning"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
