from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PartitionFilesystemStep:
    step_id = "20_partition_fs"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.setdefault("config", {})
        exe = state.setdefault("execution", {})

        # Placeholder: this is where GPT partitioning, formatting ext4, swap, and mounts happen.
        target_disk = cfg.get("target_disk")
        partitioning = cfg.get("partitioning", "auto")
        swap = cfg.get("swap", "auto")

        mounts = exe.setdefault("mounts", {})
        mounts.setdefault("target_root", "/target")
        mounts.setdefault("boot", "/target/boot")

        logger.info(
            "Partition plan: target_disk=%s mode=%s swap=%s (placeholder)",
            target_disk,
            partitioning,
            swap,
        )
        return state
