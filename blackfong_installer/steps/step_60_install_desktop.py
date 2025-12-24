from __future__ import annotations

import logging
from typing import Any, Dict

from ..lib.chroot import mount_chroot_binds, umount_chroot_binds
from ..lib.pkg import apt_has_package, apt_install, apt_update

logger = logging.getLogger(__name__)


class InstallDesktopStep:
    step_id = "60_install_desktop"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("config") or {}
        exe = state.get("execution") or {}
        mounts = exe.get("mounts") or {}
        target_root = mounts.get("target_root")
        if not target_root:
            raise RuntimeError("execution.mounts.target_root missing")

        dry_run = bool(cfg.get("dry_run", False))

        # Desktop base selection:
        # - We run a Debian rootfs today; "xubuntu" here means "Xubuntu-style XFCE desktop".
        desktop_base = str(cfg.get("desktop_base", "xubuntu")).strip().lower()

        # Baseline audio/media stack.
        packages: list[str] = ["pipewire", "wireplumber", "gstreamer1.0-tools"]

        # Xubuntu-style base (XFCE + Xorg + display manager).
        # NOTE: On Debian this is provided by task/meta packages (not Ubuntu's xubuntu-desktop).
        with_recommends = False
        if desktop_base in {"xubuntu", "xfce", "xfce4"}:
            packages += [
                "task-xfce-desktop",
                "lightdm",
                "network-manager-gnome",
            ]
            with_recommends = True

        # Optional: Blackfong shell (only if repo provides it).
        blackfong_shell_pkg = str(cfg.get("blackfong_shell_package", "blackfong-bde-shell")).strip()

        mount_chroot_binds(target_root, dry_run=dry_run)
        try:
            apt_update(target_root, dry_run=dry_run)
            if blackfong_shell_pkg and apt_has_package(target_root, blackfong_shell_pkg, dry_run=dry_run):
                packages.append(blackfong_shell_pkg)
            apt_install(target_root, packages, with_recommends=with_recommends, dry_run=dry_run)
        finally:
            umount_chroot_binds(target_root, dry_run=dry_run)

        logger.info("Desktop stack installed (desktop_base=%s)", desktop_base)
        return state
