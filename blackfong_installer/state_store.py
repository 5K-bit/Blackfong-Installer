from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)


def _detect_format(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    if ext in {"json", "yaml", "yml"}:
        return ext
    # Default to JSON for unknown extensions.
    return "json"


def load_state(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}

    fmt = _detect_format(p)
    data: Dict[str, Any]

    if fmt == "json":
        data = json.loads(p.read_text(encoding="utf-8"))
    elif fmt in {"yaml", "yml"}:
        try:
            import yaml  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "YAML state requested but PyYAML is not available. "
                "Use JSON state or add PyYAML to the live environment."
            ) from e
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    else:
        data = json.loads(p.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"State file must be an object/dict, got {type(data)}")

    return data


def save_state(path: str, state: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    fmt = _detect_format(p)
    if fmt == "json":
        p.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elif fmt in {"yaml", "yml"}:
        try:
            import yaml  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "YAML state requested but PyYAML is not available. "
                "Use JSON state or add PyYAML to the live environment."
            ) from e
        p.write_text(yaml.safe_dump(state, sort_keys=False) + "\n", encoding="utf-8")
    else:
        p.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ensure_defaults(state: Dict[str, Any]) -> Dict[str, Any]:
    """Fill required keys with sane defaults (without overriding user values)."""

    state.setdefault("version", "vNext 1.0")
    state.setdefault("config", {})
    state.setdefault("hardware", {})
    state.setdefault("execution", {})

    cfg = state["config"]
    cfg.setdefault("mode", "cli")
    cfg.setdefault("install_source", "offline")
    cfg.setdefault("firewall_enabled", True)
    cfg.setdefault("daise_device_access_enabled", True)
    cfg.setdefault("partitioning", "auto")
    cfg.setdefault("swap", "auto")
    # Target OS base.
    # - ubuntu: enables xubuntu-desktop and Ubuntu package naming.
    # - debian: keeps debootstrap+packages aligned with Debian.
    cfg.setdefault("os_base", "ubuntu")
    cfg.setdefault("ubuntu_suite", "noble")
    # Default mirror is selected per-arch (archive vs ports) in step_40_install_rootfs.
    cfg.setdefault("ubuntu_mirror", None)
    cfg.setdefault("debian_suite", "stable")
    cfg.setdefault("debian_mirror", "http://deb.debian.org/debian")
    # Desktop base: "xubuntu" means XFCE desktop stack on our Debian rootfs.
    cfg.setdefault("desktop_base", "xubuntu")

    exe = state["execution"]
    exe.setdefault("current_step", None)
    exe.setdefault("completed_steps", [])
    exe.setdefault("errors", [])

    return state


def mark_step_completed(state: Dict[str, Any], step_id: str) -> None:
    exe = state.setdefault("execution", {})
    completed = exe.setdefault("completed_steps", [])
    if step_id not in completed:
        completed.append(step_id)


def is_step_completed(state: Dict[str, Any], step_id: str) -> bool:
    exe = state.get("execution") or {}
    completed = exe.get("completed_steps") or []
    return step_id in completed
