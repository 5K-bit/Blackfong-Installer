from __future__ import annotations

import logging
from typing import Any, Dict

from ..lib.hwdetect import detect_hardware
from ..lib.manifests import load_profile

logger = logging.getLogger(__name__)


class DetectHardwareStep:
    step_id = "10_detect_hardware"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("config") or {}
        dry_run = bool(cfg.get("dry_run", False))

        hw = detect_hardware(dry_run=dry_run)
        state["hardware"] = hw

        profile_id = hw.get("profile")
        if profile_id:
            # Profiles are declarative: opt-ins + defaults. They do not execute logic.
            state["profile"] = load_profile(str(profile_id))
        return state
