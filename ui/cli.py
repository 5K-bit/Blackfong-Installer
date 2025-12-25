from __future__ import annotations

from blackfong_installer.main import main as core_main


def main(argv: list[str] | None = None) -> int:
    # Strict invariant: CLI and GUI must never disagree.
    # This wrapper intentionally delegates to the core installer CLI entrypoint.
    return core_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
