from __future__ import annotations

import logging
from typing import Any, Dict

from ..lib.chroot import mount_chroot_binds, umount_chroot_binds
from ..lib.pkg import apt_has_package, apt_install, apt_update

logger = logging.getLogger(__name__)


DEBIAN_KERNEL_BY_ARCH = {
    "arm64": "linux-image-arm64",
    "armhf": "linux-image-armhf",
    "amd64": "linux-image-amd64",
}

UBUNTU_KERNEL_CANDIDATES_BY_ARCH = {
    # Ubuntu meta packages; order matters.
    "amd64": ["linux-generic", "linux-image-generic"],
    "arm64": ["linux-generic", "linux-image-generic"],
    # armhf support varies by Ubuntu release; try generic first.
    "armhf": ["linux-image-generic"],
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

        os_base = str(cfg.get("os_base", "ubuntu")).strip().lower()

        dry_run = bool(cfg.get("dry_run", False))

        mount_chroot_binds(target_root, dry_run=dry_run)
        try:
            apt_update(target_root, dry_run=dry_run)
            if os_base == "debian":
                kernel_pkg = DEBIAN_KERNEL_BY_ARCH.get(arch)
                if not kernel_pkg:
                    raise RuntimeError(f"Unsupported arch for kernel selection: {arch}")
            elif os_base == "ubuntu":
                candidates = UBUNTU_KERNEL_CANDIDATES_BY_ARCH.get(arch)
                if not candidates:
                    raise RuntimeError(f"Unsupported arch for Ubuntu kernel selection: {arch}")
                kernel_pkg = next((p for p in candidates if apt_has_package(target_root, p, dry_run=dry_run)), None)
                if not kernel_pkg:
                    raise RuntimeError(
                        f"No supported Ubuntu kernel meta package found for arch={arch}. "
                        f"Tried: {', '.join(candidates)}"
                    )
            else:
                raise RuntimeError(f"Unsupported config.os_base={os_base!r} (expected 'ubuntu' or 'debian')")

            state.setdefault("execution", {}).setdefault("decisions", {})["kernel_package"] = kernel_pkg
            apt_install(target_root, [kernel_pkg], with_recommends=True, dry_run=dry_run)
        finally:
            umount_chroot_binds(target_root, dry_run=dry_run)

        logger.info("Kernel installed: %s", kernel_pkg)
        return state
