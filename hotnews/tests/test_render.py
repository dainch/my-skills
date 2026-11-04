"""渲染器回归测试。用标准库 unittest，零额外依赖。

运行：python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hotnews import collectors  # noqa: E402
from hotnews import render as r  # noqa: E402
from hotnews.models import Item  # noqa: E402


def minimal(**overrides) -> dict:
    data = {
        "date": "2026-11-04",
        "sections": [
            {
                "name": "测试主题",
                "items": [
                    {"title": "条目一", "url": "https://example.com/a"},
                ],
            }
        ],
    }
    data.update(overrides)
    return data


class RenderContractTest(unittest.TestCase):
    def test_minimal_renders_title_and_link(self) -> None:
        out = r.render(minimal())
        self.assertIn("# 每日热点 2026-11-04", out)
        self.assertIn("## 测试主题", out)
        self.assertIn("### 1. 条目一", out)
        self.assertIn("- 链接：[https://example.com/a](https://example.com/a)", out)
        self.assertTrue(out.rstrip().endswith(r.SIGNATURE))

    def test_null_field_omits_entire_line(self) -> None:
        data = minimal()
        data["sections"][0]["items"][0].update(
            {"published_at": None, "summary": None, "platform": "Hacker News"}
        )
        out = r.render(data)
        self.assertIn("- 来源平台：Hacker News", out)
        self.assertNotIn("发布时间", out)
        self.assertNotIn("摘要", out)
        self.assertNotIn("N/A", out)
        self.assertNotIn("未知", out)

    def test_blank_string_treated_as_missing(self) -> None:
        data = minimal()
        data["sections"][0]["items"][0]["summary"] = "   "
        self.assertNotIn("摘要", r.render(data))

    def test_empty_section_renders_placeholder(self) -> None:
        data = minimal()
        data["sections"].append({"name": "空主题", "items": []})
        out = r.render(data)
        self.assertIn("## 空主题", out)
        self.assertIn("（本主题今日无命中条目）", out)

    def test_heat_line_sits_between_content_type_and_summary(self) -> None:
        data = minimal()
        data["sections"][0]["items"][0].update(
            {
                "content_type": "产品发布",
                "heat": "HN 312 分 · 84 评论",
                "summary": "一句话事实。",
            }
        )
        out = r.render(data)
        self.assertIn("- 热度：HN 312 分 · 84 评论", out)
        positions = [
            out.index("- 内容类型："),
            out.index("- 热度："),
            out.index("- 摘要："),
        ]
        self.assertEqual(positions, sorted(positions))

    def test_missing_heat_omits_line(self) -> None:
        data = minimal()
        data["sections"][0]["items"][0]["heat"] = None
        self.assertNotIn("热度", r.render(data))

    def test_route_failure_status_appends_clarification(self) -> None:
        data = minimal(source_status={"reddit": "degraded", "v2ex": "no_hit"})
        out = r.render(data)
        self.assertIn(
            "reddit degraded、v2ex no_hit（degraded/unavailable 为路由异常，不代表该平台无内容）",
            out,
        )

    def test_no_hit_alone_gets_no_clarification(self) -> None:
        out = r.render(minimal(source_status={"v2ex": "no_hit"}))
        self.assertIn("v2ex no_hit", out)
        self.assertNotIn("路由异常", out)

    def test_status_line_reports_all_sources(self) -> None:
        data = minimal(
            source_status={"hackernews": "ok", "wechat": "unavailable"},
            window="过去 24 小时",
            generated_at="2026-11-04 18:30",
        )
        out = r.render(data)
        self.assertIn("hackernews ok、wechat unavailable", out)
        self.assertIn("时间窗口 过去 24 小时", out)
        self.assertIn("共 1 条，覆盖 1 个主题", out)


class RenderValidationTest(unittest.TestCase):
    def test_bad_date_rejected(self) -> None:
        with self.assertRaises(r.RenderError) as ctx:
            r.render(minimal(date="2026/11/04"))
        self.assertIn("date", str(ctx.exception))

    def test_empty_sections_rejected(self) -> None:
        with self.assertRaises(r.RenderError):
            r.render(minimal(sections=[]))

    def test_relative_url_rejected(self) -> None:
        data = minimal()
        data["sections"][0]["items"][0]["url"] = "example.com/a"
        with self.assertRaises(r.RenderError) as ctx:
            r.render(data)
        self.assertIn("http://", str(ctx.exception))

    def test_unknown_status_rejected(self) -> None:
        data = minimal(source_status={"wechat": "failed"})
        with self.assertRaises(r.RenderError) as ctx:
            r.render(data)
        self.assertIn("source_status.wechat", str(ctx.exception))

    def test_all_errors_reported_at_once(self) -> None:
        data = {
            "date": "bad",
            "sections": [
                {"name": "", "items": [{"title": "", "url": "ftp://x"}]},
            ],
        }
        with self.assertRaises(r.RenderError) as ctx:
            r.render(data)
        message = str(ctx.exception)
        self.assertIn("date", message)
        self.assertIn("sections[0].name", message)
        self.assertIn("sections[0].items[0].title", message)
        self.assertIn("sections[0].items[0].url", message)

    def test_non_string_optional_field_rejected(self) -> None:
        data = minimal()
        data["sections"][0]["items"][0]["summary"] = 123
        with self.assertRaises(r.RenderError):
            r.render(data)


class CleanTextTest(unittest.TestCase):
    """采集层把源描述清成一句摘要，不改写句子。"""

    def test_strips_tags_and_unescapes(self) -> None:
        raw = "<p>第一段 &amp; 第二段</p>\n<div>结束</div>"
        self.assertEqual(collectors._clean_text(raw), "第一段 & 第二段 结束")

    def test_truncates_with_ellipsis(self) -> None:
        out = collectors._clean_text("测" * 30, max_chars=10)
        self.assertEqual(out, "测" * 10 + "…")

    def test_empty_inputs_return_none(self) -> None:
        for raw in (None, "", "   ", "<p></p>", 123):
            self.assertIsNone(collectors._clean_text(raw))

    def test_item_to_dict_carries_summary(self) -> None:
        item = Item(title="t", url="https://e.com/a", source="rss", summary="一句描述")
        self.assertEqual(item.to_dict()["summary"], "一句描述")


class FeedParseTest(unittest.TestCase):
    def test_rss_description_becomes_summary(self) -> None:
        xml_text = (
            "<rss version='2.0'><channel><item>"
            "<title>标题</title><link>https://example.com/a</link>"
            "<pubDate>Mon, 03 Nov 2026 10:00:00 +0000</pubDate>"
            "<description>&lt;p&gt;正文&amp;说明&lt;/p&gt;</description>"
            "</item></channel></rss>"
        )
        items = collectors._parse_feed(xml_text, "techcrunch")
        self.assertEqual(items[0].summary, "正文&说明")

    def test_atom_summary_becomes_summary(self) -> None:
        xml_text = (
            "<feed xmlns='http://www.w3.org/2005/Atom'><entry>"
            "<title>标题</title><link href='https://example.com/b'/>"
            "<published>2026-11-03T10:00:00Z</published>"
            "<summary>原子摘要</summary></entry></feed>"
        )
        items = collectors._parse_feed(xml_text, "36kr")
        self.assertEqual(items[0].summary, "原子摘要")

    def test_exa_block_captures_text(self) -> None:
        block = (
            "Title: 示例文章\nURL: https://mp.weixin.qq.com/s/x\n"
            "Published: 2026-11-03\nText: 第一段正文\n\n---\n"
            "Title: 第二篇\nURL: https://mp.weixin.qq.com/s/y\n"
        )
        hits = collectors._parse_exa_text(block)
        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[0]["text"], "第一段正文")
        self.assertEqual(hits[1]["text"], "")


class FinalizeStatusTest(unittest.TestCase):
    """no_hit 必须由采集层产出，不能靠 Agent 自己判断。"""

    def test_zero_items_without_errors_is_no_hit(self) -> None:
        result = collectors._finalize("v2ex", [], [], limit=10, attempts=2)
        self.assertEqual(result.status, "no_hit")

    def test_items_without_errors_is_ok(self) -> None:
        item = Item(title="t", url="https://example.com/a", source="v2ex")
        self.assertEqual(collectors._finalize("v2ex", [item], [], 10, 2).status, "ok")

    def test_partial_failure_is_degraded(self) -> None:
        item = Item(title="t", url="https://example.com/a", source="v2ex")
        self.assertEqual(collectors._finalize("v2ex", [item], ["a: boom"], 10, 2).status, "degraded")

    def test_all_attempts_failed_is_unavailable(self) -> None:
        result = collectors._finalize("v2ex", [], ["a: boom", "b: boom"], 10, 2)
        self.assertEqual(result.status, "unavailable")


class LoadJsonTest(unittest.TestCase):
    def test_strips_markdown_fence(self) -> None:
        payload = {"date": "2026-11-04", "sections": [{"name": "x", "items": []}]}
        fenced = "```json\n" + json.dumps(payload) + "\n```"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "i.json"
            path.write_text(fenced, encoding="utf-8")
            self.assertEqual(r.load_json(path)["date"], "2026-11-04")

    def test_invalid_json_raises_render_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "i.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(r.RenderError):
                r.load_json(path)


if __name__ == "__main__":
    unittest.main()
