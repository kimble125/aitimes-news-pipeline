"""AI 인사이트 분석 — Summarize/Analyze 담당."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

from openai import OpenAI

from src.storage import db

logger = logging.getLogger(__name__)


def analyze_batch(
    articles: list[dict[str, Any]],
    *,
    model: str | None = None,
) -> dict[str, Any]:
    """
    여러 기사를 한 번의 AI 호출로 분석하여 구조화된 JSON을 반환한다.
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

    if not articles:
        raise ValueError("분석할 기사가 없습니다")

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    # 여러 기사를 AI에게 전달할 텍스트 구성
    article_texts = []

    for i, article in enumerate(articles, 1):
        title = article.get("title") or "(제목 없음)"

        # 요약문이 있으면 우선 사용하고, 없으면 본문 일부 사용
        content = (
            article.get("summary_text")
            or article.get("body_text")
            or ""
        )

        # 기사 1개가 지나치게 길어지는 것을 방지
        content = content[:3000]

        url = article.get("url") or ""

        article_texts.append(
            f"""
[{i}]
제목: {title}
URL: {url}
내용: {content}
""".strip()
        )

    combined_articles = "\n\n".join(article_texts)

    prompt = f"""
다음 뉴스 기사들을 종합 분석하세요.

반드시 아래 JSON 구조만 반환하세요.
코드펜스(```)나 추가 설명은 작성하지 마세요.

{{
  "trends": ["주요 트렌드"],
  "keywords": [
    {{
      "term": "핵심 키워드",
      "score": 0.0
    }}
  ],
  "similarities_differences": {{
    "similar": ["기사들의 공통점"],
    "different": ["기사들의 차이점"]
  }},
  "implications": ["시사점"],
  "top_articles": [
    {{
      "url": "기사 URL",
      "title": "기사 제목",
      "reason": "중요한 이유"
    }}
  ]
}}

조건:
- 기사에 포함된 사실을 중심으로 분석할 것
- 근거 없는 내용을 추측하지 말 것
- trends, keywords, similarities_differences, implications 중
  최소 2개 이상은 반드시 내용이 있도록 작성할 것
- keywords의 score는 0.0~1.0 사이 숫자로 작성할 것
- JSON only, 코드펜스 없이 반환할 것

분석 대상 기사:
{combined_articles}
""".strip()

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 여러 뉴스 기사를 종합하여 "
                    "트렌드와 핵심 인사이트를 구조화하는 분석 AI입니다."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    text = response.choices[0].message.content

    if not text or not text.strip():
        raise RuntimeError("AI 분석 결과가 비어 있습니다")

    # AI가 혹시 코드펜스를 붙였을 경우 최소한으로 정리
    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]

    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"AI 분석 결과를 JSON으로 변환하지 못했습니다: {exc}"
        ) from exc

    if not isinstance(result, dict):
        raise RuntimeError("AI 분석 결과가 JSON 객체가 아닙니다")

    return result


def run_analyze(
    db_path: str,
    limit: int = 50,
    since: str | None = None,
    category: str | None = None,
    config: dict[str, Any] | None = None,
) -> bool:
    """
    조건별 기사를 모아 AI 분석 1건을 저장한다.
    """
    if not os.getenv("AI_API_KEY"):
        logger.error("AI_API_KEY 가 없습니다 — .env 를 확인하세요")
        return False

    with db.get_connection(db_path) as conn:
        articles = db.get_clean_articles(
            conn,
            limit=limit,
            since=since,
            category=category,
        )

        if not articles:
            logger.warning("분석할 기사가 없습니다")
            return False

        logger.info("분석 대상: %d건", len(articles))

        batch_key = (
            f"analysis_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        try:
            result = analyze_batch(articles)

            db.insert_analysis(
                conn,
                {
                    "batch_key": batch_key,
                    "insights_json": result,
                    "model": os.getenv("AI_MODEL"),
                    "status": "ok",
                },
            )

            logger.info(
                "AI 인사이트 분석 완료: batch=%s, 기사=%d건",
                batch_key,
                len(articles),
            )

            return True

        except Exception as exc:
            logger.error("AI 인사이트 분석 실패: %s", exc)

            db.insert_analysis(
                conn,
                {
                    "batch_key": batch_key,
                    "insights_json": {},
                    "model": os.getenv("AI_MODEL"),
                    "status": "error",
                    "error_message": str(exc),
                },
            )

            return False