from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class InstallRootFSStep:
    step_id = "40_install_rootfs"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        exe = state.setdefault("execution", {})
        mounts = exe.get("mounts") or {}
        target_root = mounts.get("target_root", "/target")

        # Placeholder: debootstrap + base packages from manifests/base.yaml
        logger.info("Installing minimal Debian-based rootfs to %s (placeholder)", target_root)
        return state
