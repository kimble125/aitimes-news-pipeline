"""AI 요약 — Summarize/Analyze 담당(제안). API 키는 env 만 사용."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def summarize_article(title: str, body: str, *, model: str | None = None) -> str:
    """
    TODO(Summarize/Analyze): OpenAI-compatible chat.completions 호출.
    env: AI_API_KEY, AI_BASE_URL, AI_MODEL
    """
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        raise RuntimeError("AI_API_KEY 가 .env 에 없습니다")
    raise NotImplementedError("summarize_article 미구현")


def run_summarize(
    db_path: str,
    limit: int | None = 20,
    clean_id: int | None = None,
    unsummarized: bool = True,
    config: dict[str, Any] | None = None,
) -> int:
    logger.info(
        "run_summarize stub db=%s limit=%s clean_id=%s unsummarized=%s",
        db_path,
        limit,
        clean_id,
        unsummarized,
    )
    if not os.getenv("AI_API_KEY"):
        logger.error("AI_API_KEY missing — summarize 중단")
        return 0
    raise NotImplementedError(
        "run_summarize 미구현 — Summarize/Analyze이 get_unsummarized / upsert_summary 연결"
    )
