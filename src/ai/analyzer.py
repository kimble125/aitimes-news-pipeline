"""AI 인사이트 분석 — Summarize/Analyze 담당(제안)."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def analyze_batch(articles: list[dict[str, Any]], *, model: str | None = None) -> dict[str, Any]:
    """
    TODO(Summarize/Analyze): 구조화 JSON 반환.
    trends / keywords / similarities_differences / implications 중 2+ 채우기.
    """
    if not os.getenv("AI_API_KEY"):
        raise RuntimeError("AI_API_KEY 가 .env 에 없습니다")
    raise NotImplementedError("analyze_batch 미구현")


def run_analyze(
    db_path: str,
    limit: int = 50,
    since: str | None = None,
    config: dict[str, Any] | None = None,
) -> bool:
    logger.info("run_analyze stub db=%s limit=%s since=%s", db_path, limit, since)
    if not os.getenv("AI_API_KEY"):
        logger.error("AI_API_KEY missing — analyze 중단")
        return False
    raise NotImplementedError(
        "run_analyze 미구현 — Summarize/Analyze이 insert_analysis 로 insights_json 저장"
    )
