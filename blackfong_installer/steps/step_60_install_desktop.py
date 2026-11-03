from __future__ import annotations

import logging
from typing import Any, Dict

from ..lib import distro
from ..lib.chroot import chroot_cmd, mount_chroot_binds, umount_chroot_binds
from ..lib.command import run_cmd
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

        # Desktop base: Kubuntu 24.04 LTS + KDE Plasma with SDDM (O.B.E.O.S. v1 doctrine).
        # Unsupported values (including legacy xfce/xubuntu) raise instead of installing
        # a different desktop than the one that was asked for.
        desktop_base = distro.normalize_desktop_base(cfg.get("desktop_base", "kubuntu"))
        code_warden_enabled = bool(cfg.get("code_warden_enabled", False))

        # Baseline audio/media stack.
        packages: list[str] = ["pipewire", "wireplumber", "gstreamer1.0-tools"]
        packages += list(distro.KUBUNTU_PACKAGES)

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
            # Make SDDM the display manager without an interactive debconf prompt.
            run_cmd(
                ["chroot", target_root, "debconf-set-selections"],
                input_text=distro.DEBCONF_DISPLAY_MANAGER,
                dry_run=dry_run,
            )
            if blackfong_shell_pkg and apt_has_package(target_root, blackfong_shell_pkg, dry_run=dry_run):
                packages.append(blackfong_shell_pkg)
            # Recommends stay on: Kubuntu's session depends on them (themes, settings modules).
            apt_install(target_root, packages, with_recommends=True, dry_run=dry_run)
            chroot_cmd(target_root, ["systemctl", "set-default", "graphical.target"], dry_run=dry_run)
        finally:
            umount_chroot_binds(target_root, dry_run=dry_run)

        logger.info(
            "Desktop stack installed (desktop_base=%s code_warden_enabled=%s)",
            desktop_base,
            code_warden_enabled,
        )
        return state
