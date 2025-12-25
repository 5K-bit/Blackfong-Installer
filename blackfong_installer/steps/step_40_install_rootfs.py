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

        # Debian debootstrap arch values: amd64, arm64, armhf align with our normalized arch.
        suite = cfg.get("debian_suite", "stable")
        mirror = cfg.get("debian_mirror", "http://deb.debian.org/debian")

        debootstrap_rootfs(target_root=target_root, suite=suite, mirror=mirror, arch=arch, dry_run=dry_run)

        # Offline-first: if caller provides an on-media repo path, prefer it.
        offline_repo = cfg.get("offline_repo_path")
        if offline_repo:
            write_sources_list_offline(
                target_root,
                offline_repo,
                suite=str(cfg.get("offline_repo_suite", "bookworm")),
                component=str(cfg.get("offline_repo_component", "main")),
            )

        mount_chroot_binds(target_root, dry_run=dry_run)
        try:
            apt_update(target_root, dry_run=dry_run)
            # Minimal base tools needed for later steps
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

        logger.info("Rootfs installed at %s", target_root)
        return state
