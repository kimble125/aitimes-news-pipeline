"""RSS 수집기 — Collect/Clean 담당."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree

import requests

from src.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# AI타임스 RSS 의 pubDate 는 RFC822 가 아니라 "YYYY-MM-DD HH:MM:SS" 커스텀 포맷이다.
_PUBDATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class RSSCollector(BaseCollector):
    def fetch(self, limit: int = 20, **kwargs: Any) -> list[dict[str, Any]]:
        rss_urls = self.source_cfg.get("rss_urls") or []
        session = self.build_session()
        fetched_at = self._now_iso()

        rows: list[dict[str, Any]] = []
        for rss_url in rss_urls:
            if len(rows) >= limit:
                break
            try:
                response = session.get(rss_url, timeout=self.timeout)
                response.raise_for_status()
                root = ElementTree.fromstring(response.content)
            except (requests.RequestException, ElementTree.ParseError) as exc:
                logger.warning("RSS 수집 실패, 건너뜀: url=%s error=%s", rss_url, exc)
                continue

            for item in root.iter("item"):
                if len(rows) >= limit:
                    break
                url = self._text(item, "link")
                if not url:
                    logger.warning("RSS item에 link 없음, 건너뜀: %s", rss_url)
                    continue
                rows.append(
                    {
                        "source": self.source,
                        "method": "rss",
                        "guid": self._text(item, "guid") or url,
                        "url": url,
                        "title": self._text(item, "title"),
                        "published_at": self._parse_pubdate(self._text(item, "pubDate")),
                        "category": self._text(item, "category"),
                        "author": self._text(item, "author"),
                        "raw_html": None,
                        "raw_text": self._text(item, "description"),
                        "fetched_at": fetched_at,
                        "status": "fetched",
                        "error_message": None,
                    }
                )

        return rows

    @staticmethod
    def _text(item: ElementTree.Element, tag: str) -> str | None:
        el = item.find(tag)
        if el is None or el.text is None:
            return None
        return el.text.strip() or None

    @staticmethod
    def _parse_pubdate(value: str | None) -> str | None:
        if not value:
            return None
        try:
            dt = datetime.strptime(value, _PUBDATE_FORMAT).replace(tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            logger.warning("pubDate 파싱 실패, 원본 유지: %s", value)
            return value

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
