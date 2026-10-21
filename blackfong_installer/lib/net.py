from __future__ import annotations

import logging
import urllib.request
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


def mirror_reachable(mirror: str, suite: str, *, timeout: int = 10) -> bool:
    """True if the package mirror's Release file for `suite` can be fetched over HTTP(S).

    This tests what the install actually needs (DNS + routing + the mirror), unlike ping, which
    is often blocked on otherwise working networks.
    """
    url = f"{mirror.rstrip('/')}/dists/{suite}/Release"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 (fixed http(s) mirror URL)
            return 200 <= r.status < 300
    except Exception as e:  # noqa: BLE001
        logger.info("mirror check failed for %s: %s", url, e)
        return False
