import multiprocessing
import os
import sys
import time


def main():
    from app.agent import HIDSAgent

    # Headless agent mode: `HIDS_Agent.exe --headless`
    if "--headless" in sys.argv:
        agent = HIDSAgent()
        agent.start()
        print("HIDS Agent running headless. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            agent.stop()
        return 0

    from app.ui.app import run

    agent = HIDSAgent()
    agent.start()
    run(agent)
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass