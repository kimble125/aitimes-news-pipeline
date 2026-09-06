"""AI 요약 — Summarize/Analyze 담당. API 키는 env 만 사용."""

from __future__ import annotations

import logging
import os
from typing import Any

from openai import OpenAI

from src.storage import db

logger = logging.getLogger(__name__)


def summarize_article(title: str, body: str, *, model: str | None = None) -> str:
    """
    기사 1건을 AI로 요약한다.
    env: AI_API_KEY, AI_BASE_URL, AI_MODEL
    """
    api_key = os.getenv("AI_API_KEY")
    base_url = os.getenv("AI_BASE_URL")
    model_name = model or os.getenv("AI_MODEL")

    if not api_key:
        raise RuntimeError("AI_API_KEY 가 .env 에 없습니다")

    if not base_url:
        raise RuntimeError("AI_BASE_URL 이 .env 에 없습니다")

    if not model_name:
        raise RuntimeError("AI_MODEL 이 .env 에 없습니다")

    # 토큰 과다 사용 방지를 위해 본문 앞부분만 사용
    max_body_chars = 12000
    body_text = (body or "")[:max_body_chars]

    if not body_text.strip():
        raise ValueError("기사 본문이 비어 있습니다")

    client = OpenAI(
         api_key=api_key,
        base_url=base_url,
    )

    prompt = f"""
다음 뉴스 기사를 한국어로 요약하세요.

조건:
- 3~8문장으로 작성
- 기사에 나온 사실만 사용
- 추측하거나 없는 내용을 추가하지 말 것
- 핵심 내용이 잘 드러나도록 간결하게 작성
- 제목과 본문의 중요한 정보를 우선 반영

제목:
{title}

본문:
{body_text}
""".strip()

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": "당신은 뉴스 기사를 사실 중심으로 요약하는 AI입니다.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    text = response.choices[0].message.content

    if not text or not text.strip():
        raise RuntimeError("AI 요약 결과가 비어 있습니다")

    return text.strip()


def run_summarize(
    db_path: str,
    limit: int | None = 20,
    clean_id: int | None = None,
    unsummarized: bool = True,
    config: dict[str, Any] | None = None,
) -> int:
    if not os.getenv("AI_API_KEY"):
        logger.error("AI_API_KEY 가 없습니다 — .env 를 확인하세요")
        return 0

    done = 0

    with db.get_connection(db_path) as conn:
        targets = db.get_unsummarized(
            conn,
            limit=limit,
            clean_id=clean_id,
        )

        if not targets:
            logger.info("요약할 기사가 없습니다")
            return 0

        logger.info("요약 대상: %d건", len(targets))

        for i, art in enumerate(targets, 1):
            try:
                text = summarize_article(
                    art["title"],
                    art["body_text"],
                )

                db.upsert_summary(
                    conn,
                    {
                        "clean_id": art["id"],
                        "summary_text": text,
                        "model": os.getenv("AI_MODEL"),
                        "status": "ok",
                    },
                )

                logger.info(
                    "[%d/%d] ID=%s 요약 완료 (%d자 → %d자)",
                    i,
                    len(targets),
                    art["id"],
                    len(art["body_text"] or ""),
                    len(text),
                )

                done += 1

            except Exception as exc:
                logger.error(
                    "ID=%s 요약 실패: %s",
                    art["id"],
                    exc,
                )

                db.upsert_summary(
                    conn,
                    {
                        "clean_id": art["id"],
                        "status": "error",
                        "error_message": str(exc),
                    },
                )

    return done