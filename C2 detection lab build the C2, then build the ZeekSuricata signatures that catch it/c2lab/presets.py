"""C2 beacon profile presets used by the simulator and by rule generation.

Each preset describes the network fingerprint of a well-known family of HTTP
command-and-control. The same profile drives both the simulated beacon *and*
the Zeek / Suricata signatures so the lab is internally consistent: the rules
that are generated genuinely match the traffic the lab produces.
"""

from __future__ import annotations

from dataclasses import dataclass, field

BEACONS = (  # allowable HTTP beacon verbs
    "GET",
    "POST",
)


@dataclass(frozen=True)
class C2Profile:
    name: str
    family: str
    user_agent: str
    methods: tuple
    uri_paths: tuple
    beacon_interval: int
    jitter: float
    note: str


PROFILE_PRESETS = {
    "Cobalt Strike Beacon": C2Profile(
        name="Cobalt Strike Beacon",
        family="Cobalt Strike",
        user_agent=(
            "Mozilla/5.0 (compatible; MSIE 10.6; Windows NT 6.1; Trident/5.0; "
            "InfoPath.3; SP1; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; .NET "
            "CLR 2.0.50727)"
        ),
        methods=("GET",),
        uri_paths=("/api/v3/health", "/api/v3/events", "/submit.php", "/b"),
        beacon_interval=60,
        jitter=25.0,
        note="Classic IE-ish User-Agent with periodic GET beacons, the "
        "trademark of legacy CS beacons.",
    ),
    "Sliver HTTPS": C2Profile(
        name="Sliver HTTPS",
        family="Sliver",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        methods=("GET", "POST"),
        uri_paths=("/checkin", "/profile", "/tasks"),
        beacon_interval=30,
        jitter=15.0,
        note="Modern Chrome UA with short, periodic /checkin POST beacons.",
    ),
    "Metasploit Payload": C2Profile(
        name="Metasploit Payload",
        family="Metasploit Framework",
        user_agent=(
            "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)"
        ),
        methods=("GET", "POST"),
        uri_paths=("/", "/random", "/MSF_SUBSCRIBER"),
        beacon_interval=5,
        jitter=30.0,
        note="Old MSIE UA; aggressive, irregular beacons typical of staged "
        "meterpreter sessions.",
    ),
    "SocGholish Style": C2Profile(
        name="SocGholish-ish JS Beacon",
        family="SocGholish (fake update lures)",
        user_agent=(
            "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:60.0) Gecko/20100101 "
            "Firefox/60.0"
        ),
        methods=("GET",),
        uri_paths=("/js/update.js", "/static/chk.php", "/payload"),
        beacon_interval=15,
        jitter=40.0,
        note="JavaScript beaconing with noisy intervals, mimicking fake "
        "browser-update lures.",
    ),
    "Generic HTTP Beacon": C2Profile(
        name="Generic HTTP Beacon",
        family="Custom / hand-rolled RAT",
        user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64)",
        methods=("GET", "POST"),
        uri_paths=("/robots.txt", "/cache/7f", "/thumb.php"),
        beacon_interval=45,
        jitter=10.0,
        note="Low-and-slow beacon hiding under innocuous-looking URIs.",
    ),
}

ORDER = [
    "Cobalt Strike Beacon",
    "Sliver HTTPS",
    "Metasploit Payload",
    "SocGholish Style",
    "Generic HTTP Beacon",
]


def profile_names() -> list:
    return [n for n in ORDER if n in PROFILE_PRESETS]


def get_profile(name: str) -> C2Profile:
    try:
        return PROFILE_PRESETS[name]
    except KeyError:
        return PROFILE_PRESETS["Generic HTTP Beacon"]