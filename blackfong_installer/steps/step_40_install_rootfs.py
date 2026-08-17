from __future__ import annotations

import logging
from typing import Any, Dict

from ..lib.chroot import mount_chroot_binds, umount_chroot_binds
from ..lib.pkg import apt_install, apt_update, debootstrap_rootfs, write_sources_list_offline

logger = logging.getLogger(__name__)


class InstallRootFSStep:
    step_id = "40_install_rootfs"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("config") or {}
        hw = state.get("hardware") or {}
        exe = state.get("execution") or {}
        mounts = exe.get("mounts") or {}
        target_root = mounts.get("target_root")
        if not target_root:
            raise RuntimeError("execution.mounts.target_root missing; run partition step first")

        dry_run = bool(cfg.get("dry_run", False))
        arch = hw.get("arch")
        if not arch:
            raise RuntimeError("hardware.arch missing")

        # OBEOS v1 shipping doctrine is Ubuntu 24.04 LTS (Noble) with KDE Plasma.
        # Older Debian/Xubuntu inputs are migration-only and must not silently become
        # the installed target OS.
        base_distribution = str(cfg.get("base_distribution", "ubuntu")).strip().lower()
        if base_distribution not in {"ubuntu", "kubuntu"}:
            raise RuntimeError(
                "OBEOS v1 installer requires base_distribution=ubuntu (Kubuntu/Plasma target); "
                f"got {base_distribution!r}"
            )

        suite = str(cfg.get("ubuntu_suite", "noble")).strip().lower()
        if suite != "noble":
            raise RuntimeError(f"OBEOS v1 requires Ubuntu 24.04 LTS suite 'noble'; got {suite!r}")

        default_mirror = "http://archive.ubuntu.com/ubuntu" if arch == "amd64" else "http://ports.ubuntu.com/ubuntu-ports"
        mirror = str(cfg.get("ubuntu_mirror") or default_mirror)

        debootstrap_rootfs(target_root=target_root, suite=suite, mirror=mirror, arch=arch, dry_run=dry_run)

        # Offline-first remains supported, but the shipped repository must match Noble.
        offline_repo = cfg.get("offline_repo_path")
        if offline_repo:
            offline_suite = str(cfg.get("offline_repo_suite", suite))
            if offline_suite != suite:
                raise RuntimeError(
                    f"Offline repository suite {offline_suite!r} does not match OBEOS target suite {suite!r}"
                )
            write_sources_list_offline(
                target_root,
                offline_repo,
                suite=offline_suite,
                component=str(cfg.get("offline_repo_component", "main")),
            )

        mount_chroot_binds(target_root, dry_run=dry_run)
        try:
            apt_update(target_root, dry_run=dry_run)
            apt_install(
                target_root,
                [
                    "systemd",
                    "coreutils",
                    "ca-certificates",
                    "network-manager",
                    "openssh-server",
                    "sudo",
                    "linux-base",
                    "initramfs-tools",
                ],
                dry_run=dry_run,
            )
        finally:
            umount_chroot_binds(target_root, dry_run=dry_run)

        state.setdefault("platform", {})
        state["platform"].update(
            {
                "base_distribution": "Ubuntu",
                "release": "24.04 LTS",
                "suite": suite,
                "desktop": "KDE Plasma",
                "session_authority": "OBEOS",
            }
        )
        logger.info("OBEOS Kubuntu rootfs installed at %s (suite=%s arch=%s)", target_root, suite, arch)
        return state
