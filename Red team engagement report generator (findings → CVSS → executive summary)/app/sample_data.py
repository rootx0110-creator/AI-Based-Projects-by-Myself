"""Realistic sample data for demoing the report generator.

Loaded via the "Load Sample Data" button in the Findings tab. CVSS vectors
are real and score to the values shown.
"""

SAMPLE_ENGAGEMENT = {
    "engagement_title": "Acme Corporation - Q3 2026 External Red Team Engagement",
    "client_name": "Acme Corporation",
    "assessor": "Red Team Unit",
    "start_date": "2026-07-06",
    "end_date": "2026-07-17",
    "scope": ("Public web applications (app.acme.com, portal.acme.com), "
              "corporate perimeter, and the internal network 10.0.0.0/16"),
    "summary_notes": ("All testing was performed under an approved rules-of-engag"
                      "ement document. Findings below were reproduced and validated "
                      "before being reported."),
}

SAMPLE_FINDINGS = [
    {
        "title": "Unauthenticated Remote Code Execution via Java Deserialization",
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "affected_assets": "app.acme.com (Apache Tomcat 9.0.16)",
        "description": ("The /admin/export endpoint deserializes attacker-controlled "
                        "Java objects without validation, allowing a remote, "
                        "unauthenticated attacker to achieve full Remote Code "
                        "Execution as the application service account."),
        "impact": ("Complete server compromise; data confidentiality, integrity and "
                   "availability fully lost. Foothold can be leveraged to pivot "
                   "into the internal network."),
        "evidence": ("Sent ysoserial CommonsCollections6 payload; executed \"id\" "
                     "returned uid=1001(tomcat). Full exploit chain reproduced "
                     "on 2026-07-08."),
        "remediation": ("Disable deserialization on untrusted endpoints, use an "
                        "allow-listed class filter (e.g. SerialKiller), and upgrade "
                        "to a supported Tomcat version."),
        "references": "CWE-502 / CVE-2016-8735",
        "status": "Open",
    },
    {
        "title": "Broken Object-Level Authorization on Customer API",
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
        "affected_assets": "api.acme.com/v2/invoices/{id}",
        "description": ("The customer API trusts the authenticated user's role but "
                        "fails to verify ownership of the requested object, allowing "
                        "any authenticated customer to read and modify other "
                        "customers' invoices by enumerating IDs."),
        "impact": ("Mass disclosure of customer financial data and ability to "
                   "tamper with billing records, directly violating PCI-DSS obligations."),
        "evidence": ("Authenticated as testuser_001, retrieved invoice of a different "
                     "account by incrementing the ID parameter; 1,204 records "
                     "retrieved in 90 seconds."),
        "remediation": ("Enforce object-level authorization checks in the service "
                        "layer for every GET/PUT/PATCH on customer resources; add "
                        "IDOR tests to the CI pipeline."),
        "references": "CWE-639 / OWASP API1:2023",
        "status": "In Progress",
    },
    {
        "title": "Default Administrative Credentials on Network Appliance",
        "cvss_vector": "CVSS:3.1/AV:A/AC:L/PR:H/UI:R/S:C/C:H/I:H/A:H",
        "affected_assets": "Firewall HA pair (fw01, fw02)",
        "description": ("An administrative web console is exposed on the internal "
                        "interface and still uses the vendor default credentials, "
                        "permitting full administrative takeover of the gateway."),
        "impact": ("Attacker with a foothold can reconfigure or disable the perimeter "
                   "firewall, granting unrestricted access to the internal network."),
        "evidence": ("From an internal jump host, browsed to https://fw01:8443 and "
                     "logged in with the default admin password listed in the vendor "
                     "manual (2026-07-12)."),
        "remediation": ("Immediately rotate all default credentials, disable "
                        "unused management interfaces, and restrict management "
                        "access by source IP."),
        "references": "CWE-798 / CIS Control 1 (Inventory & Control)",
        "status": "Open",
    },
    {
        "title": "Local Privilege Escalation via Scheduled Task Service",
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:H/A:N",
        "affected_assets": "win-srv-db001 (Windows Server 2019)",
        "description": ("A scheduled task runs a backup script as SYSTEM from a "
                        "world-writable directory. The service account for the "
                        "backup agent can be subverted to execute arbitrary commands "
                        "with SYSTEM privileges."),
        "impact": ("Any domain user with access to the affected share can escalate "
                   "to full SYSTEM on the database server."),
        "evidence": ("Dropped a DLL into the writable script folder; the next run of "
                     "the task spawned a SYSTEM reverse shell (2026-07-14)."),
        "remediation": ("Move the script to a protected location, set ACLs on the "
                        "share, and run tasks under the least-privilege account."),
        "references": "CWE-732 / MITRE ATT&CK T1053",
        "status": "Open",
    },
    {
        "title": "Stored XSS in Support Portal Ticket Fields",
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N",
        "affected_assets": "portal.acme.com/tickets",
        "description": ("Ticket subject and comment fields persist HTML without "
                        "sanitisation. An attacker who submits a support ticket can "
                        "execute script in the session of any support engineer who "
                        "views the ticket."),
        "impact": ("Session hijacking and credential theft in the context of support "
                   "staff, including access to internal knowledge base and customer data."),
        "evidence": ("Submitted ticket with <script> payload in the subject; payload "
                     "executed when viewed by support console (2026-07-15)."),
        "remediation": ("Encode output on render, apply a strict CSP, and enable "
                        "Content-Security-Policy headers on the portal."),
        "references": "CWE-79 / OWASP XSS",
        "status": "Open",
    },
    {
        "title": "Weak TLS Configuration with Obsolete Ciphers",
        "cvss_vector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:H",
        "affected_assets": "*.acme.com (IIS/nginx terminated endpoints)",
        "description": ("Public endpoints negotiate TLS 1.0/1.1 and CBC ciphers "
                        "(3DES, RC4). The service has no HSTS and does not support "
                        "TLS 1.3."),
        "impact": ("Downgrade and man-in-the-middle attacks can recover or tamper "
                   "with traffic, and the configuration fails current compliance "
                   "baselines."),
        "evidence": ("sslyze scan 2026-07-09: TLS 1.1 supported, RC4 accept, "
                     "HSTS header absent on all hosts."),
        "remediation": ("Restrict to TLS 1.2/1.3 with modern AEAD ciphers "
                        "(ECDHE+AESGCM/CHACHA20) and enable HSTS."),
        "references": "CWE-327 / CIS Benchmarks",
        "status": "Fixed",
    },
    {
        "title": "Sensitive Customer Data Written to Application Logs",
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:L/A:N",
        "affected_assets": "app.acme.com (log server)",
        "description": ("The payment callback logs full card metadata and PAN "
                        "fragments in plaintext, and log files are readable by "
                        "the application service account."),
        "impact": ("If the logs are exfiltrated, cardholder data is exposed in "
                   "violation of PCI-DSS logging requirements."),
        "evidence": ("Grep of /var/log/app/payment.log showed full card fingerprint "
                     "values in 4,000+ entries."),
        "remediation": ("Mask sensitive fields at the log source, centralise logs "
                        "with retention controls, and restrict file permissions."),
        "references": "CWE-532 / PCI-DSS 10.2",
        "status": "Accepted",
    },
    {
        "title": "Physical Access Information Disclosure at Reception Kiosk",
        "cvss_vector": "CVSS:3.1/AV:P/AC:H/PR:H/UI:R/S:U/C:L/I:L/A:L",
        "affected_assets": "Lobby visitor management kiosk",
        "description": ("The visitor kiosk stores the last-visited employee name and "
                        "badge number in a local cookie that is echoed back verbatim "
                        "on the confirmation page."),
        "impact": ("A physically present attacker with brief console access could "
                   "leak a previous visitor's badge identifier."),
        "evidence": ("Observed cookie value echoed in HTML source on confirmation "
                     "screen (2026-07-10)."),
        "remediation": ("Remove the echoed value, store the reference server-side, "
                        "and add kiosk minimal privilege policy."),
        "references": "CWE-200 / ISO 27001 A.11",
        "status": "Closed",
    },
]