"""리포트 생성 — Lead/Report 담당(제안)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def write_report(
    db_path: str,
    out_dir: str,
    top_n: int = 10,
    fmt: str = "md",
    config: dict[str, Any] | None = None,
) -> str:
    """
    TODO(Lead/Report):
    - 품질 지표 2+ (DB 계산, 하드코딩 금지)
    - TOP N
    - 최신 insights_json
    - 콘솔 출력 + TXT/MD 파일
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    logger.info(
        "write_report stub db=%s out=%s top_n=%s fmt=%s",
        db_path,
        out_dir,
        top_n,
        fmt,
    )
    raise NotImplementedError("write_report 미구현")
