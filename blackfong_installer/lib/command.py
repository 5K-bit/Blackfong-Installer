from __future__ import annotations

import logging
import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CmdResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str


def _fmt_argv(argv: Sequence[str]) -> str:
    return " ".join(shlex.quote(a) for a in argv)


def run_cmd(
    argv: Sequence[str],
    *,
    check: bool = True,
    env: Mapping[str, str] | None = None,
    cwd: str | None = None,
    input_text: str | None = None,
    dry_run: bool = False,
) -> CmdResult:
    """Run a command with consistent logging.

    - Always logs the command.
    - Captures stdout/stderr for state recording if desired.
    - dry_run logs but does not execute.
    """

    argv_list = list(argv)
    logger.info("CMD %s", _fmt_argv(argv_list))

    if dry_run:
        return CmdResult(argv=argv_list, returncode=0, stdout="", stderr="")

    p = subprocess.run(
        argv_list,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=dict(os.environ, **(env or {})),
    )

    if p.stdout:
        logger.debug("STDOUT %s", p.stdout.strip())
    if p.stderr:
        logger.debug("STDERR %s", p.stderr.strip())

    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {_fmt_argv(argv_list)}\n{p.stderr}")

    return CmdResult(argv=argv_list, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
