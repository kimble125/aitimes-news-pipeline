"""HTML 크롤링 수집기 (requests + BeautifulSoup) — Collect/Clean 담당."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# 상세페이지 "입력 YYYY.MM.DD HH:MM" 포맷.
_PUBLISHED_FORMAT = "%Y.%m.%d %H:%M"


class CrawlCollector(BaseCollector):
    def fetch(self, limit: int = 20, **kwargs: Any) -> list[dict[str, Any]]:
        crawl_cfg = self.config.get("crawl") or {}
        delay = crawl_cfg.get("delay_sec", 1.5)
        max_pages = kwargs.get("max_pages") or crawl_cfg.get("max_pages", 5)
        max_articles = crawl_cfg.get("max_articles_per_run")
        if max_articles:
            limit = min(limit, max_articles)

        templates = self.source_cfg.get("list_url_templates") or []
        session = self.build_session()

        article_urls: list[str] = []
        for template in templates:
            for page in range(1, max_pages + 1):
                if len(article_urls) >= limit:
                    break
                list_url = template.format(page=page)
                try:
                    response = session.get(list_url, timeout=self.timeout)
                    response.raise_for_status()
                except requests.RequestException as exc:
                    logger.warning("목록 페이지 요청 실패, 건너뜀: url=%s error=%s", list_url, exc)
                    continue
                time.sleep(delay)

                soup = BeautifulSoup(response.text, "lxml")
                for anchor in soup.select("h2.altlist-subject a[href]"):
                    href = anchor.get("href")
                    if href and href not in article_urls:
                        article_urls.append(href)
                    if len(article_urls) >= limit:
                        break

        rows: list[dict[str, Any]] = []
        for url in article_urls[:limit]:
            try:
                response = session.get(url, timeout=self.timeout)
                response.raise_for_status()
            except requests.RequestException as exc:
                logger.warning("상세 페이지 요청 실패, 건너뜀: url=%s error=%s", url, exc)
                continue
            time.sleep(delay)

            row = self._parse_detail(url, response.text)
            if row:
                rows.append(row)

        return rows

    def _parse_detail(self, url: str, html: str) -> dict[str, Any] | None:
        soup = BeautifulSoup(html, "lxml")

        title_el = soup.select_one("h1.heading")
        if title_el is None:
            logger.warning("상세 페이지에서 제목을 찾지 못함, 건너뜀: %s", url)
            return None

        category_el = soup.select_one("nav.view-navigation a")
        author_el = soup.select_one("li.info-name")
        body_el = soup.select_one("#article-view-content-div")

        return {
            "source": self.source,
            "method": "crawl",
            "guid": url,
            "url": url,
            "title": title_el.get_text(strip=True),
            "published_at": self._parse_published(self._find_input_date(soup)),
            "category": category_el.get_text(strip=True) if category_el else None,
            "author": author_el.get_text(strip=True) if author_el else None,
            "raw_html": str(body_el) if body_el else None,
            "raw_text": None,
            "fetched_at": self._now_iso(),
            "status": "fetched",
            "error_message": None,
        }

    @staticmethod
    def _find_input_date(soup: BeautifulSoup) -> str | None:
        """게시일 <li> 를 찾는다.

        수정된 기사는 <li class="info-update"><div class="info-update-origin">입력 ...</div></li>,
        수정 안 된 기사는 클래스 없는 <li>입력 ...</li> 로 마크업이 다르다.
        """
        origin = soup.select_one("li.info-update .info-update-origin")
        if origin is not None:
            return origin.get_text(strip=True)
        for li in soup.select("ul.breadcrumbs li"):
            text = li.get_text(strip=True)
            if text.startswith("입력"):
                return text
        return None

    @staticmethod
    def _parse_published(value: str | None) -> str | None:
        if not value:
            return None
        # "입력 2026.09.05 19:25" -> "2026.09.05 19:25"
        cleaned = value.replace("입력", "").strip()
        try:
            dt = datetime.strptime(cleaned, _PUBLISHED_FORMAT).replace(tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            logger.warning("게시일 파싱 실패, 원본 유지: %s", value)
            return value

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
