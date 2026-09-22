# INTENTIONALLY INSECURE demo fixture for SecuRevealer — do not use in production.
import os, pickle, yaml, hashlib, subprocess
from flask import Flask, request, redirect
import requests

app = Flask(__name__)
DEBUG = True                                        # debug mode on
API_KEY = "sk_live_9f8e7d6c5b4a3210abcd"            # hardcoded secret

@app.route("/search")
def search():
    name = request.args.get("q")
    cur.execute(f"SELECT * FROM products WHERE name = '{name}'")  # SQL injection
    return str(cur.fetchall())

@app.route("/ping")
def ping():
    host = request.args.get("host")
    os.system("ping -c 1 " + host)                  # command injection
    subprocess.run("nslookup %s" % host, shell=True)
    return "done"

@app.route("/session")
def session():
    data = request.cookies.get("sess")
    obj = pickle.loads(data)                        # unsafe deserialization
    cfg = yaml.load(open("cfg.yml"))                # yaml.load without SafeLoader
    return str(obj)

@app.route("/calc")
def calc():
    return str(eval(request.args.get("expr")))      # code execution

@app.route("/proxy")
def proxy():
    return requests.get(request.args["url"], verify=False).text  # SSRF + TLS off

@app.route("/import")
def import_data():
    return open(os.path.join("/data", request.args.get("f"))).read()  # path traversal

@app.route("/pw")
def pw():
    return hashlib.md5(request.args["pw"].encode()).hexdigest()  # weak hash

@app.route("/next")
def go_next():
    return redirect(request.args["next"])           # open redirect

if __name__ == "__main__":
    app.run(debug=True)