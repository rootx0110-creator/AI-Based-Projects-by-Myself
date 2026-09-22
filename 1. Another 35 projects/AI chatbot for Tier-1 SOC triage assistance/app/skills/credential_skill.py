"""Skill: Credential & Identity Threat Analysis."""
PRIORITY = 30
KEYWORDS = ["credential", "password", "brute force", "password spray",
            "account", "login", "logon", "mfa", "mfa fatigue", "impossible travel",
            "authentication", "adfs", "azure ad", "entra", "okta", "sso",
            "privileged account", "service account", "kerberoast", "ntlm",
            "pass-the-hash", "pass the hash", "lsaass", "lsass", "mimikatz",
            "token", "disabled account", "account lockout", "anomalous login"]

FAIL_SOFTWARE = {
    "mimikatz": "Credential dumping tool — LSASS access, T1003:001.",
    "secretsdump": "Remote credential dumping via SAM/NTDS — T1003:003.",
    "procexp": "Process Explorer LSASS handle — review for T1003.",
    "procdump": "Procdump LSASS dump — possible T1003 (also legit admin use).",
    "nanodump": "LSASS dumper — T1003.",
    "rubeus": "Kerberos abuse toolkit — T1558.",
    "kekeo": "Kerberos abuse toolkit — T1558.",
    "wce": "Windows Credential Editor — T1003.",
    "gsecdump": "Credential dumper — T1003.",
    "pypykatz": "Python Mimikatz — T1003.",
}


def analyze(text, iocs, context):
    low = (text or "").lower()
    tools = [d for kw, d in FAIL_SOFTWARE.items() if kw in low]

    impossible_travel = "impossible travel" in low
    mfa_fatigue = "mfa fatigue" in low or ("mfa" in low and "push" in low)
    brute = "brute force" in low or "password spray" in low or "credential stuffing" in low
    pass_the_hash = "pass-the-hash" in low or "pass the hash" in low or "pth" in low.split()
    kerberoast = "kerberoast" in low
    new_account = "account created" in low or "new user created" in low
    disabled_av = "disabled" in low and ("defender" in low or "av " in low or "antivirus" in low)

    risk = 0
    risk += 30 if tools else 0
    risk += 25 if impossible_travel else 0
    risk += 25 if mfa_fatigue else 0
    risk += 20 if brute else 0
    risk += 30 if pass_the_hash else 0
    risk += 20 if kerberoast else 0
    risk += 10 if new_account else 0
    risk += 15 if disabled_av else 0

    return {
        "credential": {
            "dumping_tools": tools,
            "impossible_travel": impossible_travel,
            "mfa_fatigue": mfa_fatigue,
            "brute_force": brute,
            "pass_the_hash": pass_the_hash,
            "kerberoast": kerberoast,
            "new_account_created": new_account,
            "risk_score": min(risk, 100),
        }
    }


def respond(text, iocs, analysis, context):
    c = analysis.get("credential", {})
    if not c:
        return ""
    lines = ["**Credential & Identity Threats**"]
    for tool in c.get("dumping_tools", []):
        lines.append(f"- 🔑 {tool}")
    if c.get("impossible_travel"):
        lines.append("- 🌍 Impossible travel detected — validate recent geo-locations with the user and check concurrent sessions.")
    if c.get("mfa_fatigue"):
        lines.append("- 📲 MFA fatigue pattern — consider number matching / FIDO2 and re-issue sessions.")
    if c.get("brute_force"):
        lines.append("- 🧱 Brute force / password spraying — enforce lockout, check source IPs across the tenant.")
    if c.get("pass_the_hash"):
        lines.append("- 🪪 Pass-the-hash behavior — rotate credentials and review 4624 logons with the same logon type.")
    if c.get("kerberoast"):
        lines.append("- 🎫 Kerberoasting — check SPNs with weak service passwords and enable gMSA.")
    if c.get("new_account_created"):
        lines.append("- ➕ Newly created account — verify owner; unexplained accounts are persistence (T1136).")
    lines.append(f"- Identity risk score: **{c.get('risk_score', 0)}/100**")
    return "\n".join(lines)


def report_section(analysis):
    c = analysis.get("credential")
    if not c:
        return None

    def yn(flag):
        return "Yes" if flag else "No"

    rows = "".join([
        f"<tr><td class='k'>Credential dumping tools</td><td>{', '.join(c.get('dumping_tools', [])) or 'None detected'}</td></tr>",
        f"<tr><td class='k'>Impossible travel</td><td>{yn(c.get('impossible_travel'))}</td></tr>",
        f"<tr><td class='k'>MFA fatigue</td><td>{yn(c.get('mfa_fatigue'))}</td></tr>",
        f"<tr><td class='k'>Brute force / spray</td><td>{yn(c.get('brute_force'))}</td></tr>",
        f"<tr><td class='k'>Pass-the-hash</td><td>{yn(c.get('pass_the_hash'))}</td></tr>",
        f"<tr><td class='k'>Kerberoasting</td><td>{yn(c.get('kerberoast'))}</td></tr>",
        f"<tr><td class='k'>New account created</td><td>{yn(c.get('new_account_created'))}</td></tr>",
        f"<tr><td class='k'>Identity risk</td><td><b>{c.get('risk_score', 0)}/100</b></td></tr>",
    ])
    return {"title": "Credential & Identity Analysis", "html": f"<table>{rows}</table>"}
