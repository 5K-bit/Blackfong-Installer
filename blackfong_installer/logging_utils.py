from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

DEFAULT_LOG_PATH = "/var/log/blackfong-installer.log"


def configure_logging(
    log_path: str = DEFAULT_LOG_PATH,
    level: int = logging.INFO,
    also_console: bool = True,
) -> str:
    """Configure logging.

    Requirement: all decisions recorded to /var/log/blackfong-installer.log.

    Notes:
    - In some live environments, writing to /var/log may not be permitted.
      We still *attempt* to write there first; if it fails, we fall back to
      a local file next to the running working directory, while continuing to
      *report* the intended path in state/logs.

    Returns the actual file path being used.
    """

    logger = logging.getLogger()
    logger.setLevel(level)

    # Avoid duplicate handlers if configure_logging() is called multiple times.
    if getattr(logger, "_blackfong_configured", False):
        return getattr(logger, "_blackfong_log_path", log_path)

    chosen_path = log_path
    handlers: list[logging.Handler] = []

    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    file_handler: Optional[logging.Handler] = None
    try:
        Path(os.path.dirname(log_path) or ".").mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(fmt)
        handlers.append(file_handler)
        chosen_path = log_path
    except Exception:
        # Fall back to a writable location.
        fallback = str(Path.cwd() / "blackfong-installer.log")
        file_handler = logging.FileHandler(fallback)
        file_handler.setFormatter(fmt)
        handlers.append(file_handler)
        chosen_path = fallback

    if also_console:
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        handlers.append(console)

    for h in handlers:
        logger.addHandler(h)

    setattr(logger, "_blackfong_configured", True)
    setattr(logger, "_blackfong_log_path", chosen_path)

    logging.getLogger(__name__).info(
        "Logging initialized (requested=%s, actual=%s)", log_path, chosen_path
    )
    return chosen_path
