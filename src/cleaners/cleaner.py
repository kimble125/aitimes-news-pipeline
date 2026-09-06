"""정제 모듈 — raw → clean. Collect/Clean 담당."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 정제 과정에서 시도해볼 원본 날짜 포맷들 (수집기가 이미 ISO8601로 정규화하지만,
# 다른 소스/수동 입력 데이터를 대비해 방어적으로 처리한다).
_DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S",
    "%Y.%m.%d %H:%M",
    "%Y-%m-%d",
)


def clean_article(raw_row: dict[str, Any]) -> dict[str, Any]:
    """news_raw 한 행을 news_clean 행으로 변환한다(순수 함수)."""
    url = raw_row.get("url")
    title = raw_row.get("title")

    body_text = _extract_body_text(raw_row.get("raw_html"), raw_row.get("raw_text"))
    word_count = len(body_text.split()) if body_text else 0

    if not url or not title:
        status = "error"
    elif not body_text:
        status = "empty"
    else:
        status = "clean"

    return {
        "source": raw_row.get("source"),
        "url": url,
        "title": title,
        "published_at": _normalize_date(raw_row.get("published_at")),
        "category": raw_row.get("category"),
        "author": raw_row.get("author"),
        "body_text": body_text,
        "word_count": word_count,
        "cleaned_at": _now_iso(),
        "status": status,
    }


def _extract_body_text(raw_html: str | None, raw_text: str | None) -> str:
    """raw_html 우선, 없으면 raw_text 에서 태그를 제거하고 공백을 정규화한다."""
    source = raw_html or raw_text
    if not source:
        return ""
    text = BeautifulSoup(source, "lxml").get_text(" ")
    return re.sub(r"\s+", " ", text).strip()


def _normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    logger.warning("날짜 정규화 실패, 원본 유지: %s", value)
    return value


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean_articles(
    db_path: str,
    source: str | None = None,
    limit: int | None = None,
    force: bool = False,
    config: dict[str, Any] | None = None,
) -> int:
    """DB에서 raw를 읽어 clean 테이블에 기록. 처리 건수 반환."""
    from src.storage import db

    processed = 0
    with db.get_connection(db_path) as conn:
        rows = db.get_raw_for_clean(conn, source=source, limit=limit, include_cleaned=force)
        for raw in rows:
            cleaned = clean_article(raw)
            cleaned["raw_id"] = raw["id"]
            db.upsert_clean(conn, cleaned)
            processed += 1
    return processed
