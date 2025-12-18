"""GUI wrapper stub.

A real GUI (Wayland/GTK/Qt) should:
- Collect user config choices
- Write them into the shared state file under state['config']
- Call blackfong_installer.main.run(...)
- Display progress using log tailing or step callbacks (future)

This module exists to document the integration boundary.
"""

from __future__ import annotations

from blackfong_installer.main import run


def run_from_gui(*, state_path: str, log_path: str) -> None:
    run(state_path=state_path, log_path=log_path)
