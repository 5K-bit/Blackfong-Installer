from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Sequence

from .command import run_cmd

logger = logging.getLogger(__name__)


def fetch_bundle(repos: Sequence[Dict[str, Any]], dest: Path, *, dry_run: bool = False) -> list[str]:
    """Shallow-clone each bundle repo into dest/<name> (no .git kept). Returns names fetched."""
    fetched: list[str] = []
    if not dry_run:
        dest.mkdir(parents=True, exist_ok=True)
    for r in repos:
        name, url = str(r["name"]), str(r["url"])
        out = dest / name
        if out.exists() and not dry_run:
            run_cmd(["rm", "-rf", str(out)])
        run_cmd(["git", "clone", "--depth", "1", url, str(out)], dry_run=dry_run)
        if not dry_run:
            run_cmd(["rm", "-rf", str(out / ".git")])
        fetched.append(name)
    return fetched
