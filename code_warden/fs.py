from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class WorkspaceViolation(ValueError):
    pass


@dataclass(frozen=True)
class Workspace:
    root: Path

    @classmethod
    def from_path(cls, root: str | Path) -> "Workspace":
        p = Path(root).expanduser()
        try:
            p = p.resolve()
        except Exception:
            # If resolve fails (non-existent), normalize as absolute.
            p = p.absolute()
        return cls(root=p)

    def resolve_rel(self, rel: str | Path) -> Path:
        """Resolve a user-provided relative path within the workspace."""
        rp = Path(rel)
        if rp.is_absolute():
            raise WorkspaceViolation(f"Absolute paths are not allowed: {rel}")

        candidate = (self.root / rp).resolve()
        root = self.root
        try:
            root_rel = candidate.relative_to(root)
        except Exception as e:
            raise WorkspaceViolation(f"Path escapes workspace: {rel}") from e
        # Avoid oddities: disallow empty/parent traversal results.
        _ = root_rel  # kept for clarity
        return candidate

    def ensure_parent_dirs(self, rel: str | Path) -> Path:
        p = self.resolve_rel(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def read_text(self, rel: str | Path, *, max_bytes: int = 2_000_000) -> str:
        p = self.resolve_rel(rel)
        data = p.read_bytes()
        if len(data) > max_bytes:
            raise ValueError(f"Refusing to read >{max_bytes} bytes from {rel}")
        return data.decode("utf-8", errors="replace")

    def write_text(self, rel: str | Path, content: str) -> None:
        p = self.ensure_parent_dirs(rel)
        p.write_text(content, encoding="utf-8")

    def exists(self, rel: str | Path) -> bool:
        return self.resolve_rel(rel).exists()

    def list_dir(self, rel: str | Path = ".", *, include_hidden: bool = False) -> list[str]:
        p = self.resolve_rel(rel)
        if not p.exists():
            raise FileNotFoundError(str(rel))
        if not p.is_dir():
            raise NotADirectoryError(str(rel))
        out: list[str] = []
        for child in sorted(p.iterdir(), key=lambda c: c.name.lower()):
            if not include_hidden and child.name.startswith("."):
                continue
            suffix = "/" if child.is_dir() else ""
            out.append(child.name + suffix)
        return out

