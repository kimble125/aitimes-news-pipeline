"""수집기 베이스 클래스."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

import requests

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

    @property
    def timeout(self) -> tuple[float, float]:
        """(connect, read) 타임아웃. config.timeouts 에서 읽는다."""
        timeouts = self.config.get("timeouts") or {}
        return (
            float(timeouts.get("http_connect_sec", 10)),
            float(timeouts.get("http_read_sec", 30)),
        )

    def build_session(self) -> requests.Session:
        """User-Agent 가 설정된 공용 requests 세션을 만든다."""
        session = requests.Session()
        user_agent = self.source_cfg.get("user_agent")
        if user_agent:
            session.headers.update({"User-Agent": user_agent})
        return session
