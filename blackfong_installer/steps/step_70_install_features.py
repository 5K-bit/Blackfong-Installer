from __future__ import annotations

import logging
from typing import Any, Dict

from ..lib.chroot import mount_chroot_binds, umount_chroot_binds
from ..lib.net import is_online
from ..lib.pkg import apt_install, apt_update

logger = logging.getLogger(__name__)


class InstallFeaturesStep:
    step_id = "70_install_features"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("config") or {}
        exe = state.get("execution") or {}
        mounts = exe.get("mounts") or {}
        target_root = mounts.get("target_root")
        if not target_root:
            raise RuntimeError("execution.mounts.target_root missing")

        dry_run = bool(cfg.get("dry_run", False))
        src = cfg.get("install_source", "offline")

        online = is_online(dry_run=dry_run)
        state.setdefault("execution", {}).setdefault("decisions", {})["online"] = online

        # Offline-first rule: only attempt online extras if install_source permits and we are online.
        allow_online = src in {"online", "hybrid"} and online

        base_features = [
            "python3",
            "python3-venv",
            "python3-pip",
            "gstreamer1.0-plugins-base",
            "gstreamer1.0-plugins-good",
        ]

        extras_online = [
            # These are often large or repo-dependent; gated.
            "onnxruntime",
            "python3-torch",
        ]

        mount_chroot_binds(target_root, dry_run=dry_run)
        try:
            apt_update(target_root, dry_run=dry_run)
            apt_install(target_root, base_features, dry_run=dry_run)
            if allow_online:
                apt_install(target_root, extras_online, dry_run=dry_run)
        finally:
            umount_chroot_binds(target_root, dry_run=dry_run)

        logger.info("Features installed (allow_online=%s)", allow_online)
        return state
