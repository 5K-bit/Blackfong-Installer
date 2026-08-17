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

        # OBEOS v1 ships one desktop doctrine: Kubuntu 24.04 LTS + KDE Plasma.
        # Legacy XFCE/Xubuntu values are migration inputs only and are rejected here
        # instead of silently installing the wrong desktop.
        desktop_base = str(cfg.get("desktop_base", "kubuntu-plasma")).strip().lower()
        if desktop_base not in {"kubuntu", "kubuntu-plasma", "plasma", "kde-plasma"}:
            raise RuntimeError(
                "OBEOS v1 shipping installer requires desktop_base=kubuntu-plasma; "
                f"got {desktop_base!r}"
            )

        code_warden_enabled = bool(cfg.get("code_warden_enabled", False))

        packages: list[str] = [
            "kubuntu-desktop",
            "plasma-workspace",
            "sddm",
            "network-manager",
            "pipewire",
            "wireplumber",
            "gstreamer1.0-tools",
        ]
        with_recommends = True

        # Code Warden remains an optional developer/operator capability inside Plasma.
        # It does not replace the shipping desktop/session authority.
        if code_warden_enabled:
            packages += [
                "sway",
                "foot",
                "waybar",
                "wofi",
                "xwayland",
                "wl-clipboard",
            ]

        blackfong_shell_pkg = str(cfg.get("blackfong_shell_package", "blackfong-code-warden-shell")).strip()

        mount_chroot_binds(target_root, dry_run=dry_run)
        try:
            apt_update(target_root, dry_run=dry_run)
            if blackfong_shell_pkg and apt_has_package(target_root, blackfong_shell_pkg, dry_run=dry_run):
                packages.append(blackfong_shell_pkg)
            apt_install(target_root, packages, with_recommends=with_recommends, dry_run=dry_run)
        finally:
            umount_chroot_binds(target_root, dry_run=dry_run)

        state.setdefault("platform", {})
        state["platform"].update(
            {
                "desktop": "KDE Plasma",
                "display_manager": "SDDM",
                "desktop_base": "kubuntu-plasma",
                "session_authority": "OBEOS",
            }
        )
        logger.info(
            "OBEOS Plasma desktop installed (desktop_base=%s code_warden_enabled=%s)",
            desktop_base,
            code_warden_enabled,
        )
        return state
