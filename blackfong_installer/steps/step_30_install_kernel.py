from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


KERNEL_BY_ARCH = {
    "arm64": "linux-image-arm64",
    "armhf": "linux-image-armhf",
    "amd64": "linux-image-amd64",
}


class InstallKernelStep:
    step_id = "30_install_kernel"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        hw = state.get("hardware") or {}
        arch = hw.get("arch")
        if not arch:
            raise RuntimeError("hardware.arch is missing; run detect step first")

        kernel_pkg = KERNEL_BY_ARCH.get(arch)
        if not kernel_pkg:
            raise RuntimeError(f"Unsupported arch for kernel selection: {arch}")

        state.setdefault("execution", {}).setdefault("decisions", {})["kernel_package"] = kernel_pkg
        logger.info("Selected kernel package for arch=%s: %s", arch, kernel_pkg)

        # Placeholder: install boot tooling based on hw['firmware'] and hw['profile'].
        return state
