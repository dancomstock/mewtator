import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from pathlib import Path


def _get_log_dir() -> Path:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).resolve().parents[2]
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_logger() -> logging.Logger:
    logger = logging.getLogger("mewtator")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    log_path = _get_log_dir() / "mewtator.log"

    handler = RotatingFileHandler(
        log_path,
        maxBytes=1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
