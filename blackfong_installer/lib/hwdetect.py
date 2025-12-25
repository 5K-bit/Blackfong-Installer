from __future__ import annotations

import logging
import platform
from pathlib import Path
from typing import Any, Dict

from .command import run_cmd
from .firmware import detect_firmware

logger = logging.getLogger(__name__)

_GPU_VENDOR_MAP = {
    "0x8086": "intel",
    "0x1002": "amd",
    "0x10de": "nvidia",
    "0x13b5": "arm",  # Arm (Mali)
    "0x5143": "qualcomm",  # Qualcomm / Adreno (sometimes)
}


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

def _detect_camera() -> Dict[str, Any]:
    """Best-effort camera presence detection.

    Meaningful signal:
    - If we can see any V4L2 nodes (/dev/video* or /sys/class/video4linux/*), treat camera as present.
    - Otherwise camera is absent, and camera-related packages/services must not be installed/enabled.
    """

    dev = Path("/dev")
    sys_v4l = Path("/sys/class/video4linux")

    dev_nodes = sorted([p.name for p in dev.glob("video*") if p.name.startswith("video")])
    sys_nodes = sorted([p.name for p in sys_v4l.glob("*")]) if sys_v4l.exists() else []

    present = bool(dev_nodes or sys_nodes)
    return {
        "present": present,
        "dev_nodes": dev_nodes,
        "sys_nodes": sys_nodes,
    }


def _detect_gpu(*, dry_run: bool) -> Dict[str, Any]:
    """Best-effort GPU detection with a stable, actionable schema."""

    gpu: Dict[str, Any] = {
        "present": False,
        "vendor": "unknown",
        "vendor_id": None,
        "driver": None,
        "render_node_present": Path("/dev/dri/renderD128").exists(),
        "raw": {},
    }

    # Preferred path: /sys/class/drm (works on most modern kernels, including ARM).
    drm = Path("/sys/class/drm")
    cards = sorted([p for p in drm.glob("card[0-9]*") if p.is_dir()]) if drm.exists() else []
    gpu["raw"]["drm_cards"] = [c.name for c in cards]
    if cards:
        gpu["present"] = True
        dev = cards[0] / "device"
        vendor_id = None
        try:
            vendor_id = (dev / "vendor").read_text(encoding="utf-8").strip()
        except Exception:
            vendor_id = None
        if vendor_id:
            gpu["vendor_id"] = vendor_id
            gpu["vendor"] = _GPU_VENDOR_MAP.get(vendor_id.lower(), "unknown")

        # driver: /sys/class/drm/card0/device/driver -> .../drivers/amdgpu
        try:
            driver_link = dev / "driver"
            if driver_link.exists():
                gpu["driver"] = driver_link.resolve().name
        except Exception:
            pass

    # Optional enrichment on amd64: lspci can provide vendor strings.
    if platform.system().lower() == "linux":
        try:
            r = run_cmd(["lspci", "-nn"], check=False, dry_run=dry_run)
            if r.stdout:
                lines = [ln for ln in r.stdout.splitlines() if any(x in ln.lower() for x in ("vga", "3d", "display"))]
                if lines:
                    gpu["raw"]["lspci_display"] = lines
                    gpu["present"] = True
        except Exception:
            pass

    return gpu


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

    # GPU + camera signals that materially affect what we install/enable.
    hw["gpu"] = _detect_gpu(dry_run=dry_run)
    hw["camera"] = _detect_camera()

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
