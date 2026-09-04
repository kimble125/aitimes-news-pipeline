"""수집기 베이스 클래스."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    def __init__(self, config: dict[str, Any], source: str = "aitimes") -> None:
        self.config = config
        self.source = source
        self.source_cfg = (config.get("sources") or {}).get(source, {})

    @abstractmethod
    def fetch(self, limit: int = 20, **kwargs: Any) -> list[dict[str, Any]]:
        """news_raw 에 넣을 dict 리스트를 반환."""
        raise NotImplementedError
