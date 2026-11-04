"""各信源的抓取实现。

每个 collect_* 函数只负责抓取和归一化，不做关键词价值判断，
不因为单条失败而中止，最终状态由 _finalize 统一计算。
"""

from __future__ import annotations

import html
import json
import math
import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Optional

from . import http
from .models import Item, SourceResult

DEFAULT_RSS_FEEDS = {
    "36kr": "https://36kr.com/feed",
    "techcrunch": "https://techcrunch.com/feed/",
    "producthunt": "https://www.producthunt.com/feed",
    "devto": "https://dev.to/feed",
}

ATOM_NS = "http://www.w3.org/2005/Atom"
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


# ── 公共工具 ──────────────────────────────────────────────────────


def _per_keyword(limit: int, keyword_count: int) -> int:
    """把总配额平均分给每个关键词，至少 2 条。"""
    if keyword_count <= 0:
        return limit
    return max(2, math.ceil(limit / keyword_count))


def _iso_from_epoch(value: Any) -> Optional[str]:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _iso_from_text(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return parsedate_to_datetime(text).isoformat()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return None


def _dedupe(items: list[Item]) -> list[Item]:
    seen: set[str] = set()
    result: list[Item] = []
    for item in items:
        key = item.url.strip().rstrip("/").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _matches_keywords(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords if keyword)


def _clean_text(raw: Any, max_chars: int = 200) -> Optional[str]:
    """把 HTML 正文/描述清成一句摘要；拿不到实质内容时返回 None。

    这里只做去标签、反转义、压空白和长度截断，不改写句子。
    """
    if not isinstance(raw, str):
        return None
    text = html.unescape(TAG_RE.sub(" ", raw))
    text = SPACE_RE.sub(" ", text).strip()
    if not text:
        return None
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "…"
    return text


def _finalize(
    name: str, items: list[Item], errors: list[str], limit: int, attempts: int
) -> SourceResult:
    """去重截断并判定状态。

    no_hit      = 请求全部成功，但零条命中（路由正常，该平台确实没有相关内容）
    ok          = 请求全部成功且有命中
    degraded    = 部分请求成功
    unavailable = 全部请求失败

    no_hit 与 unavailable 是两种事实：前者的路由是通的，后者不是。
    不要把两者合写成 0 条，否则无法区分“工具挂了”和“确实没内容”。
    """
    unique = _dedupe(items)[:limit]
    if errors:
        status = "degraded" if attempts > len(errors) else "unavailable"
    else:
        status = "ok" if unique else "no_hit"
    return SourceResult(
        name=name,
        status=status,
        items=unique,
        error="; ".join(errors) if errors else None,
    )


# ── 信源实现 ──────────────────────────────────────────────────────


def collect_hackernews(
    keywords: list[str], limit: int, timeout: int, hours: int
) -> SourceResult:
    items: list[Item] = []
    errors: list[str] = []
    per = _per_keyword(limit, len(keywords))
    # /search 按相关性排序会捞出几年前的帖子，必须用 /search_by_date 加时间窗
    since = int(time.time() - max(hours, 1) * 3600)

    for keyword in keywords:
        try:
            data = http.get_json(
                "https://hn.algolia.com/api/v1/search_by_date",
                params={
                    "query": keyword,
                    "tags": "story",
                    "hitsPerPage": per,
                    "numericFilters": f"created_at_i>{since}",
                },
                timeout=timeout,
            )
            for hit in data.get("hits", []):
                title = (hit.get("title") or "").strip()
                if not title:
                    continue
                object_id = hit.get("objectID", "")
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
                items.append(
                    Item(
                        title=title,
                        url=url,
                        source="hackernews",
                        published_at=_iso_from_epoch(hit.get("created_at_i")),
                        summary=_clean_text(hit.get("story_text")),
                        extra={
                            "points": hit.get("points"),
                            "comments": hit.get("num_comments"),
                            "keyword": keyword,
                        },
                    )
                )
        except Exception as exc:  # noqa: BLE001 - 单源失败必须降级而非中断
            errors.append(f"{keyword}: {http.describe_error(exc)}")
        time.sleep(0.3)

    return _finalize("hackernews", items, errors, limit, len(keywords))


def collect_github(keywords: list[str], limit: int, timeout: int, hours: int) -> SourceResult:
    items: list[Item] = []
    errors: list[str] = []
    per = _per_keyword(limit, len(keywords))
    # 不限近期活跃会返回多年前停更的仓库，按 30 天窗口过滤
    active_since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("HOTNEWS_GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    for keyword in keywords:
        try:
            data = http.get_json(
                "https://api.github.com/search/repositories",
                params={
                    "q": f"{keyword} pushed:>{active_since}",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": per,
                },
                headers=headers,
                timeout=timeout,
            )
            for repo in data.get("items", []):
                full_name = repo.get("full_name", "")
                if not full_name:
                    continue
                stars = repo.get("stargazers_count", 0)
                items.append(
                    Item(
                        title=full_name,
                        url=repo.get("html_url", ""),
                        source="github",
                        published_at=_iso_from_text(repo.get("pushed_at")),
                        summary=_clean_text(repo.get("description"), 160),
                        extra={"stars": stars, "keyword": keyword},
                    )
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{keyword}: {http.describe_error(exc)}")
        # 未认证限额 10 次/分钟，留出间隔避免连坐
        time.sleep(1.0 if token else 6.5)

    return _finalize("github", items, errors, limit, len(keywords))


def collect_reddit(keywords: list[str], limit: int, timeout: int, hours: int) -> SourceResult:
    items: list[Item] = []
    errors: list[str] = []
    per = _per_keyword(limit, len(keywords))

    for keyword in keywords:
        try:
            data = http.get_json(
                "https://www.reddit.com/search.json",
                params={"q": keyword, "sort": "hot", "t": "day", "limit": per},
                headers={"Accept": "application/json"},
                timeout=timeout,
            )
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                title = (post.get("title") or "").strip()
                permalink = post.get("permalink") or ""
                if not title or not permalink:
                    continue
                items.append(
                    Item(
                        title=title,
                        url=f"https://www.reddit.com{permalink}",
                        source="reddit",
                        published_at=_iso_from_epoch(post.get("created_utc")),
                        summary=_clean_text(post.get("selftext")),
                        extra={"subreddit": post.get("subreddit"), "keyword": keyword},
                    )
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{keyword}: {http.describe_error(exc)}")
        time.sleep(1.0)

    return _finalize("reddit", items, errors, limit, len(keywords))


def _parse_feed(xml_text: str, source_name: str) -> list[Item]:
    """同时兼容 RSS 2.0 与 Atom。"""
    items: list[Item] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    for node in root.iter("item"):
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()
        if title and link:
            items.append(
                Item(
                    title=f"[{source_name.upper()}] {title}",
                    url=link,
                    source="rss",
                    published_at=_iso_from_text(node.findtext("pubDate")),
                    summary=_clean_text(
                        node.findtext("description")
                        or node.findtext(f"{{{CONTENT_NS}}}encoded")
                    ),
                )
            )

    if items:
        return items

    for node in root.findall(f".//{{{ATOM_NS}}}entry"):
        title = (node.findtext(f"{{{ATOM_NS}}}title") or "").strip()
        link_node = node.find(f"{{{ATOM_NS}}}link")
        link = link_node.get("href", "").strip() if link_node is not None else ""
        published = node.findtext(f"{{{ATOM_NS}}}published") or node.findtext(
            f"{{{ATOM_NS}}}updated"
        )
        if title and link:
            items.append(
                Item(
                    title=f"[{source_name.upper()}] {title}",
                    url=link,
                    source="rss",
                    published_at=_iso_from_text(published),
                    summary=_clean_text(
                        node.findtext(f"{{{ATOM_NS}}}summary")
                        or node.findtext(f"{{{ATOM_NS}}}content")
                    ),
                )
            )

    return items


def collect_rss(
    keywords: list[str],
    limit: int,
    timeout: int,
    hours: int,
    feeds: Optional[dict[str, str]] = None,
) -> SourceResult:
    feeds = feeds or DEFAULT_RSS_FEEDS
    matched: list[Item] = []
    unmatched: list[Item] = []
    errors: list[str] = []

    for name, url in feeds.items():
        try:
            text = http.get_text(url, timeout=timeout)
            for item in _parse_feed(text, name):
                if _matches_keywords(item.title, keywords):
                    matched.append(item)
                else:
                    unmatched.append(item)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {http.describe_error(exc)}")

    # 关键词命中的排前面，泛科技条目只用来补足配额
    ordered = _dedupe(matched) + _dedupe(
        [item for item in unmatched if item.url not in {m.url for m in matched}]
    )
    return _finalize("rss", ordered, errors, limit, len(feeds))


def collect_v2ex(keywords: list[str], limit: int, timeout: int, hours: int) -> SourceResult:
    items: list[Item] = []
    errors: list[str] = []
    try:
        data = http.get_json("https://www.v2ex.com/api/topics/hot.json", timeout=timeout)
        for topic in data if isinstance(data, list) else []:
            title = (topic.get("title") or "").strip()
            url = topic.get("url") or ""
            if not title or not url:
                continue
            items.append(
                Item(
                    title=title,
                    url=url,
                    source="v2ex",
                    published_at=_iso_from_epoch(topic.get("created")),
                    summary=_clean_text(topic.get("content")),
                    extra={"node": (topic.get("node") or {}).get("title")},
                )
            )
    except Exception as exc:  # noqa: BLE001
        errors.append(http.describe_error(exc))

    return _finalize("v2ex", items, errors, limit, 1)


# ── Exa MCP（微信公众号唯一通路） ─────────────────────────────────

EXA_ENDPOINT = "https://mcp.exa.ai/mcp"
MCP_PROTOCOL = "2024-11-05"


def _mcp_headers(session_id: Optional[str]) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["mcp-session-id"] = session_id
    return headers


def _parse_sse(payload: str) -> list[dict[str, Any]]:
    """MCP 的 HTTP 传输可能返回纯 JSON，也可能返回 SSE 事件流。"""
    payload = payload.strip()
    if not payload:
        return []
    if payload.startswith("{"):
        try:
            return [json.loads(payload)]
        except json.JSONDecodeError:
            return []

    events: list[dict[str, Any]] = []
    for block in payload.split("\n\n"):
        data_lines = [
            line[5:].lstrip() for line in block.splitlines() if line.startswith("data:")
        ]
        if not data_lines:
            continue
        try:
            events.append(json.loads("\n".join(data_lines)))
        except json.JSONDecodeError:
            continue
    return events


def _mcp_post(
    endpoint: str, payload: dict[str, Any], session_id: Optional[str], timeout: int
) -> tuple[list[dict[str, Any]], Optional[str]]:
    body = json.dumps(payload).encode("utf-8")
    raw, headers = http.request(
        endpoint,
        method="POST",
        data=body,
        headers=_mcp_headers(session_id),
        timeout=timeout,
    )
    events = _parse_sse(raw.decode("utf-8", errors="replace"))
    return events, headers.get("mcp-session-id")


def _parse_exa_text(text: str) -> list[dict[str, str]]:
    """Exa 返回的正文形如 Title/URL/Published/Text 块，以 --- 分隔。"""
    results: list[dict[str, str]] = []
    for block in re.split(r"\n-{3,}\s*\n", text):
        title_match = re.search(r"^Title:\s*(.+)$", block, re.MULTILINE)
        url_match = re.search(r"^URL:\s*(.+)$", block, re.MULTILINE)
        if not title_match or not url_match:
            continue
        published_match = re.search(r"^Published:\s*(.+)$", block, re.MULTILINE)
        text_match = re.search(r"^Text:\s*(.+)$", block, re.MULTILINE | re.DOTALL)
        results.append(
            {
                "title": title_match.group(1).strip(),
                "url": url_match.group(1).strip(),
                "published": published_match.group(1).strip() if published_match else "",
                "text": text_match.group(1).strip() if text_match else "",
            }
        )
    return results


def exa_search(query: str, num_results: int, timeout: int) -> list[dict[str, str]]:
    endpoint = os.environ.get("HOTNEWS_EXA_ENDPOINT", EXA_ENDPOINT)

    _, session_id = _mcp_post(
        endpoint,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL,
                "capabilities": {},
                "clientInfo": {"name": "hotnews", "version": "0.1.0"},
            },
        },
        None,
        timeout,
    )

    _mcp_post(
        endpoint,
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        session_id,
        timeout,
    )

    events, _ = _mcp_post(
        endpoint,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "web_search_exa",
                "arguments": {"query": query, "numResults": num_results},
            },
        },
        session_id,
        timeout,
    )

    for event in events:
        result = event.get("result") or {}
        for block in result.get("content", []):
            if block.get("type") == "text":
                return _parse_exa_text(block.get("text", ""))
    return []


