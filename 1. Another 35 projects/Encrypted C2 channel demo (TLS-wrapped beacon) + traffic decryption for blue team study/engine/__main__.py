"""
__main__.py -- headless end-to-end verification of the lab engine.

Runs the full loop without any GUI: start listener, run one beacon check-in
with a queued task, decrypt the capture, write an HTML report.

Educational software. Not for use on systems you do not own.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import beacon as beacon_mod            # noqa: E402
from engine import decrypt as decrypt_mod          # noqa: E402
from engine.listener import LabListener            # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def log(kind, msg):
    print("  [%-7s] %s" % (kind.upper(), msg))


def main():
    print("== GLM Beacon Lab -- engine self-test ==\n")

    listener = LabListener(host="127.0.0.1", port=8443,
                           campaign="purple-night", log=log)
    listener.start()
    time.sleep(0.3)

    b = beacon_mod.Beacon(host="127.0.0.1", port=8443,
                          beacon_id="test01", sleep_time=1.0, jitter=0.0,
                          campaign="purple-night", log=log)
    b.start()

    listener.queue_task("*", "whoami")
    time.sleep(3.0)

    b.stop()
    listener.stop()

    events = listener.snapshot_events()
    print("\n  captured %d events, %d pcap records" % (len(events), len(listener.pcap)))
    assert any(e.kind == "c2" and "REGISTER" in e.summary for e in events), "no REGISTER seen"
    results = [e for e in events if "RESULT" in e.summary]
    print("  RESULT events: %d" % len(results))

    # decryption exercise on the live capture
    frames = [data for ts, tag, direction, data in listener.pcap if tag == "packet"
              and data[:4] == b"GLM1"]
    print("  framed packets available for decryption: %d" % len(frames))
    enc, mac = decrypt_mod.derive_keys("purple-night")
    ok, fail = 0, 0
    for f in frames:
        try:
            r = decrypt_mod.try_decrypt_frame(f, enc, mac, listener.last_nonce)
            ok += 1
            print("    [%s] %s" % (r["msg_name"], r["plaintext"].decode("utf-8")[:70]))
        except ValueError as exc:
            fail += 1
    print("  decryption: %d ok, %d failed" % (ok, fail))
    assert ok >= 3, "expected at least 3 frames to decrypt"

    # report generator
    from engine.report import build_report, write_report
    html = build_report("purple-night", events, frames, listener.last_nonce, "purple-night")
    out = write_report(html, os.path.join(ROOT, "GLM_Beacon_Lab_Report.html"))
    print("  report written: %s" % out)
    print("\nPASS")


if __name__ == "__main__":
    main()
