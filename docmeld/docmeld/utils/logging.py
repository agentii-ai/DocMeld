"""Timestamped logging utility for DocMeld pipeline."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path


def setup_logging(log_dir: str | None = None) -> logging.Logger:
    """Set up logging with timestamped log file.

    Creates a log file named docmeld_YYYYMMDD_HHMMSS.log in the
    specified directory (defaults to current working directory).
    """
    if log_dir is None:
        log_dir = str(Path.cwd())

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_filename = f"docmeld_{timestamp}.log"
    log_path = Path(log_dir) / log_filename

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger = logging.getLogger("docmeld")
    logger.setLevel(logging.DEBUG)

    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"Logging to {log_path}")
    return logger
