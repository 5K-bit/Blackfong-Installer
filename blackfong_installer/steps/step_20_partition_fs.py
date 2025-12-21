from __future__ import annotations

import logging
from typing import Any, Dict

from ..lib.env import PATHS
from ..lib.storage import PartitionPlan, partition_and_format

logger = logging.getLogger(__name__)


class PartitionFilesystemStep:
    step_id = "20_partition_fs"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.setdefault("config", {})
        hw = state.get("hardware") or {}
        exe = state.setdefault("execution", {})

        target_disk = cfg.get("target_disk")
        if not target_disk:
            raise RuntimeError("config.target_disk is required for partitioning")

        firmware = hw.get("firmware")
        if firmware not in {"efi", "uboot"}:
            raise RuntimeError(f"hardware.firmware must be 'efi' or 'uboot', got: {firmware}")

        dry_run = bool(cfg.get("dry_run", False))

        plan = PartitionPlan(
            disk=target_disk,
            firmware=firmware,
            swap_size_mib=None if cfg.get("swap", "auto") in {"none", None} else None,
        )

        target_root = (exe.get("mounts") or {}).get("target_root") or PATHS.target_root
        result = partition_and_format(plan=plan, target_root=target_root, dry_run=dry_run)

        exe.setdefault("mounts", {})["target_root"] = target_root
        exe["mounts"]["root_part"] = result.root_part
        exe["mounts"]["esp_part"] = result.esp_part
        exe["mounts"]["boot_part"] = result.boot_part

        logger.info("Partitioned and mounted target_root=%s", target_root)
        return state
