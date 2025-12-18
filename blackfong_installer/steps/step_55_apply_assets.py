from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from ..lib.assets import copy_tree
from ..lib.chroot import chroot_cmd, mount_chroot_binds, umount_chroot_binds

logger = logging.getLogger(__name__)


class ApplyAssetsStep:
    step_id = "55_apply_assets"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("config") or {}
        exe = state.get("execution") or {}
        mounts = exe.get("mounts") or {}
        target_root = mounts.get("target_root")
        if not target_root:
            raise RuntimeError("execution.mounts.target_root missing")

        dry_run = bool(cfg.get("dry_run", False))

        repo_root = Path(__file__).resolve().parents[2]
        assets_dir = repo_root / "assets"

        # Copy systemd, udev, sudoers.d assets into target
        copy_tree(str(assets_dir / "systemd"), f"{target_root}/etc/systemd/system", dry_run=dry_run)
        copy_tree(str(assets_dir / "udev"), f"{target_root}/etc/udev/rules.d", dry_run=dry_run)
        copy_tree(str(assets_dir / "sudoers.d"), f"{target_root}/etc/sudoers.d", dry_run=dry_run)

        mount_chroot_binds(target_root, dry_run=dry_run)
        try:
            # Enable DAISE service only if binary exists.
            # (Your offline repo should provide /usr/local/bin/daise or package it appropriately.)
            chroot_cmd(
                target_root,
                [
                    "bash",
                    "-lc",
                    "if [ -x /usr/local/bin/daise ]; then systemctl enable daise.service; else echo 'DAISE binary missing; leaving service disabled'; fi",
                ],
                dry_run=dry_run,
            )

            # Firewall (ufw) toggle
            if bool(cfg.get("firewall_enabled", True)):
                chroot_cmd(target_root, ["bash", "-lc", "apt-get install -y ufw && ufw --force enable"], dry_run=dry_run)
            else:
                chroot_cmd(target_root, ["bash", "-lc", "apt-get install -y ufw && ufw --force disable"], dry_run=dry_run)
        finally:
            umount_chroot_binds(target_root, dry_run=dry_run)

        logger.info("Assets applied")
        return state
