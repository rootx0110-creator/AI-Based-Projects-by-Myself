import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.analyzer import run_scan

tests = [
    ("union", "http://shop.local/products.php?id=1 UNION ALL SELECT NULL,user(),3-- -"),
    ("auth-bypass", "http://shop.local/login.php?user=admin' OR '1'='1&pass=x"),
    ("boolean", "http://portal.local/account?id=5 AND 1=1"),
    ("time-blind", "http://api.local/v1/search?q=1' AND SLEEP(3)-- -"),
    ("dbms-fp", "http://old.local/report.aspx?code=1;WAITFOR DELAY '00:00:03'-- &db=@@version"),
    ("clean", "http://shop.local/product/1042?utm_source=newsletter&lang=en"),
]

print("OFFLINE URL samples")
for tag, t in tests:
    r = run_scan(t, mode="url")
    tr = r["targets"][0]
    worst = max(tr["findings"], key=lambda f: f["score"]) if tr["findings"] else None
    worst_s = ("worst=%s (%s)" % (worst["name"], worst["risk"])) if worst else "no params"
    print("  %-12s -> risk=%-8s score=%3d  %s" % (tag, tr["risk"], tr["score"], worst_s))
    for f in tr["findings"]:
        print("       %s: %d (%s)  %s" % (f["name"], f["score"], f["risk"],
              "; ".join(t2["key"] for t2 in f["techniques"][:3])))