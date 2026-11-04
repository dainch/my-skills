"""数据模型：collect 层的中间表示。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class Item:
    """单一热点条目。字段只描述事实，不做价值判断。"""

    title: str
    url: str
    source: str
    published_at: Optional[str] = None
    summary: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SourceResult:
    """单个信源的抓取结果。status 取值 ok / no_hit / degraded / unavailable。"""

    name: str
    status: str
    items: list[Item] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "count": len(self.items),
            "error": self.error,
            "items": [item.to_dict() for item in self.items],
        }
