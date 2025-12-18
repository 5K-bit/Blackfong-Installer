from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class FinalizeRebootStep:
    step_id = "90_finalize_reboot"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # Placeholder: summary log, unmount, sync, reboot.
        logger.info("Finalizing installation and rebooting (placeholder)")
        return state
