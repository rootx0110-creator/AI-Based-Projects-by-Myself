"""Phishing Email Analyzer entry point."""

import sys

if __name__ == "__main__":
    import utils.state as state_mod
    state_mod.ensure_dirs()

    from utils.state import StateManager
    from app import App

    store = StateManager()
    app = App(store)
    app.mainloop()