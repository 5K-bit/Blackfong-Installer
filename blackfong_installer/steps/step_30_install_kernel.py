from __future__ import annotations

import logging
from typing import Any, Dict

from ..lib import distro
from ..lib.chroot import mount_chroot_binds, umount_chroot_binds
from ..lib.pkg import apt_install, apt_update

logger = logging.getLogger(__name__)


# Ubuntu kernel metapackage (see lib/distro.py); Debian's linux-image-amd64 does not exist on Ubuntu.
KERNEL_BY_ARCH = distro.KERNEL_BY_ARCH


class InstallKernelStep:
    step_id = "30_install_kernel"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("config") or {}
        hw = state.get("hardware") or {}
        exe = state.get("execution") or {}
        mounts = exe.get("mounts") or {}
        target_root = mounts.get("target_root")
        if not target_root:
            raise RuntimeError("execution.mounts.target_root missing; run partition step first")

        arch = hw.get("arch")
        if not arch:
            raise RuntimeError("hardware.arch is missing")

        kernel_pkg = distro.kernel_package(arch)

        state.setdefault("execution", {}).setdefault("decisions", {})["kernel_package"] = kernel_pkg

        dry_run = bool(cfg.get("dry_run", False))

        mount_chroot_binds(target_root, dry_run=dry_run)
        try:
            apt_update(target_root, dry_run=dry_run)
            apt_install(target_root, [kernel_pkg], dry_run=dry_run)
        finally:
            umount_chroot_binds(target_root, dry_run=dry_run)

        logger.info("Kernel installed: %s", kernel_pkg)
        return state
