from __future__ import annotations

import logging
from .command import run_cmd

logger = logging.getLogger(__name__)


def is_online(*, dry_run: bool = False) -> bool:
    """Best-effort online check."""

    try:
        run_cmd(["ip", "route"], dry_run=dry_run)
        r = run_cmd(["ping", "-c", "1", "-W", "2", "1.1.1.1"], check=False, dry_run=dry_run)
        return r.returncode == 0
    except Exception:
        return False
