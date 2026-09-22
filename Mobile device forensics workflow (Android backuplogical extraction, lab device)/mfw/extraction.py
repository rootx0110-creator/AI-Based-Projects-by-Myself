"""Core extraction pipeline (device-independent; runs inside a QThread or tests).

Method dispatch:
  adb_backup  -> adb backup -> unpack .ab -> parse contacts2.db / mmssms.db
  packages    -> pm list packages -> parse -> Apps artifacts
  screenshot  -> screencap -> PNG evidence
  demo        -> deterministic synthetic dataset (no device required)
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable

from . import adb, demo, parsers

LogFn = Callable[[str], None]
ProgressFn = Callable[[int], None]

METHODS = {
    "adb_backup": "ADB Backup (logical acquisition)",
    "packages": "Package inventory",
    "screenshot": "Screenshot capture",
    "demo": "Demo dataset (offline)",
}


def run_extraction(
    case_number: str,
    case_dir: str,
    method: str,
    adb_path: str | None = None,
    serial: str | None = None,
    log: LogFn | None = None,
    progress: ProgressFn | None = None,
) -> dict[str, Any]:
    """Run one extraction end-to-end. Returns a record dict for the case index."""
    def L(msg: str) -> None:
        if log:
            log(msg)

    def P(v: int) -> None:
        if progress:
            progress(v)

    record: dict[str, Any] = {
        "method": method,
        "method_label": METHODS.get(method, method),
        "started": None,
        "status": "unknown",
        "detail": "",
        "device": serial or "",
        "evidence_files": [],
        "artifact_counts": {},
    }

    ev_dir = os.path.join(case_dir, "evidence")
    ex_dir = os.path.join(case_dir, "extracted")
    os.makedirs(ev_dir, exist_ok=True)
    os.makedirs(ex_dir, exist_ok=True)

    P(5)
    if method == "demo":
        record["started"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        L("[demo] generating deterministic synthetic dataset ...")
        info = demo.demo_device_info(case_number)
        arts = demo.demo_artifacts(case_number)
        P(50)
        ev_path = os.path.join(ev_dir, f"demo_dataset_{case_number}.json")
        with open(ev_path, "w", encoding="utf-8") as fh:
            json.dump({"device": info, "artifacts": arts}, fh, indent=1)
        record["evidence_files"].append(os.path.basename(ev_path))
        L(f"[demo] dataset saved: {os.path.basename(ev_path)}")
        P(75)
    else:
        if not adb_path:
            record["status"] = "failed"
            record["detail"] = "adb not found - install Android platform-tools or use the Demo dataset method."
            L("[error] " + record["detail"])
            return record
        if not serial:
            record["status"] = "failed"
            record["detail"] = "no device selected"
            L("[error] no device selected")
            return record

        record["started"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        L(f"[adb] reading device info for {serial} ...")
        info = adb.device_info(adb_path, serial)
        record["device_info"] = info
        L(f"[adb] device: {info.get('manufacturer', '?')} {info.get('model', '?')} "
          f"Android {info.get('android_version', '?')} (SDK {info.get('sdk', '?')})")
        P(20)

        if method == "adb_backup":
            ab_path = os.path.join(ev_dir, f"backup_{case_number}.ab")
            L("[adb backup] starting logical acquisition - CONFIRM 'Back up my data' on the device ...")
            ok, out = adb.run_backup(adb_path, serial, ab_path, timeout=240)
            L("[adb backup] " + out.splitlines()[0] if out else "[adb backup] done")
            if not ok:
                record["status"] = "failed"
                record["detail"] = "backup missing/empty (cancelled on device, timed out, or restricted Android build)"
                L("[error] " + record["detail"])
                return record
            size_mb = os.path.getsize(ab_path) / (1024 * 1024)
            L(f"[adb] backup written: {os.path.basename(ab_path)} ({size_mb:.2f} MB)")
            record["evidence_files"].append(os.path.basename(ab_path))
            P(45)
            L("[unpack] inflating .ab (zlib) and extracting tar ...")
            ok, out = parsers.unpack_ab(ab_path, ex_dir)
            L("[unpack] " + out)
            if not ok:
                record["status"] = "failed"
                record["detail"] = out
                return record
            P(65)
            L("[parse] contacts2.db / mmssms.db ...")
            arts = parsers.parse_artifacts(ex_dir)
            P(85)

        elif method == "packages":
            ok3, out3 = adb.list_packages(adb_path, serial, third_party=True)
            oks, outs = adb.list_packages(adb_path, serial, third_party=False)
            text = (out3 if ok3 else "") + "\n" + (outs if oks else "")
            if not text.strip():
                record["status"] = "failed"
                record["detail"] = "pm list packages returned nothing"
                L("[error] " + record["detail"])
                return record
            pkg_path = os.path.join(ev_dir, f"packages_{case_number}.txt")
            with open(pkg_path, "w", encoding="utf-8") as fh:
                fh.write(text)
            record["evidence_files"].append(os.path.basename(pkg_path))
            L(f"[adb] package list saved ({text.count(chr(10))} lines)")
            P(60)
            arts = parsers.parse_artifacts(ex_dir, package_text=text)
            info_pkg = {"note": "no backup performed"}
            P(85)

        elif method == "screenshot":
            png_path = os.path.join(ev_dir, f"screenshot_{case_number}_{int(__import__('time').time())}.png")
            ok, out = adb.screenshot(adb_path, serial, png_path)
            L("[screencap] " + out)
            if not ok:
                record["status"] = "failed"
                record["detail"] = out
                return record
            record["evidence_files"].append(os.path.basename(png_path))
            L(f"[screencap] saved {os.path.basename(png_path)}")
            arts = parsers.parse_artifacts(ex_dir)
            info = info  # already read
            P(85)
        else:
            record["status"] = "failed"
            record["detail"] = f"unknown method '{method}'"
            L("[error] " + record["detail"])
            return record

    # ------------------------------------------------------- post-common --
    P(90)
    counts = {k: len(v) for k, v in arts.items()}
    record["artifact_counts"] = counts
    parsers.save_artifacts(case_dir, arts)
    L(f"[artifacts] " + ", ".join(f"{k}={v}" for k, v in counts.items()))

    dev_path = os.path.join(ex_dir, "device_info.json")
    with open(dev_path, "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=1)

    record["status"] = "completed"
    P(100)
    L("[done] extraction completed")
    return record
