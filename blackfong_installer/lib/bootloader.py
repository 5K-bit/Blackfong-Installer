from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .chroot import chroot_cmd

logger = logging.getLogger(__name__)


def install_grub_efi(
    *,
    target_root: str,
    disk: str,
    dry_run: bool = False,
) -> None:
    """Install GRUB for x86_64 EFI targets."""

    # Assumes /boot/efi is mounted in target.
    chroot_cmd(
        target_root,
        [
            "grub-install",
            "--target=x86_64-efi",
            "--efi-directory=/boot/efi",
            "--bootloader-id=BlackfongOS",
            "--recheck",
        ],
        dry_run=dry_run,
    )
    chroot_cmd(target_root, ["update-grub"], dry_run=dry_run)
    logger.info("GRUB EFI installed")


def write_extlinux_config(
    *,
    target_root: str,
    root_uuid: str,
    dry_run: bool = False,
) -> None:
    """Write a generic extlinux.conf for U-Boot."""

    extlinux_dir = Path(target_root) / "boot/extlinux"
    extlinux_dir.mkdir(parents=True, exist_ok=True)

    cfg = extlinux_dir / "extlinux.conf"
    contents = (
        "DEFAULT blackfong\n"
        "TIMEOUT 5\n"
        "MENU TITLE Blackfong OS\n\n"
        "LABEL blackfong\n"
        "  LINUX /vmlinuz\n"
        "  INITRD /initrd.img\n"
        f"  APPEND root=UUID={root_uuid} rw quiet\n"
    )

    if not dry_run:
        cfg.write_text(contents, encoding="utf-8")
    logger.info("Wrote extlinux config: %s", str(cfg))
