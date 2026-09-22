"""Deterministic synthetic dataset for offline demo of the full workflow.

Same case-number seed -> same dataset, so demos and screenshots are stable.
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta

FIRST = ["Ava","Liam","Noah","Maya","Ethan","Zoe","Lucas","Rania","Omar","Sofia",
         "Priya","Chen","Diego","Fatima","Jonas","Karim","Elena","Tariq","Nina","Hugo"]
LAST = ["Bennett","Okafor","Silva","Nguyen","Kowalski","Haddad","Ivanov","Mensah",
        "Torres","Yamada","Petrov","Almeida","Fischer","Diallo","Rossi","Lindqvist"]
SMS_BODIES = [
    "Running 10 min late, sorry!",
    "Did you get the files?",
    "Meeting moved to 15:00",
    "Call me when you land",
    "Can you send the report tonight?",
    "Happy birthday!! 🎉",
    "The package was delivered",
    "Please review the contract",
    "On my way",
    "Don't forget the charger",
    "Are we still on for Saturday?",
    "Sent you the photos",
    "Network is down at the office",
    "Thanks, got it",
    "Check your email please",
]
APPS = [
    "com.whatsapp","org.telegram.messenger","com.instagram.android",
    "com.spotify.music","com.netflix.mediaclient","com.android.chrome",
    "com.google.android.gm","com.sec.android.app.launcher",
    "com.signal","com.linkedin.android","com.dropbox.android",
    "com.amazon.mShop.android.shopping","com.ubercab","com.airbnb.android",
]
MANUFACTURERS = [("Samsung", "SM-S918B"), ("Google", "Pixel 8"), ("Xiaomi", "23021RAAEG")]


def _seed(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


def demo_device_info(case_number: str) -> dict[str, str]:
    rnd = random.Random(_seed(case_number + "|device"))
    man, model = rnd.choice(MANUFACTURERS)
    return {
        "manufacturer": man,
        "model": model,
        "device": model.lower().replace(" ", "_"),
        "android_version": rnd.choice(["12", "13", "14", "15"]),
        "sdk": str(rnd.choice([31, 33, 34, 35])),
        "security_patch": f"2025-{rnd.randint(1, 12):02d}-0{rnd.randint(1, 9)}",
        "serial": f"DEMO{(_seed(case_number) % 900000 + 100000)}",
        "build": f"{model[:2].upper()}1A.{_seed(case_number) % 250000}.{rnd.choice(['A','B','C'])}",
    }


def demo_artifacts(case_number: str) -> dict[str, list[dict]]:
    rnd = random.Random(_seed(case_number + "|artifacts"))

    contacts = [
        {"name": f"{rnd.choice(FIRST)} {rnd.choice(LAST)}", "phone": f"+1-555-{rnd.randint(100, 999)}-{rnd.randint(1000, 9999)}"}
        for _ in range(rnd.randint(14, 20))
    ]
    seen: set[str] = set()
    contacts = [c for c in contacts if not (c["phone"] in seen or seen.add(c["phone"]))]

    base = datetime.now() - timedelta(days=rnd.randint(20, 40))
    calls: list[dict] = []
    for _ in range(rnd.randint(40, 70)):
        ts = base + timedelta(minutes=rnd.randint(0, 60 * 24 * 30))
        calls.append({
            "number": rnd.choice(contacts)["phone"],
            "datetime": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_s": rnd.choice([0, 0, rnd.randint(5, 2400)]),
            "call_type": rnd.choices(
                ["Incoming", "Outgoing", "Missed", "Rejected"],
                weights=[4, 4, 2, 1])[0],
        })

    sms: list[dict] = []
    for _ in range(rnd.randint(45, 80)):
        ts = base + timedelta(minutes=rnd.randint(0, 60 * 24 * 30))
        sms.append({
            "address": rnd.choice(contacts)["phone"],
            "datetime": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "sms_type": rnd.choices(["Received", "Sent"], weights=[5, 5])[0],
            "body": rnd.choice(SMS_BODIES),
        })

    apps = [
        {"package": pkg, "kind": "app", "installed": "TRUE"}
        for pkg in sorted(rnd.sample(APPS, k=rnd.randint(9, len(APPS))))
    ]

    def _sort(rows: list[dict], key: str) -> list[dict]:
        return sorted(rows, key=lambda r: r.get(key, ""), reverse=True)

    return {
        "contacts": _sort(contacts, "name"),
        "calls": _sort(calls, "datetime"),
        "sms": _sort(sms, "datetime"),
        "apps": apps,
    }
