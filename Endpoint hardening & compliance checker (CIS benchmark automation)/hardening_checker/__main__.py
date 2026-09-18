"""Entry point: `python -m hardening_checker` (GUI) or `--cli` for headless mode."""

from __future__ import annotations

import sys

from . import __version__


def main() -> int:
    argv = sys.argv[1:]

    if argv and argv[0] in {"--cli", "-c"}:
        # Delegate the rest of argv to the CLI parser.
        from .cli import main as cli_main

        rest = argv[1:]
        # Allow bare `--cli scan ...` and `--cli --version` forms.
        if not rest or rest[0] not in {"scan", "rules", "--help", "-h"}:
            rest = ["--help"]
        return cli_main(rest)

    if argv and argv[0] in {"--version", "-V"}:
        print(f"hardening-checker {__version__}")
        return 0

    if argv and argv[0] in {"--help", "-h"}:
        print(__doc__)
        print("\nUsage:")
        print("  python -m hardening_checker            launch the GUI")
        print("  python -m hardening_checker --cli scan launch the CLI scanner")
        return 0

    try:
        from .gui.app import run_gui
    except ImportError as exc:
        print(
            "PySide6 is required for the GUI. Install it with:\n"
            "  pip install PySide6\n"
            f"(import error: {exc})",
            file=sys.stderr,
        )
        return 3

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
