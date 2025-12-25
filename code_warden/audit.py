from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AuditLogger:
    path: Path

    @classmethod
    def default_for_workspace(cls, workspace_root: Path) -> "AuditLogger":
        p = (workspace_root / ".code-warden").resolve()
        p.mkdir(parents=True, exist_ok=True)
        return cls(path=p / "audit.jsonl")

    def log(self, event: Dict[str, Any]) -> None:
        event = dict(event)
        event.setdefault("ts", time.time())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8") if not self.path.exists() else None
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")


def audit_event(
    *,
    action: str,
    ok: bool,
    details: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    e: Dict[str, Any] = {"action": action, "ok": ok}
    if details:
        e["details"] = details
    if error:
        e["error"] = error
    return e

