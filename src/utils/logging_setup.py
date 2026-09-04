"""로깅 초기화 — INFO/WARNING/ERROR (+ verbose 시 DEBUG)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any


def setup_logging(config: dict[str, Any], verbose: bool = False) -> None:
    log_cfg = config.get("logging", {})
    level_name = "DEBUG" if verbose else log_cfg.get("level", "INFO")
    level = getattr(logging, str(level_name).upper(), logging.INFO)

    log_file = log_cfg.get("file", "logs/pipeline.log")
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    root.addHandler(sh)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    root.addHandler(fh)
