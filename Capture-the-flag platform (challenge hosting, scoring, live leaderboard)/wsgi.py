"""Production serving entry point (used by the EXE build and general deploys).

Usage:  python wsgi.py   (serves with waitress on 127.0.0.1:5000)
"""
from app import config
from app.app_factory import create_app

app = create_app()

if __name__ == "__main__":
    from waitress import serve
    print(f"[*] NEON//GRID CTF on http://{config.HOST}:{config.PORT}")
    serve(app, host=config.HOST, port=config.PORT, threads=8)
