"""RSS 수집기 — Collect/Clean 담당(제안). stub: NotImplementedError."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class RSSCollector(BaseCollector):
    def fetch(self, limit: int = 20, **kwargs: Any) -> list[dict[str, Any]]:
        """
        TODO(Collect/Clean):
        - config.sources[source].rss_urls 순회
        - feedparser 또는 ElementTree/BS4 로 item 파싱
        - title, link/url, guid, pubDate, description → raw row
        - limit 적용, rate limit 불필요(피드 1~소수)
        """
        rss_urls = self.source_cfg.get("rss_urls") or []
        logger.info("RSSCollector stub: urls=%s limit=%s", rss_urls, limit)
        # 스켈레톤: 크래시 없이 빈 결과 + 명시적 미구현 신호
        raise NotImplementedError(
            "RSSCollector.fetch 미구현 — Collect/Clean이 docs/INTERFACE.md 계약에 맞게 구현하세요"
        )

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
