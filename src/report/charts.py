"""matplotlib 차트 — Lead/Report 담당(제안)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def setup_korean_font() -> str | None:
    """시스템에서 한글 폰트를 찾아 matplotlib에 설정. 없으면 None."""
    # TODO(Lead/Report): NanumGothic, Noto Sans CJK KR 등 탐지
    logger.warning("setup_korean_font stub — 한글 폰트 미설정")
    return None


def make_charts(
    db_path: str,
    out_dir: str,
    config: dict[str, Any] | None = None,
) -> list[str]:
    """
    TODO(Lead/Report):
    1) 카테고리별 건수 막대 PNG
    2) 일별 추이 선 PNG
    데이터 없으면 WARNING 후 빈 리스트.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    logger.info("make_charts stub db=%s out=%s", db_path, out_dir)
    raise NotImplementedError("make_charts 미구현 — 카테고리 건수 + 일별 추이 PNG")
