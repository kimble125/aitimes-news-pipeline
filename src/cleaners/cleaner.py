"""정제 모듈 — raw → clean. Collect/Clean 담당(제안)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def clean_article(raw_row: dict[str, Any]) -> dict[str, Any]:
    """
    TODO(Collect/Clean):
    - raw_html/raw_text 에서 HTML 제거 (BS4 get_text)
    - 공백 정규화, word_count
    - 빈 본문이면 status='empty'
    """
    raise NotImplementedError("clean_article 미구현")


def clean_articles(
    db_path: str,
    source: str | None = None,
    limit: int | None = None,
    force: bool = False,
    config: dict[str, Any] | None = None,
) -> int:
    """DB에서 raw를 읽어 clean 테이블에 기록. 처리 건수 반환."""
    logger.info(
        "clean_articles stub db=%s source=%s limit=%s force=%s",
        db_path,
        source,
        limit,
        force,
    )
    raise NotImplementedError(
        "clean_articles 미구현 — Collect/Clean이 storage.get_raw_for_clean / upsert_clean 사용"
    )
