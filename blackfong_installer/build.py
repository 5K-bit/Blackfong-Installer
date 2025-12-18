from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .build_config import load_build_config
from .build_state import ensure_build_defaults, load_build_state, save_build_state
from .build_steps import ALL_STEPS, BuildCtx
from .logging_utils import configure_logging

logger = logging.getLogger(__name__)


DEFAULT_BUILD_CONFIG = "build_config.yaml"
DEFAULT_BUILD_STATE = "build/build_state.json"
DEFAULT_BUILD_LOG = "logs/blackfong-build.log"


def run_build(
    *,
    config_path: str,
    state_path: str,
    log_path: str,
    target: str | None,
    dry_run: bool,
    force: bool,
) -> None:
    configure_logging(log_path=log_path)

    cfg = load_build_config(config_path)
    state = ensure_build_defaults(load_build_state(state_path))

    targets = [target] if target else cfg.targets
    if not targets:
        raise RuntimeError("No build targets specified")

    for t in targets:
        ctx = BuildCtx(cfg=cfg, target=t, state_path=state_path, dry_run=dry_run)
        logger.info("=== Build target: %s ===", t)
        for fn in ALL_STEPS:
            fn(ctx=ctx, state=state, force=force)
            save_build_state(state_path, state)


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="blackfong-build")
    p.add_argument("--config", default=DEFAULT_BUILD_CONFIG)
    p.add_argument("--state", default=DEFAULT_BUILD_STATE)
    p.add_argument("--log", default=DEFAULT_BUILD_LOG)
    p.add_argument("--target", default=None, help="Build a single target (amd64|arm64|armhf)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")

    args = p.parse_args(argv)

    run_build(
        config_path=args.config,
        state_path=args.state,
        log_path=args.log,
        target=args.target,
        dry_run=bool(args.dry_run),
        force=bool(args.force),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
