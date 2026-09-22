"""Entry point for running the CTF platform.

Usage:
    python run.py            # starts on http://127.0.0.1:5000
    python run.py --seed     # seeds demo users/solves on first run
"""
import argparse

from app import config
from app.app_factory import create_app

app = create_app()


def seed_demo() -> None:
    """Seed through the app's own DB instance so both share one source of truth."""
    from app.features.demo import ensure_demo_data
    ensure_demo_data(app.extensions["ctf_db"])
    print("[*] demo data seeded")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NEON GRID CTF platform")
    parser.add_argument("--seed", action="store_true", help="seed demo data")
    parser.add_argument("--port", type=int, default=None, help="override port")
    args = parser.parse_args()

    if args.seed:
        seed_demo()

    import socket

    host, port = config.HOST, args.port or config.PORT
    # Port fallback so double-clicking the EXE twice never crashes.
    for candidate in range(port, port + 10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((host if host != "0.0.0.0" else "127.0.0.1", candidate)) != 0:
                port = candidate
                break

    print(r"""
  _   _ _____ _   _ _____  _____  _   _
 | \ | | ____| \ | / _ \ \/ / _ \| \ | |
 |  \| |  _| |  \| | | | \  / | | |  \| |
 | |\  | |___| |\  | |_| /  \ |_| | |\  |
 |_| \_|_____|_| \_|\____/_/\_\___/|_| \_|   CTF PLATFORM
""")
    print(f"[*] Open http://{host}:{port}")
    print("[*] Admin login: admin / admin123 (change it!)")
    app.run(host=host, port=port, debug=config.DEBUG)
