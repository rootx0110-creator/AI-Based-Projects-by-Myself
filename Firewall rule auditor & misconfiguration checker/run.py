"""Dev entrypoint: run the FRAMC web app locally."""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FRAMC web app")
    parser.add_argument("--host", default=os.environ.get("FRAMC_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int,
                        default=int(os.environ.get("FRAMC_PORT", 8765)))
    parser.add_argument("--no-browser", action="store_true",
                        help="do not auto-open the browser")
    args = parser.parse_args()

    from backend.app import app

    if not args.no_browser:
        webbrowser.open(f"http://{args.host}:{args.port}")

    try:
        from waitress import serve
        print(f"FRAMC listening on http://{args.host}:{args.port} (waitress)")
        serve(app, host=args.host, port=args.port)
    except ImportError:
        print(f"FRAMC listening on http://{args.host}:{args.port} (flask dev)")
        app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()