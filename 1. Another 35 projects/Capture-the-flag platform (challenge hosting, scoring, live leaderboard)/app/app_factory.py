"""Flask app factory for the CTF platform."""
import os

from flask import Flask, session

from . import config, services
from .db import JSONDatabase
from .routes import bp
from .websocket import sock, hub


def create_app() -> Flask:
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), "templates"),
                static_folder=os.path.join(os.path.dirname(__file__), "static"))

    # In a PyInstaller bundle the package dir is not on disk; resources are
    # unpacked to sys._MEIPASS. Point Flask there when frozen.
    if getattr(__import__("sys"), "frozen", False):
        meipass = __import__("sys")._MEIPASS
        app.template_folder = os.path.join(meipass, "app", "templates")
        app.static_folder = os.path.join(meipass, "app", "static")
    app.secret_key = config.SECRET_KEY
    app.config["JSON_SORT_KEYS"] = False
    app.permanent_session_lifetime = __import__("datetime").timedelta(days=7)

    db = JSONDatabase(config.DB_PATH)
    app.extensions["ctf_db"] = db

    sock.init_app(app)
    app.register_blueprint(bp)

    # Seed the demo admin once.
    if not db.get_user_by_name(config.ADMIN_USERNAME):
        db.create_user(config.ADMIN_USERNAME, config.ADMIN_PASSWORD, is_admin=True)

    @app.context_processor
    def inject_globals():
        user = None
        if session.get("uid"):
            user = db.get_user(session["uid"])
        return dict(current_user=user, ctf_name=db.ctf_config().get("ctf_name", "CTF"))

    @app.route("/_demo_seed", methods=["POST"])  # dev helper
    def demo_seed():
        from .features.demo import ensure_demo_data
        ensure_demo_data(db)
        return {"ok": True}

    return app
