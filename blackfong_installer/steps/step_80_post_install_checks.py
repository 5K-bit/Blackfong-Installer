from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PostInstallChecksStep:
    step_id = "80_post_install_checks"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        exe = state.get("execution") or {}
        mounts = exe.get("mounts") or {}
        target_root = mounts.get("target_root")
        if not target_root:
            raise RuntimeError("execution.mounts.target_root missing")

        # Basic filesystem sanity checks
        must_exist = [
            "etc",
            "boot",
        ]
        for rel in must_exist:
            p = Path(target_root) / rel
            if not p.exists():
                raise RuntimeError(f"Post-install check failed: missing {p}")

        logger.info("Post-install checks passed (basic)")
        return state
