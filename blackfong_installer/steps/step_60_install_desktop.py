from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class InstallDesktopStep:
    step_id = "60_install_desktop"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # Placeholder: install Wayland compositor + BDE shell + PipeWire defaults.
        logger.info("Installing BDE desktop stack (placeholder)")
        return state
