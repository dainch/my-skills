"""命令行入口。三个子命令对应三层工作流。"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from . import collectors, render as renderer

SCHEMA_TEXT = """\
interpret.json 契约
===================

必填字段：
  date            字符串，YYYY-MM-DD
  sections        数组，至少一个主题；每个主题：
                    name   字符串，主题名
                    items  数组，无命中时给空数组
                  每个条目：
                    title  字符串，必填
                    url    字符串，必填，http(s):// 开头

选填字段（条目级）：
  platform        来源平台，如 "Hacker News"
  published_at    发布时间，拿不到就写 null
  content_type    内容类型，如 "社区讨论" / "产品发布" / "学术论文"
  heat            互动量，如 "HN 312 分·84 评论" / "★12.3k"；取不到写 null
  summary         一到两句事实摘要；优先压缩 raw.json 的 items[].summary，没有才写 null
  significance    判断/意义，属于推断而非事实；没有就写 null

选填字段（顶层）：
  window          时间窗口描述，如 "过去 24 小时"
  generated_at    生成时间，如 "2026-11-04 12:00"
  source_status   对象，值只允许 ok / no_hit / degraded / unavailable
                  no_hit 为路由正常但零命中，与路由异常（degraded/unavailable）严格分开

硬性规则：
  1. 不得编造 published_at、summary、heat 中的任何数字
  2. summary 只写事实，significance 只写判断，两者不得混淆
  3. 拿不到的字段写 null —— 渲染器会整行省略，不会输出"未知"或"N/A"
  4. 条目顺序即你判断的重要性顺序
"""


def _split_keywords(raw: str) -> list[str]:
    parts = re.split(r"[,，]", raw)
    keywords = [part.strip() for part in parts if part.strip()]
    if not keywords:
        raise ValueError("--keywords 至少需要一个关键词")
    return keywords


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _temp_raw_path() -> str:
    """中间件默认落在系统临时目录，不污染调用方工作目录。"""
    return str(Path(tempfile.mkdtemp(prefix="hotnews-")) / "raw.json")


def _default_md_name(data: Any) -> str:
    """产物默认名只带日期，不带关键词。"""
    return f"每日热点-{data['date']}.md"


def cmd_collect(args: argparse.Namespace) -> int:
    try:
        keywords = _split_keywords(args.keywords)
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    requested = [name.strip() for name in args.sources.split(",")] if args.sources else None
    if requested:
        unknown = [name for name in requested if name not in collectors.COLLECTORS]
        if unknown:
            available = ", ".join(collectors.COLLECTORS)
            print(f"错误：未知信源 {unknown}；可用：{available}", file=sys.stderr)
            return 2
        selected = requested
    else:
        selected = list(collectors.COLLECTORS)

    def run(name: str) -> tuple[str, Any]:
        collector = collectors.COLLECTORS[name]
        print(f"[collect] {name} ...", file=sys.stderr, flush=True)
        return name, collector(keywords, args.limit, args.timeout, args.hours)

    with ThreadPoolExecutor(max_workers=len(selected)) as pool:
        results = dict(pool.map(run, selected))

    payload = {
        "schema_version": 1,
        "date": args.date,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "window_hours": args.hours,
        "keywords": keywords,
        "sources": [results[name].to_dict() for name in selected],
    }

    target = args.out or _temp_raw_path()
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if target == "-":
        out_path = "<stdout>"
        sys.stdout.write(text + "\n")
    else:
        out_path = Path(target)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")

    print("", file=sys.stderr)
    for name in selected:
        result = results[name]
        detail = f" — {result.error}" if result.error else ""
        if result.status == "no_hit":
            detail = " — 无匹配；英文平台（hackernews/github/reddit）请提供英文关键词"
        print(
            f"[collect] {name}: {result.status} ({len(result.items)} 条){detail}",
            file=sys.stderr,
        )
    print(f"[collect] 已写入 {out_path}", file=sys.stderr)
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    try:
        if args.data == "-":
            data = renderer.loads_text(sys.stdin.read(), "stdin")
        else:
            data_path = Path(args.data)
            if not data_path.exists():
                print(f"错误：找不到 {data_path}", file=sys.stderr)
                return 2
            data = renderer.load_json(data_path)
        markdown = renderer.render(data)
    except renderer.RenderError as exc:
        print(f"渲染失败：{exc}", file=sys.stderr)
        return 1

    out_path = Path(args.out or _default_md_name(data))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        print(f"[render] 覆盖已存在的 {out_path}", file=sys.stderr)
    out_path.write_text(markdown, encoding="utf-8")
    print(f"[render] 已写入 {out_path}", file=sys.stderr)
    return 0


def cmd_schema(_: argparse.Namespace) -> int:
    print(SCHEMA_TEXT)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hotnews",
        description="关键词驱动热点收集器 + 确定性渲染器",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    collect = sub.add_parser("collect", help="抓取原始信号，写出 raw.json")
    collect.add_argument("--keywords", required=True, help="逗号分隔，支持中英文逗号")
    collect.add_argument(
        "--out",
        help="输出路径；省略则写入系统临时目录，'-' 表示写 stdout",
    )
    collect.add_argument("--date", default=_today(), help="日期 YYYY-MM-DD，默认今天")
    collect.add_argument("--hours", type=int, default=24, help="时间窗口（小时），默认 24")
    collect.add_argument("--limit", type=int, default=20, help="每个信源的最大条数")
    collect.add_argument("--timeout", type=int, default=20, help="单次请求超时（秒）")
    collect.add_argument("--sources", help="只跑指定信源，逗号分隔")
    collect.set_defaults(func=cmd_collect)

    render = sub.add_parser("render", help="把 interpret.json 强制渲染成 Markdown")
    render.add_argument("--data", required=True, help="interpret.json 路径；'-' 表示读 stdin")
    render.add_argument(
        "--out",
        help="输出 Markdown 路径；省略则为 每日热点-YYYY-MM-DD.md（不含关键词）",
    )
    render.set_defaults(func=cmd_render)

    schema = sub.add_parser("schema", help="打印 interpret.json 契约")
    schema.set_defaults(func=cmd_schema)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
