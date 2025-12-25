from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple

from .fs import Workspace


PatchOp = Literal["add", "update"]


class PatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class FilePatch:
    op: PatchOp
    path: str
    # For "add": full content
    # For "update": either full content (mode="full") or hunk-apply mode.
    content: str
    mode: Literal["full", "hunks"] = "full"
    hunks: Optional[List[Tuple[str, str]]] = None  # list of (old_text, new_text)


def parse_warden_patch(text: str) -> FilePatch:
    """Parse a minimal patch format.

    Supported:
      - Add file:
        *** Begin Patch
        *** Add File: path/rel.txt
        +line
        +line2
        *** End Patch

      - Update file (FULL replace):
        *** Begin Patch
        *** Update File: path/rel.txt
        @@ FULL
        +entire new file line1
        +line2
        *** End Patch

      - Update file (HUNKS replace):
        *** Begin Patch
        *** Update File: path/rel.txt
        @@
         context
        -old
        +new
         context
        @@
        ...
        *** End Patch

    In hunks mode, each hunk is applied by searching for the old_text block and replacing with new_text.
    """

    lines = text.splitlines()
    if not lines or lines[0].strip() != "*** Begin Patch":
        raise PatchError("Patch must start with '*** Begin Patch'")
    if lines[-1].strip() != "*** End Patch":
        raise PatchError("Patch must end with '*** End Patch'")

    i = 1
    header = None
    while i < len(lines) - 1 and not lines[i].startswith("*** "):
        i += 1
    if i >= len(lines) - 1:
        raise PatchError("Missing patch header (Add File / Update File)")

    header = lines[i].strip()
    i += 1

    if header.startswith("*** Add File:"):
        path = header.split(":", 1)[1].strip()
        content_lines: List[str] = []
        for ln in lines[i:-1]:
            if not ln.startswith("+"):
                raise PatchError("Add File body must use '+' lines only")
            content_lines.append(ln[1:])
        return FilePatch(op="add", path=path, content="\n".join(content_lines) + ("\n" if content_lines else ""))

    if header.startswith("*** Update File:"):
        path = header.split(":", 1)[1].strip()
        # Look for @@ FULL
        if i < len(lines) - 1 and lines[i].strip() == "@@ FULL":
            i += 1
            content_lines: List[str] = []
            for ln in lines[i:-1]:
                if not ln.startswith("+"):
                    raise PatchError("FULL update body must use '+' lines only")
                content_lines.append(ln[1:])
            return FilePatch(
                op="update",
                path=path,
                content="\n".join(content_lines) + ("\n" if content_lines else ""),
                mode="full",
            )

        # Otherwise treat as hunks.
        hunks: List[Tuple[str, str]] = []
        old_lines: List[str] = []
        new_lines: List[str] = []
        in_hunk = False
        saw_change = False

        def flush() -> None:
            nonlocal old_lines, new_lines, in_hunk, saw_change
            if in_hunk:
                old = "\n".join(old_lines) + ("\n" if old_lines else "")
                new = "\n".join(new_lines) + ("\n" if new_lines else "")
                if saw_change:
                    hunks.append((old, new))
            old_lines = []
            new_lines = []
            in_hunk = False
            saw_change = False

        for ln in lines[i:-1]:
            if ln.startswith("@@"):
                flush()
                in_hunk = True
                continue
            if not in_hunk:
                # ignore preamble whitespace
                if not ln.strip():
                    continue
                raise PatchError("Update hunks must start with '@@'")
            if ln.startswith(" "):
                old_lines.append(ln[1:])
                new_lines.append(ln[1:])
            elif ln.startswith("-"):
                old_lines.append(ln[1:])
                saw_change = True
            elif ln.startswith("+"):
                new_lines.append(ln[1:])
                saw_change = True
            else:
                raise PatchError("Invalid hunk line prefix (expected ' ', '+', '-')")
        flush()
        if not hunks:
            raise PatchError("No applicable hunks found")
        return FilePatch(op="update", path=path, content="", mode="hunks", hunks=hunks)

    raise PatchError(f"Unknown patch header: {header}")


def apply_file_patch(ws: Workspace, fp: FilePatch, *, allow_overwrite: bool = False) -> None:
    path = fp.path.strip()
    if not path:
        raise PatchError("Empty patch path")

    if fp.op == "add":
        if ws.exists(path) and not allow_overwrite:
            raise PatchError(f"File already exists: {path}")
        ws.write_text(path, fp.content)
        return

    if fp.op == "update":
        if fp.mode == "full":
            ws.write_text(path, fp.content)
            return
        if fp.mode == "hunks":
            original = ws.read_text(path)
            cur = original
            assert fp.hunks is not None
            for old, new in fp.hunks:
                idx = cur.find(old)
                if idx == -1:
                    raise PatchError(f"Failed to apply hunk: old block not found in {path}")
                # Ensure uniqueness to keep it honest.
                if cur.find(old, idx + 1) != -1:
                    raise PatchError(f"Failed to apply hunk: old block not unique in {path}")
                cur = cur.replace(old, new, 1)
            ws.write_text(path, cur)
            return

    raise PatchError(f"Unsupported operation: {fp.op}")

