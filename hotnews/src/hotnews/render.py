"""确定性渲染器。

格式的唯一真源在这里，不在任何 Markdown 模板文件里。
任何字段缺失或类型错误都会导致渲染失败并返回非零退出码，
从而保证「同一份 interpret.json 在任何机器上产出逐字节一致的结果」。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

SIGNATURE = "<!-- rendered by hotnews 0.1.0 -->"
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VALID_STATUS = {"ok", "no_hit", "degraded", "unavailable"}
# 路由级异常：写进资料说明，避免被读成"该平台今日无内容"
ROUTE_FAILURE_STATUS = {"degraded", "unavailable"}

ITEM_ORDER = (
    ("platform", "来源平台"),
    ("published_at", "发布时间"),
    ("content_type", "内容类型"),
    ("heat", "热度"),
    ("summary", "摘要"),
    ("significance", "判断"),
)


class RenderError(ValueError):
    """interpret.json 不满足契约。"""


def load_json(path: Path) -> Any:
    return loads_text(path.read_text(encoding="utf-8"), str(path))


def loads_text(text: str, source: str = "stdin") -> Any:
    """读 JSON 时容忍 Agent 常见的 ```json 围栏包裹。"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RenderError(f"{source}: 不是合法 JSON（{exc.msg}，第 {exc.lineno} 行）") from exc


def _clean(value: Any) -> Optional[str]:
    """空串、纯空白、None 一律视为"未取得"。"""
    if value is None:
        return None
    if not isinstance(value, str):
        raise RenderError(f"期望字符串，实际是 {type(value).__name__}: {value!r}")
    stripped = value.strip()
    return stripped or None


def validate(data: Any) -> None:
    """收集全部错误后一次性抛出，便于 Agent 一次改完。"""
    errors: list[str] = []
    if not isinstance(data, dict):
        raise RenderError("顶层必须是 JSON 对象")

    date = data.get("date")
    if not isinstance(date, str) or not DATE_PATTERN.match(date):
        errors.append("date: 必填，格式 YYYY-MM-DD")

    window = data.get("window")
    if window is not None and not isinstance(window, str):
        errors.append("window: 必须是字符串")

    generated_at = data.get("generated_at")
    if generated_at is not None and not isinstance(generated_at, str):
        errors.append("generated_at: 必须是字符串")

    status_map = data.get("source_status")
    if status_map is not None:
        if not isinstance(status_map, dict):
            errors.append("source_status: 必须是对象")
        else:
            for key, status in status_map.items():
                if status not in VALID_STATUS:
                    errors.append(
                        f"source_status.{key}: 只允许 {'/'.join(sorted(VALID_STATUS))}，实际 {status!r}"
                    )

    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append("sections: 必填，且至少一个主题")
    else:
        for s_idx, section in enumerate(sections):
            where = f"sections[{s_idx}]"
            if not isinstance(section, dict):
                errors.append(f"{where}: 必须是对象")
                continue
            if _clean(section.get("name")) is None:
                errors.append(f"{where}.name: 必填，主题名不能为空")
            items = section.get("items")
            if not isinstance(items, list):
                errors.append(f"{where}.items: 必填，必须是数组（无命中时给空数组）")
                continue
            for i_idx, item in enumerate(items):
                at = f"{where}.items[{i_idx}]"
                if not isinstance(item, dict):
                    errors.append(f"{at}: 必须是对象")
                    continue
                if _clean(item.get("title")) is None:
                    errors.append(f"{at}.title: 必填")
                url = _clean(item.get("url"))
                if url is None:
                    errors.append(f"{at}.url: 必填")
                elif not url.startswith(("http://", "https://")):
                    errors.append(f"{at}.url: 必须以 http:// 或 https:// 开头")
                for field, label in ITEM_ORDER:
                    value = item.get(field)
                    if value is not None and not isinstance(value, str):
                        errors.append(f"{at}.{field}: {label}必须是字符串或 null")

    if errors:
        raise RenderError("interpret.json 不符合契约：\n  - " + "\n  - ".join(errors))


def _status_line(data: dict[str, Any]) -> str:
    parts: list[str] = []
    if data.get("generated_at"):
        parts.append(f"生成时间 {data['generated_at'].strip()}")
    if data.get("window"):
        parts.append(f"时间窗口 {data['window'].strip()}")

    status_map = data.get("source_status") or {}
    if status_map:
        joined = "、".join(f"{name} {status}" for name, status in status_map.items())
        if any(status in ROUTE_FAILURE_STATUS for status in status_map.values()):
            joined += "（degraded/unavailable 为路由异常，不代表该平台无内容）"
        parts.append(f"信源状态：{joined}")

    total = sum(len(section.get("items") or []) for section in data["sections"])
    parts.append(f"共 {total} 条，覆盖 {len(data['sections'])} 个主题")
    return "资料说明：" + "；".join(parts) + "。"


def render(data: dict[str, Any]) -> str:
    validate(data)

    lines: list[str] = [f"# 每日热点 {data['date']}", "", _status_line(data), ""]

    for section in data["sections"]:
        lines.append(f"## {section['name'].strip()}")
        lines.append("")
        items = section.get("items") or []
        if not items:
            lines.extend(["（本主题今日无命中条目）", ""])
            continue

        for index, item in enumerate(items, start=1):
            lines.append(f"### {index}. {item['title'].strip()}")
            lines.append("")
            for field, label in ITEM_ORDER:
                value = _clean(item.get(field))
                if value is None:
                    # 未取得就省略整行，不写"未知"、不写"N/A"
                    continue
                lines.append(f"- {label}：{value}")
            url = item["url"].strip()
            lines.append(f"- 链接：[{url}]({url})")
            lines.append("")

    lines.append(SIGNATURE)
    lines.append("")
    return "\n".join(lines)
