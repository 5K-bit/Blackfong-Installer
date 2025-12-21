from __future__ import annotations

from pathlib import Path


def detect_firmware() -> str:
    """Detect firmware type for the *currently running* environment.

    Returns: 'efi' or 'uboot'.

    Note: For installation targets, profiles may override this.
    """

    if Path("/sys/firmware/efi").exists():
        return "efi"
    return "uboot"
