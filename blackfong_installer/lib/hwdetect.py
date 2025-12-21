from __future__ import annotations

import logging
import platform
from pathlib import Path
from typing import Any, Dict

from .command import run_cmd
from .firmware import detect_firmware

logger = logging.getLogger(__name__)


def normalize_arch(machine: str) -> str:
    m = machine.lower()
    return {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "armv7l": "armhf",
        "armv6l": "armhf",
    }.get(m, m)


def detect_hardware(dry_run: bool = False) -> Dict[str, Any]:
    machine = platform.machine()
    arch = normalize_arch(machine)

    hw: Dict[str, Any] = {
        "arch": arch,
        "cpu_model": platform.processor() or "unknown",
        "firmware": detect_firmware(),
    }

    # RAM (best-effort)
    try:
        mem_kb = 0
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                mem_kb = int(line.split()[1])
                break
        if mem_kb:
            hw["ram_mb"] = mem_kb // 1024
    except Exception:
        pass

    # Disks (best-effort)
    try:
        r = run_cmd(["lsblk", "-J", "-o", "NAME,SIZE,TYPE,RM,TRAN"], check=True, dry_run=dry_run)
        hw["lsblk_json"] = r.stdout  # raw for support/repro
    except Exception:
        # keep going
        pass

    # Minimal default profile selection (real project can evolve rule engine)
    if arch == "amd64":
        hw["profile"] = "amd64-pc"
    elif arch == "arm64":
        hw["profile"] = "arm64-pi"
    else:
        hw["profile"] = "armhf-legacy"

    logger.info("Hardware: arch=%s firmware=%s profile=%s", hw.get("arch"), hw.get("firmware"), hw.get("profile"))
    return hw
