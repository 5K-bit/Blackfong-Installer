from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def copy_tree(src: str, dst: str, *, dry_run: bool = False) -> None:
    s = Path(src)
    d = Path(dst)
    if not s.exists():
        raise FileNotFoundError(src)

    if dry_run:
        logger.info("Would copy tree %s -> %s", str(s), str(d))
        return

    d.mkdir(parents=True, exist_ok=True)
    for item in s.rglob("*"):
        rel = item.relative_to(s)
        out = d / rel
        if item.is_dir():
            out.mkdir(parents=True, exist_ok=True)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, out)
