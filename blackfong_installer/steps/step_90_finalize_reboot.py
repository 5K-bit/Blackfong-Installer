from __future__ import annotations

import logging
from typing import Any, Dict

from ..lib.command import run_cmd

logger = logging.getLogger(__name__)


class FinalizeRebootStep:
    step_id = "90_finalize_reboot"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("config") or {}
        exe = state.get("execution") or {}
        mounts = exe.get("mounts") or {}
        target_root = mounts.get("target_root")
        dry_run = bool(cfg.get("dry_run", False))

        logger.info("Finalize summary: %s", (state.get("execution") or {}).get("decisions") or {})

        # Unmounting and reboot are operational and should be explicitly enabled.
        # For a real installer environment, set config.finalize_reboot=true.
        if bool(cfg.get("finalize_reboot", False)):
            # best-effort unmount
            for p in [
                f"{target_root}/boot/efi",
                f"{target_root}/boot",
                f"{target_root}",
            ]:
                if p:
                    run_cmd(["umount", "-lf", p], check=False, dry_run=dry_run)
            run_cmd(["sync"], dry_run=dry_run)
            run_cmd(["reboot"], dry_run=dry_run)

        return state
