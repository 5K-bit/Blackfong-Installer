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

        # Desktop base:
        # - OS boots into XFCE ("Xubuntu-style") by default.
        # - Code Warden is an optional in-OS capability installed alongside XFCE.
        desktop_base = str(cfg.get("desktop_base", "xubuntu")).strip().lower()
        code_warden_enabled = bool(cfg.get("code_warden_enabled", False))

        # Baseline audio/media stack.
        packages: list[str] = ["pipewire", "wireplumber", "gstreamer1.0-tools"]

        with_recommends = False

        # Xubuntu-style base (XFCE + Xorg + display manager).
        # NOTE: On Debian this is provided by task/meta packages (not Ubuntu's xubuntu-desktop).
        if desktop_base in {"xubuntu", "xfce", "xfce4"}:
            packages += [
                "task-xfce-desktop",
                "lightdm",
                "network-manager-gnome",
            ]
            with_recommends = True
        else:
            # If someone sets a non-xfce desktop_base today, do not silently install nothing.
            # Keep behavior honest: install XFCE baseline unless/ until more desktop bases exist.
            packages += [
                "task-xfce-desktop",
                "lightdm",
                "network-manager-gnome",
            ]
            with_recommends = True

        # Code Warden: terminal-first toolset available within the OS.
        if code_warden_enabled:
            packages += [
                "sway",
                "foot",
                "waybar",
                "wofi",
                "xwayland",
                "wl-clipboard",
            ]

        # Optional: Blackfong shell (only if repo provides it).
        blackfong_shell_pkg = str(cfg.get("blackfong_shell_package", "blackfong-code-warden-shell")).strip()

        mount_chroot_binds(target_root, dry_run=dry_run)
        try:
            apt_update(target_root, dry_run=dry_run)
            if blackfong_shell_pkg and apt_has_package(target_root, blackfong_shell_pkg, dry_run=dry_run):
                packages.append(blackfong_shell_pkg)
            apt_install(target_root, packages, with_recommends=with_recommends, dry_run=dry_run)
        finally:
            umount_chroot_binds(target_root, dry_run=dry_run)

        logger.info(
            "Desktop stack installed (desktop_base=%s code_warden_enabled=%s)",
            desktop_base,
            code_warden_enabled,
        )
        return state
