from __future__ import annotations

import logging
from typing import Any, Dict

from ..lib.chroot import mount_chroot_binds, umount_chroot_binds
from ..lib.pkg import apt_install, apt_update

logger = logging.getLogger(__name__)


KERNEL_BY_ARCH = {
    "arm64": "linux-image-arm64",
    "armhf": "linux-image-armhf",
    "amd64": "linux-image-amd64",
}


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

        kernel_pkg = KERNEL_BY_ARCH.get(arch)
        if not kernel_pkg:
            raise RuntimeError(f"Unsupported arch for kernel selection: {arch}")

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
