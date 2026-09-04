"""데이터 내보내기 CSV/JSONL/Excel — Lead/Report 담당(제안)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def export_data(
    db_path: str,
    out_dir: str,
    formats: list[str],
    config: dict[str, Any] | None = None,
) -> list[str]:
    """
    TODO(Lead/Report): pandas 등으로 news_clean(+summary) export.
    formats 예: ['csv','jsonl','xlsx'] — 최소 2종.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    logger.info("export_data stub db=%s out=%s formats=%s", db_path, out_dir, formats)
    raise NotImplementedError("export_data 미구현 — csv/jsonl 우선")
