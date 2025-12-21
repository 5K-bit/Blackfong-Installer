from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from ..lib.block import get_uuid
from ..lib.fstab import FstabEntry, render_fstab

logger = logging.getLogger(__name__)


class WriteFstabStep:
    step_id = "25_write_fstab"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("config") or {}
        exe = state.get("execution") or {}
        mounts = exe.get("mounts") or {}
        target_root = mounts.get("target_root")
        root_part = mounts.get("root_part")
        esp_part = mounts.get("esp_part")
        boot_part = mounts.get("boot_part")

        if not target_root or not root_part:
            raise RuntimeError("Missing target_root/root_part; run partition step first")

        dry_run = bool(cfg.get("dry_run", False))

        entries: list[FstabEntry] = []

        root_uuid = get_uuid(root_part, dry_run=dry_run)
        entries.append(
            FstabEntry(
                spec=f"UUID={root_uuid}",
                mountpoint="/",
                fstype="ext4",
                options="defaults",
                dump=0,
                passno=1,
            )
        )

        if boot_part:
            boot_uuid = get_uuid(boot_part, dry_run=dry_run)
            entries.append(
                FstabEntry(
                    spec=f"UUID={boot_uuid}",
                    mountpoint="/boot",
                    fstype="ext4",
                    options="defaults",
                    dump=0,
                    passno=2,
                )
            )

        if esp_part:
            esp_uuid = get_uuid(esp_part, dry_run=dry_run)
            entries.append(
                FstabEntry(
                    spec=f"UUID={esp_uuid}",
                    mountpoint="/boot/efi",
                    fstype="vfat",
                    options="umask=0077",
                    dump=0,
                    passno=1,
                )
            )

        fstab_contents = render_fstab(entries)
        fstab_path = Path(target_root) / "etc/fstab"

        if dry_run:
            logger.info("Would write %s", str(fstab_path))
        else:
            fstab_path.parent.mkdir(parents=True, exist_ok=True)
            fstab_path.write_text(fstab_contents, encoding="utf-8")

        state.setdefault("execution", {}).setdefault("decisions", {})["root_uuid"] = root_uuid
        logger.info("Wrote fstab (root_uuid=%s)", root_uuid)
        return state
