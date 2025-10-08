from __future__ import annotations
import sys
from loguru import logger

def setup_logging(level: str = "INFO") -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=level.upper(),
        enqueue=True,
        backtrace=True,
        diagnose=False,
        # sink=lambda msg: print(msg, end=""),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}"
        # colorize=False,
    )
