from __future__ import annotations

import logging
from dataclasses import dataclass

from .command import run_cmd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BlockIds:
    uuid: str


def get_uuid(dev: str, *, dry_run: bool = False) -> str:
    """Return filesystem UUID for a block device."""

    r = run_cmd(["blkid", "-s", "UUID", "-o", "value", dev], dry_run=dry_run)
    uuid = (r.stdout or "").strip()
    if not uuid and not dry_run:
        raise RuntimeError(f"Unable to determine UUID for {dev}")
    return uuid
