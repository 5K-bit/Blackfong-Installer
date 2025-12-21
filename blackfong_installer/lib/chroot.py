from __future__ import annotations

import logging
from typing import Sequence

from .command import run_cmd

logger = logging.getLogger(__name__)


def chroot_cmd(target_root: str, argv: Sequence[str], *, dry_run: bool = False) -> None:
    """Run a command inside target root."""

    run_cmd(["chroot", target_root, *argv], dry_run=dry_run)


def mount_chroot_binds(target_root: str, *, dry_run: bool = False) -> None:
    # Minimal bind mounts for apt, grub-install, initramfs tooling
    for src, dst in [
        ("/dev", f"{target_root}/dev"),
        ("/proc", f"{target_root}/proc"),
        ("/sys", f"{target_root}/sys"),
    ]:
        run_cmd(["mount", "--bind", src, dst], dry_run=dry_run)


def umount_chroot_binds(target_root: str, *, dry_run: bool = False) -> None:
    for p in [f"{target_root}/sys", f"{target_root}/proc", f"{target_root}/dev"]:
        run_cmd(["umount", "-lf", p], check=False, dry_run=dry_run)
