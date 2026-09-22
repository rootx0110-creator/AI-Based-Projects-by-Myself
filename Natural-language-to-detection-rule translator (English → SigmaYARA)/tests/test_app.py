import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

client = app.test_client()

# page renders
for route in ["/", "/examples", "/about"]:
    r = client.get(route)
    print(route, r.status_code, "len", len(r.data))

# translate api
r = client.post("/api/translate", json={"text": (
    "A PowerShell process downloads a file from hxxps://evil.example.com/update.exe using "
    "Invoke-WebRequest, decodes it from Base64 and runs it with iex while staying hidden. "
    "It then writes a registry Run key under HKCU\\Software for persistence."
)})
print("translate", r.status_code)
data = r.get_json()
print("  confidence:", data["confidence_pct"], "level:", data["level"],
      "entities:", data["entities_count"], "concepts:", len(data["concepts"]),
      "mitre:", len(data["mitre"]))
print("  logsource:", data["logsource"])
print("  has sigma:", bool(data["sigma"]), "| has yara:", bool(data["yara"]))

# empty input
print("empty ->", client.post("/api/translate", json={"text": ""}).status_code)
# pasted rule detection
print("rule-look ->", client.post("/api/translate", json={
    "text": "title: X\ndetection:\n  selection:\n    a: b\n  condition: selection\nlogsource: z"}).status_code)

# report download
r = client.post("/api/report", json={"text": "Mimikatz dumps LSASS credentials"})
print("report", r.status_code, "ctype", r.headers.get("Content-Type"),
      "bytes", len(r.data))
assert b"Sigma Rule" in r.data and b"YARA Rule" in r.data
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "report-test.html"),
     "wb").write(r.data)

print("ALL OK")