"""Code Warden: a workspace-scoped coding agent shell.

This package intentionally starts with a "safe core":
- Workspace-scoped filesystem access (no traversal outside the allowed root)
- Audit logging of actions
- A patch format that can be produced by an LLM and applied deterministically
- A command runner restricted to the workspace (with timeouts)

LLM backends can be integrated later without changing the safety model.
"""

from __future__ import annotations

__all__ = []

