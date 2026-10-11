from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def copy_tree(src: str, dst: str, *, dry_run: bool = False, ignore: tuple[str, ...] = ()) -> None:
    """Copy a tree. `ignore` is top-level-relative names/dirs to skip (e.g. build, .git)."""
    s = Path(src)
    d = Path(dst)
    if not s.exists():
        raise FileNotFoundError(src)

    if dry_run:
        logger.info("Would copy tree %s -> %s", str(s), str(d))
        return

    d.mkdir(parents=True, exist_ok=True)
    skip = set(ignore)
    for item in s.rglob("*"):
        rel = item.relative_to(s)
        if rel.parts and rel.parts[0] in skip:
            continue
        out = d / rel
        if item.is_dir():
            out.mkdir(parents=True, exist_ok=True)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, out)
