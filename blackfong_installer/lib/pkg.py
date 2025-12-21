from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Sequence

from .chroot import chroot_cmd
from .command import run_cmd

logger = logging.getLogger(__name__)


def debootstrap_rootfs(
    *,
    target_root: str,
    suite: str = "stable",
    mirror: str = "http://deb.debian.org/debian",
    arch: str | None = None,
    dry_run: bool = False,
) -> None:
    argv = ["debootstrap"]
    if arch:
        argv += ["--arch", arch]
    argv += [suite, target_root, mirror]
    run_cmd(argv, dry_run=dry_run)


def apt_update(target_root: str, *, dry_run: bool = False) -> None:
    chroot_cmd(target_root, ["apt-get", "update"], dry_run=dry_run)


def apt_install(target_root: str, packages: Sequence[str], *, dry_run: bool = False) -> None:
    if not packages:
        return
    chroot_cmd(
        target_root,
        [
            "apt-get",
            "install",
            "-y",
            "--no-install-recommends",
            *packages,
        ],
        dry_run=dry_run,
    )


def write_sources_list_offline(
    target_root: str,
    repo_path: str,
    *,
    suite: str = "bookworm",
    component: str = "main",
) -> None:
    """Configure apt to use an on-media repo (file://).

    repo_path must be a path accessible in the live environment and mounted or copied into target.
    """

    p = Path(target_root) / "etc/apt/sources.list.d/blackfong-offline.list"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"deb [trusted=yes] file:{repo_path} {suite} {component}\n", encoding="utf-8")
    logger.info("Configured offline apt repo: %s (%s %s)", repo_path, suite, component)
