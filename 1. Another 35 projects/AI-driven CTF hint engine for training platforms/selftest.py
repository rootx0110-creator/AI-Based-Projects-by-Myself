import app

c = app.app.test_client()

r = c.get("/")
print("dashboard:", r.status_code, "has_seed:", "Login Bypass 101" in r.get_data(as_text=True))

r = c.get("/challenges")
print("challenges page:", r.status_code)

for i in range(6):
    rr = c.post("/api/challenge/1/hint")
    d = rr.get_json()
    print("  hint lvl={} src={} text={!r}".format(d["level"], d["source"], d["content"][:60]))

r = c.get("/challenge/1")
print("challenge page:", r.status_code)

r = c.post("/api/challenge/1/verify", json={"answer": "ctf{sql_1nj3ct10n}"})
print("verify correct:", r.get_json())

r = c.post("/api/challenge/2/verify", json={"answer": "wrong"})
print("verify wrong:", r.get_json())

r = c.post("/api/challenge/3/solve")
print("manual solve:", r.get_json())

r = c.get("/download/report")
print("report download:", r.status_code, "bytes", len(r.data), "disp:", r.headers.get("Content-Disposition"))

r = c.post("/api/settings", json={"provider": "openai", "base_url": "https://api.openai.com/v1", "api_key": "sk-x", "model": "gpt-4o-mini", "enabled": False})
print("settings save:", r.status_code)
d = c.get("/api/settings").get_json()
print("settings persisted provider=", d["provider"], "enabled=", d["enabled"])

r = c.post("/api/challenges", json={"title": "Test Challenge", "category": "Misc", "difficulty": "Easy", "description": "do the thing", "flag": "ctf{t}", "hints": "nudge\npath"})
print("add challenge:", r.get_json())

r = c.get("/report")
print("report preview:", r.status_code)

import html as H
from report import render_report
print("report has hint timeline:", "Hint Activity Timeline" in render_report(
    app.store.stats(), *app.store.report_data(), "now").replace("&", "&amp;"))