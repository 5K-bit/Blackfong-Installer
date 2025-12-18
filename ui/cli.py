from __future__ import annotations

import argparse

from blackfong_installer.main import run


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="blackfong-installer-cli")
    p.add_argument("--state", required=False, help="State path (defaults to /var/lib/blackfong-installer/state.json)")
    p.add_argument("--log", required=False, help="Log path (defaults to /var/log/blackfong-installer.log)")
    p.add_argument("--start-at", default=None)
    p.add_argument("--stop-after", default=None)
    p.add_argument("--force", action="store_true")

    args = p.parse_args(argv)

    kwargs = {}
    if args.state:
        kwargs["state_path"] = args.state
    if args.log:
        kwargs["log_path"] = args.log

    run(start_at=args.start_at, stop_after=args.stop_after, force=args.force, **kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
