from __future__ import annotations

import argparse
import logging
from typing import Any, Dict, Optional

from .logging_utils import DEFAULT_LOG_PATH, configure_logging
from .pipeline import run_pipeline
from .state_store import ensure_defaults, load_state, save_state
from .steps import (
    ConfigureServicesStep,
    DetectHardwareStep,
    FinalizeRebootStep,
    InstallDesktopStep,
    InstallFeaturesStep,
    InstallKernelStep,
    InstallRootFSStep,
    PartitionFilesystemStep,
    PostInstallChecksStep,
)

logger = logging.getLogger(__name__)


DEFAULT_STATE_PATH = "/var/lib/blackfong-installer/state.json"


def build_steps():
    return [
        DetectHardwareStep(),
        PartitionFilesystemStep(),
        InstallKernelStep(),
        InstallRootFSStep(),
        ConfigureServicesStep(),
        InstallDesktopStep(),
        InstallFeaturesStep(),
        PostInstallChecksStep(),
        FinalizeRebootStep(),
    ]


def run(
    *,
    state_path: str = DEFAULT_STATE_PATH,
    log_path: str = DEFAULT_LOG_PATH,
    start_at: Optional[str] = None,
    stop_after: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Run the installer pipeline, persisting state for resume."""

    actual_log_path = configure_logging(log_path=log_path)

    state = ensure_defaults(load_state(state_path))
    state.setdefault("execution", {}).setdefault("paths", {})["log_path_requested"] = log_path
    state.setdefault("execution", {}).setdefault("paths", {})["log_path_actual"] = actual_log_path

    steps = build_steps()

    try:
        result = run_pipeline(
            state=state,
            steps=steps,
            start_at=start_at,
            stop_after=stop_after,
            force=force,
        )
        state = result.state
        state.setdefault("execution", {}).setdefault("summary", {})["ran_steps"] = result.ran_steps
        state.setdefault("execution", {}).setdefault("summary", {})["skipped_steps"] = result.skipped_steps
        return state
    except Exception as e:
        logger.exception("Installer failed")
        state.setdefault("execution", {}).setdefault("errors", []).append(
            {
                "step": (state.get("execution") or {}).get("current_step"),
                "error": str(e),
            }
        )
        raise
    finally:
        save_state(state_path, state)


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="blackfong-installer")
    p.add_argument("--state", default=DEFAULT_STATE_PATH, help="Path to installer state (json|yaml)")
    p.add_argument("--log", default=DEFAULT_LOG_PATH, help="Path to installer log")
    p.add_argument("--start-at", default=None, help="Start at step_id (e.g. 30_install_kernel)")
    p.add_argument("--stop-after", default=None, help="Stop after step_id")
    p.add_argument("--force", action="store_true", help="Re-run steps even if marked completed")

    args = p.parse_args(argv)

    run(
        state_path=args.state,
        log_path=args.log,
        start_at=args.start_at,
        stop_after=args.stop_after,
        force=args.force,
    )
    return 0
