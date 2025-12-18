from __future__ import annotations

import logging
import platform
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DetectHardwareStep:
    step_id = "10_detect_hardware"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        hw = state.setdefault("hardware", {})

        # Minimal, safe defaults. Real implementation should probe /proc, lspci, lsusb, drm, etc.
        machine = platform.machine().lower()
        arch = {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
            "armv7l": "armhf",
            "armv6l": "armhf",
        }.get(machine, machine)

        hw.setdefault("arch", arch)
        hw.setdefault("firmware", "efi" if arch == "amd64" else "uboot")
        hw.setdefault("cpu_model", platform.processor() or "unknown")

        # Profile selection (placeholder rule set)
        profile = "amd64-pc" if arch == "amd64" else "arm64-pi" if arch == "arm64" else "armhf-legacy"
        hw.setdefault("profile", profile)

        logger.info("Detected arch=%s firmware=%s profile=%s", hw.get("arch"), hw.get("firmware"), hw.get("profile"))
        return state
