"""Entry point for the Compliance Automation Suite.

Usage:
    python run.py            # start server and open browser
    python run.py --no-browser
    python run.py --port 9000
"""

import argparse

from app.server import run


def main():
    parser = argparse.ArgumentParser(description="Compliance Automation Suite")
    parser.add_argument("--port", type=int, default=9999)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    run(host=args.host, port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
