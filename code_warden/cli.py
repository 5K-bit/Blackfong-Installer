from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .audit import AuditLogger, audit_event
from .exec import parse_command, run_in_workspace
from .fs import Workspace, WorkspaceViolation
from .patch import PatchError, apply_file_patch, parse_warden_patch


def _workspace_from_args(args: argparse.Namespace) -> Workspace:
    if not args.workspace:
        raise SystemExit("--workspace is required")
    return Workspace.from_path(args.workspace)


def _audit_from_args(ws: Workspace, args: argparse.Namespace) -> AuditLogger:
    if args.audit_log:
        return AuditLogger(path=Path(args.audit_log).expanduser())
    return AuditLogger.default_for_workspace(ws.root)


def cmd_ls(args: argparse.Namespace) -> int:
    ws = _workspace_from_args(args)
    audit = _audit_from_args(ws, args)
    rel = args.path or "."
    try:
        items = ws.list_dir(rel, include_hidden=bool(args.all))
        for it in items:
            print(it)
        audit.log(audit_event(action="ls", ok=True, details={"path": rel, "count": len(items)}))
        return 0
    except Exception as e:
        audit.log(audit_event(action="ls", ok=False, details={"path": rel}, error=str(e)))
        raise


def cmd_read(args: argparse.Namespace) -> int:
    ws = _workspace_from_args(args)
    audit = _audit_from_args(ws, args)
    try:
        txt = ws.read_text(args.path)
        sys.stdout.write(txt)
        if txt and not txt.endswith("\n"):
            sys.stdout.write("\n")
        audit.log(audit_event(action="read", ok=True, details={"path": args.path, "bytes": len(txt.encode("utf-8"))}))
        return 0
    except Exception as e:
        audit.log(audit_event(action="read", ok=False, details={"path": args.path}, error=str(e)))
        raise


def cmd_write(args: argparse.Namespace) -> int:
    ws = _workspace_from_args(args)
    audit = _audit_from_args(ws, args)
    content = sys.stdin.read()
    try:
        ws.write_text(args.path, content)
        audit.log(
            audit_event(
                action="write",
                ok=True,
                details={"path": args.path, "bytes": len(content.encode("utf-8"))},
            )
        )
        return 0
    except Exception as e:
        audit.log(audit_event(action="write", ok=False, details={"path": args.path}, error=str(e)))
        raise


def cmd_apply(args: argparse.Namespace) -> int:
    ws = _workspace_from_args(args)
    audit = _audit_from_args(ws, args)
    patch_text = sys.stdin.read()
    try:
        fp = parse_warden_patch(patch_text)
        apply_file_patch(ws, fp, allow_overwrite=bool(args.force))
        audit.log(audit_event(action="apply_patch", ok=True, details={"op": fp.op, "path": fp.path, "mode": fp.mode}))
        return 0
    except Exception as e:
        audit.log(audit_event(action="apply_patch", ok=False, error=str(e)))
        raise


def cmd_run(args: argparse.Namespace) -> int:
    ws = _workspace_from_args(args)
    audit = _audit_from_args(ws, args)
    argv = args.command
    if not argv:
        raise SystemExit("run: provide a command after --")
    try:
        res = run_in_workspace(argv, cwd=str(ws.root), timeout_s=float(args.timeout))
        sys.stdout.write(res.stdout)
        sys.stderr.write(res.stderr)
        audit.log(
            audit_event(
                action="run",
                ok=res.returncode == 0,
                details={"argv": res.argv, "returncode": res.returncode, "timeout": args.timeout},
            )
        )
        return int(res.returncode)
    except Exception as e:
        audit.log(audit_event(action="run", ok=False, details={"argv": argv, "timeout": args.timeout}, error=str(e)))
        raise


HELP_REPL = """\
Code Warden REPL (workspace-scoped)

Slash commands:
  /ls [path]            list directory
  /read <path>          print a file
  /write <path>         write file from multi-line input (end with a single dot on its own line)
  /apply                apply a patch (paste until '*** End Patch')
  /run <cmd...>         run a command in the workspace
  /help                 show this help
  /exit                 quit

Notes:
  - Paths must be relative to the workspace root.
  - This REPL is designed so an LLM backend can later emit /apply patches and /run commands.
"""


