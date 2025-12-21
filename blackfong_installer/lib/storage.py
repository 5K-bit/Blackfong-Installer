from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .command import run_cmd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PartitionPlan:
    disk: str
    firmware: str  # efi|uboot
    root_fs: str = "ext4"
    esp_size_mib: int = 512
    boot_size_mib: int = 1024
    swap_size_mib: Optional[int] = None


@dataclass(frozen=True)
class PartitionResult:
    root_part: str
    esp_part: Optional[str]
    boot_part: Optional[str]


def _part_suffix(disk: str, n: int) -> str:
    # nvme/mmcblk devices use p suffix
    if disk.endswith(tuple("0123456789")):
        return f"{disk}p{n}"
    return f"{disk}{n}"


def partition_and_format(
    *,
    plan: PartitionPlan,
    target_root: str,
    dry_run: bool = False,
) -> PartitionResult:
    """Create GPT partitions and filesystems.

    Layout:
    - EFI: ESP (FAT32) mounted at /boot/efi
    - U-Boot: optional /boot (ext4) mounted at /boot
    - Root: ext4 mounted at /

    Note: Device-specific layouts (e.g., Raspberry Pi firmware FAT) should be
    handled via profiles; this is a solid baseline for EFI systems and generic U-Boot.
    """

    disk = plan.disk
    logger.info("Partitioning disk=%s firmware=%s", disk, plan.firmware)

    # Wipe + GPT
    run_cmd(["sgdisk", "--zap-all", disk], dry_run=dry_run)
    run_cmd(["sgdisk", "--clear", disk], dry_run=dry_run)

    part_num = 1
    esp_part = None
    boot_part = None

    if plan.firmware == "efi":
        # ESP
        run_cmd(
            [
                "sgdisk",
                f"--new={part_num}:0:+{plan.esp_size_mib}MiB",
                f"--typecode={part_num}:ef00",
                f"--change-name={part_num}:EFI",
                disk,
            ],
            dry_run=dry_run,
        )
        esp_part = _part_suffix(disk, part_num)
        part_num += 1

    if plan.firmware == "uboot":
        # Dedicated /boot for extlinux (generic)
        run_cmd(
            [
                "sgdisk",
                f"--new={part_num}:0:+{plan.boot_size_mib}MiB",
                f"--typecode={part_num}:8300",
                f"--change-name={part_num}:BOOT",
                disk,
            ],
            dry_run=dry_run,
        )
        boot_part = _part_suffix(disk, part_num)
        part_num += 1

    # Root gets rest
    run_cmd(
        [
            "sgdisk",
            f"--new={part_num}:0:0",
            f"--typecode={part_num}:8300",
            f"--change-name={part_num}:ROOT",
            disk,
        ],
        dry_run=dry_run,
    )
    root_part = _part_suffix(disk, part_num)

    # Inform kernel
    run_cmd(["partprobe", disk], dry_run=dry_run)

    # Format
    if esp_part:
        run_cmd(["mkfs.vfat", "-F", "32", esp_part], dry_run=dry_run)
    if boot_part:
        run_cmd(["mkfs.ext4", "-F", boot_part], dry_run=dry_run)
    run_cmd(["mkfs.ext4", "-F", root_part], dry_run=dry_run)

    # Mount
    run_cmd(["mkdir", "-p", target_root], dry_run=dry_run)
    run_cmd(["mount", root_part, target_root], dry_run=dry_run)

    if boot_part:
        run_cmd(["mkdir", "-p", f"{target_root}/boot"], dry_run=dry_run)
        run_cmd(["mount", boot_part, f"{target_root}/boot"], dry_run=dry_run)

    if esp_part:
        run_cmd(["mkdir", "-p", f"{target_root}/boot/efi"], dry_run=dry_run)
        run_cmd(["mount", esp_part, f"{target_root}/boot/efi"], dry_run=dry_run)

    return PartitionResult(root_part=root_part, esp_part=esp_part, boot_part=boot_part)
