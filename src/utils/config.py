"""설정 로더 — config.json + .env."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_config(path: str) -> dict[str, Any]:
    """JSON 설정 파일을 로드한다. .env 는 dotenv로 선택 로드."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        logger.debug("python-dotenv 미설치 — .env 스킵")

    p = Path(path)
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    logger.info("config loaded: %s", p)
    return data