def cmd_repl(args: argparse.Namespace) -> int:
    ws = _workspace_from_args(args)
    audit = _audit_from_args(ws, args)
    print(HELP_REPL)

    while True:
        try:
            line = input("warden> ").strip()
        except EOFError:
            print()
            return 0
        if not line:
            continue
        if not line.startswith("/"):
            print("No LLM backend wired yet. Use /help for commands.")
            continue

        if line in {"/exit", "/quit"}:
            return 0
        if line == "/help":
            print(HELP_REPL)
            continue

        parts = line.split(maxsplit=1)
        cmd = parts[0][1:]
        rest = parts[1] if len(parts) == 2 else ""

        try:
            if cmd == "ls":
                target = rest or "."
                for it in ws.list_dir(target, include_hidden=bool(args.all)):
                    print(it)
                audit.log(audit_event(action="repl_ls", ok=True, details={"path": target}))
                continue

            if cmd == "read":
                if not rest:
                    print("usage: /read <path>")
                    continue
                txt = ws.read_text(rest)
                sys.stdout.write(txt)
                if txt and not txt.endswith("\n"):
                    sys.stdout.write("\n")
                audit.log(audit_event(action="repl_read", ok=True, details={"path": rest}))
                continue

            if cmd == "write":
                if not rest:
                    print("usage: /write <path>")
                    continue
                print("Enter file content. End with a single '.' line.")
                buf: list[str] = []
                while True:
                    ln = input()
                    if ln == ".":
                        break
                    buf.append(ln)
                ws.write_text(rest, "\n".join(buf) + ("\n" if buf else ""))
                audit.log(audit_event(action="repl_write", ok=True, details={"path": rest, "lines": len(buf)}))
                continue

            if cmd == "apply":
                print("Paste patch. End with '*** End Patch' line.")
                buf: list[str] = []
                while True:
                    ln = input()
                    buf.append(ln)
                    if ln.strip() == "*** End Patch":
                        break
                fp = parse_warden_patch("\n".join(["*** Begin Patch", *buf]) if (buf and buf[0].strip() != "*** Begin Patch") else "\n".join(buf))
                apply_file_patch(ws, fp, allow_overwrite=bool(args.force))
                print(f"Applied: {fp.op} {fp.path} ({fp.mode})")
                audit.log(audit_event(action="repl_apply", ok=True, details={"op": fp.op, "path": fp.path, "mode": fp.mode}))
                continue

            if cmd == "run":
                if not rest:
                    print("usage: /run <cmd...>")
                    continue
                argv = parse_command(rest)
                res = run_in_workspace(argv, cwd=str(ws.root), timeout_s=float(args.timeout))
                sys.stdout.write(res.stdout)
                sys.stderr.write(res.stderr)
                audit.log(
                    audit_event(
                        action="repl_run",
                        ok=res.returncode == 0,
                        details={"argv": res.argv, "returncode": res.returncode, "timeout": args.timeout},
                    )
                )
                continue

            print(f"Unknown command: /{cmd} (use /help)")
        except (WorkspaceViolation, PatchError) as e:
            print(f"ERROR: {e}")
            audit.log(audit_event(action="repl_error", ok=False, details={"cmd": line}, error=str(e)))
        except Exception as e:
            print(f"ERROR: {e}")
            audit.log(audit_event(action="repl_error", ok=False, details={"cmd": line}, error=str(e)))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="code-warden")
    p.add_argument("--workspace", help="Workspace root (required)")
    p.add_argument("--audit-log", help="Audit log path (defaults to <workspace>/.code-warden/audit.jsonl)")
    p.add_argument("--timeout", default="30", help="Command timeout seconds (default: 30)")
    p.add_argument("--force", action="store_true", help="Allow overwriting files when applying patches")
    p.add_argument("-a", "--all", action="store_true", help="Include dotfiles in /ls")

    sub = p.add_subparsers(dest="subcmd", required=True)

    sp = sub.add_parser("repl", help="Interactive REPL")
    sp.set_defaults(func=cmd_repl)

    sp = sub.add_parser("ls", help="List directory")
    sp.add_argument("path", nargs="?", default=".")
    sp.set_defaults(func=cmd_ls)

    sp = sub.add_parser("read", help="Read a file to stdout")
    sp.add_argument("path")
    sp.set_defaults(func=cmd_read)

    sp = sub.add_parser("write", help="Write a file from stdin")
    sp.add_argument("path")
    sp.set_defaults(func=cmd_write)

    sp = sub.add_parser("apply", help="Apply a Warden patch from stdin")
    sp.set_defaults(func=cmd_apply)

    sp = sub.add_parser("run", help="Run a command in the workspace")
    sp.add_argument("command", nargs=argparse.REMAINDER, help="Command; use: code-warden run -- <cmd...>")
    sp.set_defaults(func=cmd_run)

    return p


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

