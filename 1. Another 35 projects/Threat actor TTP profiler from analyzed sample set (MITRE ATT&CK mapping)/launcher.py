"""Root launcher used by PyInstaller builds (and optionally by `python launcher.py`).

Imports `app.main` as a package so relative imports resolve correctly when frozen,
where the entry module would otherwise be treated as a top-level script.
"""

from __future__ import annotations

import os
import sys


def _mark(msg: str) -> None:
    try:
        logdir = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.abspath("."), "ThreatActorTTPProfiler")
        os.makedirs(logdir, exist_ok=True)
        with open(os.path.join(logdir, "startup.log"), "a", encoding="utf-8") as fh:
            fh.write("[%s] %s\n" % (os.path.basename(sys.argv[0]), msg))
    except Exception:  # noqa: BLE001
        pass


_mark("launcher top; py=%s%s" % (sys.version_info.major, sys.version_info.minor))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.main import _fail, main  # noqa: E402
    _mark("launcher imports OK")
except Exception as exc:  # noqa: BLE001
    _mark("launcher import FAILED: %r" % exc)
    raise


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        sys.exit(_fail(exc))