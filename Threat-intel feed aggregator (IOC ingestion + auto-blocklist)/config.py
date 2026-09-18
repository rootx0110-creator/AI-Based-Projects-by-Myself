import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DB_PATH = os.path.join(BASE_DIR, "data", "threatintel.db")

DATA_DIR = os.path.join(BASE_DIR, "data")

REPORT_DIR = os.path.join(BASE_DIR, "reports")

DEFAULT_USER_AGENT = "ThreatIntel-Aggregator/1.0 (+SOC tooling)"

FETCH_TIMEOUT = 60

MAX_FEED_BYTES = 10 * 1024 * 1024  # 10 MB cap per feed

# How far back auto-purging will keep IOCs before expiration check
IOC_EXPIRY_DAYS = 90

# Multiplier applied to a feed's reputation score between 0..1
FEED_REPUTATION_WEIGHT = 0.6

# Retention window for ingestion log
LOG_RETENTION_DAYS = 30

SEED_FEEDS = [
    {
        "name": "Abuse.ch Feodo Tracker",
        "url": "https://feodotracker.abuse.ch/downloads/ipblocklist.txt",
        "format": "TXT",
        "ioc_types": ["IP"],
        "reputation": 0.95,
    },
    {
        "name": "Abuse.ch URLhaus",
        "url": "https://urlhaus.abuse.ch/downloads/text/",
        "format": "TXT",
        "ioc_types": ["URL"],
        "reputation": 0.95,
    },
    {
        "name": "Blocklist.de",
        "url": "https://lists.blocklist.de/lists/all.txt",
        "format": "TXT",
        "ioc_types": ["IP"],
        "reputation": 0.8,
    },
    {
        "name": "Emerging Threats BotCC",
        "url": "https://rules.emergingthreats.net/blockrules/compromised-ips.txt",
        "format": "TXT",
        "ioc_types": ["IP"],
        "reputation": 0.9,
    },
    {
        "name": "Tor Exit Nodes",
        "url": "https://check.torproject.org/exit-addresses",
        "format": "TXT",
        "ioc_types": ["IP"],
        "reputation": 0.7,
    },
    {
        "name": "Greensnow",
        "url": "https://blocklist.greensnow.co/greensnow.txt",
        "format": "TXT",
        "ioc_types": ["IP"],
        "reputation": 0.85,
    },
    {
        "name": "Binary Defense Artillery",
        "url": "https://www.binarydefense.com/banlist.txt",
        "format": "TXT",
        "ioc_types": ["IP"],
        "reputation": 0.85,
    },
    {
        "name": "CI Army BadGuys",
        "url": "https://www.ciarmy.com/list/ci-badguys.txt",
        "format": "TXT",
        "ioc_types": ["IP"],
        "reputation": 0.8,
    },
    {
        "name": "OpenPhish",
        "url": "https://openphish.com/feed.txt",
        "format": "TXT",
        "ioc_types": ["URL"],
        "reputation": 0.75,
    },
    {
        "name": "Darklist.de",
        "url": "https://www.darklist.de/raw.php",
        "format": "TXT",
        "ioc_types": ["IP"],
        "reputation": 0.7,
    },
]