from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Sequence


@dataclass(frozen=True)
class ExecResult:
    argv: List[str]
    returncode: int
    stdout: str
    stderr: str


def parse_command(cmd: str) -> list[str]:
    return shlex.split(cmd)


def run_in_workspace(
    argv: Sequence[str],
    *,
    cwd: str,
    timeout_s: float = 30.0,
    input_text: Optional[str] = None,
) -> ExecResult:
    argv_list = list(argv)
    p = subprocess.run(
        argv_list,
        cwd=cwd,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_s,
    )
    return ExecResult(argv=argv_list, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)