def collect_wechat(keywords: list[str], limit: int, timeout: int, hours: int) -> SourceResult:
    """微信只走 Exa。发布日期多半拿不到，如实留空而非编造。"""
    items: list[Item] = []
    errors: list[str] = []
    per = _per_keyword(limit, len(keywords))

    for keyword in keywords:
        # 在查询串里嵌入年月，部分弥补 Exa 不支持日期过滤的缺陷
        stamp = datetime.now().strftime("%Y年%m月")
        query = f"{stamp} {keyword} site:mp.weixin.qq.com"
        try:
            for hit in exa_search(query, per, timeout):
                if "mp.weixin.qq.com" not in hit["url"]:
                    continue
                items.append(
                    Item(
                        title=hit["title"],
                        url=hit["url"],
                        source="wechat",
                        published_at=_iso_from_text(hit.get("published") or None),
                        summary=_clean_text(hit.get("text")),
                        extra={"keyword": keyword},
                    )
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{keyword}: {http.describe_error(exc)}")
        time.sleep(1.0)

    return _finalize("wechat", items, errors, limit, len(keywords))


# ── 注册表 ────────────────────────────────────────────────────────

COLLECTORS = {
    "hackernews": collect_hackernews,
    "github": collect_github,
    "reddit": collect_reddit,
    "rss": collect_rss,
    "v2ex": collect_v2ex,
    "wechat": collect_wechat,
}
