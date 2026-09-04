"""HTML 크롤링 수집기 (requests + BeautifulSoup) — Collect/Clean 담당(제안)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class CrawlCollector(BaseCollector):
    def fetch(self, limit: int = 20, **kwargs: Any) -> list[dict[str, Any]]:
        """
        TODO(Collect/Clean):
        - list_url_templates 로 페이지 순회 (max_pages)
        - 기사 URL 추출 후 detail 파싱
        - config.crawl.delay_sec sleep
        - User-Agent 헤더
        """
        max_pages = kwargs.get("max_pages")
        delay = (self.config.get("crawl") or {}).get("delay_sec", 1.5)
        templates = self.source_cfg.get("list_url_templates") or []
        logger.info(
            "CrawlCollector stub: templates=%s limit=%s max_pages=%s delay=%s",
            templates,
            limit,
            max_pages,
            delay,
        )
        raise NotImplementedError(
            "CrawlCollector.fetch 미구현 — Collect/Clean이 list+detail 파서를 구현하세요"
        )

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
