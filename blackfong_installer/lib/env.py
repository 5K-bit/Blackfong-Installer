from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Paths:
    target_root: str = "/target"
    state_default: str = "/var/lib/blackfong-installer/state.json"
    log_default: str = "/var/log/blackfong-installer.log"


PATHS = Paths()
