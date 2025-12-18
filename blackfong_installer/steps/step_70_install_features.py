from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class InstallFeaturesStep:
    step_id = "70_install_features"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("config") or {}
        src = cfg.get("install_source", "offline")

        hw = state.get("hardware") or {}
        # Placeholder: install AI/ML, media; gate LoRa/haptics/camera by detection.
        logger.info(
            "Installing features (install_source=%s, lora=%s, haptics=%s, camera=%s) (placeholder)",
            src,
            (hw.get("lora") or {}).get("present") if isinstance(hw.get("lora"), dict) else hw.get("lora"),
            (hw.get("haptics") or {}).get("present") if isinstance(hw.get("haptics"), dict) else hw.get("haptics"),
            (hw.get("camera") or {}).get("present") if isinstance(hw.get("camera"), dict) else hw.get("camera"),
        )
        return state
