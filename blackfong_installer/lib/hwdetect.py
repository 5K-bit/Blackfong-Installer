from __future__ import annotations

import logging
import platform
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

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


def _read_text(path: Path) -> Optional[str]:
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore").strip()
        return txt or None
    except Exception:
        return None


def _detect_identity() -> Dict[str, Any]:
    """Collect host identity signals (best-effort).

    These are used by the profile rule engine to distinguish PC vs Steam Deck vs SBC models.
    """

    dmi = Path("/sys/class/dmi/id")
    dt = Path("/sys/firmware/devicetree/base")

    identity: Dict[str, Any] = {
        "dmi": {
            "sys_vendor": _read_text(dmi / "sys_vendor"),
            "product_name": _read_text(dmi / "product_name"),
            "product_version": _read_text(dmi / "product_version"),
            "board_name": _read_text(dmi / "board_name"),
        },
        "device_tree": {
            "model": _read_text(dt / "model") or _read_text(Path("/proc/device-tree/model")),
        },
        "virtualization": {
            "product_name_hint": _read_text(dmi / "product_name"),
        },
    }
    return identity


def _pick_profile(hw: Dict[str, Any], *, forced_profile: Optional[str]) -> Tuple[str, Dict[str, Any]]:
    """Rule engine: pick best profile + record why."""

    if forced_profile:
        return forced_profile, {"confidence": 1.0, "reason": "forced_profile", "evidence": {"forced_profile": forced_profile}}

    arch = str(hw.get("arch") or "")
    identity = hw.get("identity") or {}
    dmi = (identity.get("dmi") or {}) if isinstance(identity, dict) else {}
    dt = (identity.get("device_tree") or {}) if isinstance(identity, dict) else {}

    sys_vendor = str(dmi.get("sys_vendor") or "").lower()
    product_name = str(dmi.get("product_name") or "").lower()
    board_name = str(dmi.get("board_name") or "").lower()
    dt_model = str(dt.get("model") or "").lower()

    # Steam Deck (Jupiter/Galileo). Typically reports Valve in DMI.
    if arch == "amd64":
        if ("valve" in sys_vendor) or ("steam deck" in product_name) or ("jupiter" in product_name) or ("galileo" in product_name):
            return "amd64-steamdeck", {
                "confidence": 0.95,
                "reason": "dmi_matches_steamdeck",
                "evidence": {"sys_vendor": sys_vendor, "product_name": product_name},
            }
        return "amd64-pc", {
            "confidence": 0.75,
            "reason": "amd64_default",
            "evidence": {"sys_vendor": sys_vendor, "product_name": product_name},
        }

    # ARM64 SBCs: device-tree model is the most reliable signal.
    if arch == "arm64":
        if "uconsole" in dt_model or "clockwork" in dt_model:
            return "arm64-uconsole", {
                "confidence": 0.9,
                "reason": "device_tree_matches_uconsole",
                "evidence": {"model": dt_model},
            }
        if "raspberry pi" in dt_model:
            return "arm64-pi", {
                "confidence": 0.9,
                "reason": "device_tree_matches_rpi",
                "evidence": {"model": dt_model},
            }
        # Unknown ARM64 SBC: prefer the Pi profile as the most conservative baseline today.
        return "arm64-pi", {
            "confidence": 0.55,
            "reason": "arm64_fallback",
            "evidence": {"model": dt_model},
        }

    # ARMHF legacy: keep explicit legacy profile.
    if arch == "armhf":
        return "armhf-legacy", {"confidence": 0.7, "reason": "armhf_default", "evidence": {"model": dt_model}}

    return "amd64-pc", {"confidence": 0.3, "reason": "unknown_arch_fallback", "evidence": {"arch": arch, "board_name": board_name}}

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


def detect_hardware(dry_run: bool = False, *, forced_profile: Optional[str] = None) -> Dict[str, Any]:
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

    # Identity signals: used by profile rule engine.
    hw["identity"] = _detect_identity()

    # Disks (best-effort)
    try:
        r = run_cmd(["lsblk", "-J", "-o", "NAME,SIZE,TYPE,RM,TRAN"], check=True, dry_run=dry_run)
        hw["lsblk_json"] = r.stdout  # raw for support/repro
    except Exception:
        # keep going
        pass

    profile, why = _pick_profile(hw, forced_profile=forced_profile)
    hw["profile"] = profile
    hw["profile_selection"] = why

    logger.info("Hardware: arch=%s firmware=%s profile=%s", hw.get("arch"), hw.get("firmware"), hw.get("profile"))
    return hw
