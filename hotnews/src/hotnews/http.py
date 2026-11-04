"""零依赖 HTTP 封装。只做三件事：拼查询串、带 UA、可选代理。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

USER_AGENT = "Mozilla/5.0 (compatible; hotnews/0.1)"


def build_opener() -> urllib.request.OpenerDirector:
    """按 HOTNEWS_PROXY 环境变量决定是否走代理。"""
    proxy = os.environ.get("HOTNEWS_PROXY")
    if proxy:
        handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        return urllib.request.build_opener(handler)
    return urllib.request.build_opener()


def build_url(url: str, params: Optional[dict[str, Any]] = None) -> str:
    if not params:
        return url
    query = urllib.parse.urlencode(params, doseq=True)
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{query}"


def request(
    url: str,
    *,
    method: str = "GET",
    data: Optional[bytes] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: int = 20,
) -> tuple[bytes, dict[str, str]]:
    """发起请求，返回 (原始字节, 响应头)。失败直接抛异常，由调用方降级。"""
    merged = {"User-Agent": USER_AGENT}
    if headers:
        merged.update(headers)
    req = urllib.request.Request(url, data=data, headers=merged, method=method)
    with build_opener().open(req, timeout=timeout) as resp:
        raw = resp.read()
        resp_headers = {k.lower(): v for k, v in resp.headers.items()}
    return raw, resp_headers


def get_text(
    url: str,
    *,
    params: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: int = 20,
) -> str:
    raw, _ = request(build_url(url, params), headers=headers, timeout=timeout)
    return raw.decode("utf-8", errors="replace")


def get_json(
    url: str,
    *,
    params: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: int = 20,
) -> Any:
    return json.loads(get_text(url, params=params, headers=headers, timeout=timeout))


def describe_error(exc: BaseException) -> str:
    """把异常压成一行可读文本，写进 raw.json 的 error 字段。"""
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return f"{type(exc.reason).__name__}: {exc.reason}"
    return f"{type(exc).__name__}: {exc}"
