from __future__ import annotations

import logging
from typing import Any, Dict

from ..lib.hwdetect import detect_hardware

logger = logging.getLogger(__name__)


class DetectHardwareStep:
    step_id = "10_detect_hardware"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("config") or {}
        dry_run = bool(cfg.get("dry_run", False))

        state["hardware"] = detect_hardware(dry_run=dry_run)
        return state
