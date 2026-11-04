from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import validate_publish_manifest as manifest_validator
import validate_wechat_article as article_validator


SOURCE_REF = "[[300-Wiki/04-Sources/Source-GeoE-Test]]"


class WeChatArticleValidatorTests(unittest.TestCase):
    def test_rejects_contact_and_cross_content_prompt(self) -> None:
        text = """---
output_profile: publish_article
source_refs:
  - "[[300-Wiki/04-Sources/Source-GeoE-Test]]"
status: reviewing
---

## 正文

如有疑问请加小编微信号：YSN_GEO。
建议先看上一篇文章，再回来读这篇。
"""

        result = article_validator.scan_article_text(text)
        codes = {issue["code"] for issue in result["fatal"]}

        self.assertIn("contact_info", codes)
        self.assertIn("cross_content_prompt", codes)

    def test_allows_neutral_submission_footer_contact(self) -> None:
        clean = """---
output_profile: publish_article
source_refs:
  - "[[300-Wiki/04-Sources/Source-GeoE-Test]]"
status: reviewing
---

## 正文

**欢迎投稿与交流**
> **投稿邮箱：** test@example.com
> **小编微信：** YSN_GEO
"""

        clean_result = article_validator.scan_article_text(clean)

        self.assertEqual([], clean_result["fatal"])

    def test_rejects_explicit_wechat_add_prompt(self) -> None:
        text = """---
output_profile: publish_article
source_refs:
  - "[[300-Wiki/04-Sources/Source-GeoE-Test]]"
status: reviewing
---

## 正文

如有疑问请加小编微信号：YSN_GEO。
"""

        result = article_validator.scan_article_text(text)
        dirty_codes = {issue["code"] for issue in result["fatal"]}

        self.assertIn("contact_info", dirty_codes)

    def test_flags_technical_numeric_claim(self) -> None:
        text = """---
output_profile: publish_article
source_refs:
  - "[[300-Wiki/04-Sources/Source-GeoE-Test]]"
status: reviewing
---

## 监测判断

当 v/a 连续 3 天不下降时，必须启动黄色预警。
"""

        result = article_validator.scan_article_text(text)

        self.assertEqual([], result["fatal"])
        self.assertEqual(1, len(result["technical_claims"]))
        self.assertEqual("technical_claim", result["technical_claims"][0]["code"])

    def test_clean_article_passes(self) -> None:
        text = """---
output_profile: publish_article
source_refs:
  - "[[300-Wiki/04-Sources/Source-GeoE-Test]]"
status: reviewing
---

## 正文

本文介绍隧道监测中常见的数据判读思路，并说明使用边界。
"""

        result = article_validator.scan_article_text(text)

        self.assertEqual([], result["fatal"])
        self.assertEqual([], result["warning"])
        self.assertEqual([], result["technical_claims"])


class PublishManifestIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        manifest_validator.write_test_png(self.root / "cover.png", 2350, 1000)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def manifest(self) -> dict:
        return {
            "schema_version": 2,
            "status": "ready",
            "output_profile": "publish_article",
            "title": "Test title",
            "summary": "Test summary",
            "body_path": "article.md",
            "cover": {"path": "cover.png", "width": 2350, "height": 1000},
            "source_refs": [SOURCE_REF],
            "claim_evidence": [],
            "review": {key: "pass" for key in manifest_validator.REVIEW_KEYS},
            "publisher": {"mode": "manual", "enabled": False, "adapter": None, "action": "none"},
        }

    def write_article(self, body: str) -> None:
        (self.root / "article.md").write_text(body, encoding="utf-8")

    def test_manifest_revalidates_body_gate(self) -> None:
        self.write_article(
            """---
output_profile: publish_article
source_refs:
  - "[[300-Wiki/04-Sources/Source-GeoE-Test]]"
status: ready
---

## 正文

如有疑问请加小编微信号：YSN_GEO。
"""
        )

        errors = manifest_validator.validate_manifest(self.manifest(), self.root)

        self.assertTrue(any("body gate" in error and "contact_info" in error for error in errors))

    def test_manifest_requires_evidence_for_technical_claim(self) -> None:
        self.write_article(
            """---
output_profile: publish_article
source_refs:
  - "[[300-Wiki/04-Sources/Source-GeoE-Test]]"
status: ready
---

## 正文

当 v/a 连续 3 天不下降时，必须启动黄色预警。
"""
        )

        errors = manifest_validator.validate_manifest(self.manifest(), self.root)

        self.assertTrue(any("claim_evidence" in error for error in errors))

    def test_manifest_accepts_verified_claim_evidence(self) -> None:
        article = """---
output_profile: publish_article
source_refs:
  - "[[300-Wiki/04-Sources/Source-GeoE-Test]]"
status: ready
---

## 正文

当 v/a 连续 3 天不下降时，必须启动黄色预警。
"""
        self.write_article(article)
        claim = article_validator.scan_article_text(article)["technical_claims"][0]
        manifest = self.manifest()
        manifest["claim_evidence"] = [
            {
                "line": claim["line"],
                "claim": claim["text"],
                "source_ref": SOURCE_REF,
                "support": "来源明确给出了连续观测周期与对应预警动作。",
                "status": "verified",
            }
        ]

        errors = manifest_validator.validate_manifest(manifest, self.root)

        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
