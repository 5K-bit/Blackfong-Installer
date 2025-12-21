from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_build_state(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("build_state.json must contain an object")
    return data


def save_build_state(path: str, state: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ensure_build_defaults(state: Dict[str, Any]) -> Dict[str, Any]:
    state.setdefault("completed", {})
    state.setdefault("targets", {})
    return state


def mark_completed(state: Dict[str, Any], *, target: str, step_id: str) -> None:
    t = state.setdefault("targets", {}).setdefault(target, {})
    completed = t.setdefault("completed_steps", [])
    if step_id not in completed:
        completed.append(step_id)


def is_completed(state: Dict[str, Any], *, target: str, step_id: str) -> bool:
    t = (state.get("targets") or {}).get(target) or {}
    return step_id in (t.get("completed_steps") or [])
