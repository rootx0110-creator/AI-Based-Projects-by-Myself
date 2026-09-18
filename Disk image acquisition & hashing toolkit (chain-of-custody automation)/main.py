import sys
import os


def run():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))) if False else None
    from app.ui.app import launch

    launch()


if __name__ == "__main__":
    run()