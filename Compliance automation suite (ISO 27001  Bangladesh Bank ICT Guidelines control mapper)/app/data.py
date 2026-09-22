"""Control catalog datasets for the Compliance Automation Suite.

Contains a curated crosswalk of:
- ISO/IEC 27001:2022 Annex A (93 controls)
- Bangladesh Bank ICT Security Guideline v2.0 domains (18 domains, B-xxx sections)
- NIST Cybersecurity Framework 2.0 (22 categories across 6 functions)

The data is a practical audit-oriented subset with keyword-based crosswalk links.
Swap this module out for a full dataset (e.g. loaded from JSON/Excel) without
touching the rest of the application.
"""

# ---------------------------------------------------------------------------
# Framework definitions
# ---------------------------------------------------------------------------

FRAMEWORKS = {
    "iso27001": {
        "id": "iso27001",
        "name": "ISO/IEC 27001:2022 — Annex A",
        "short": "ISO 27001",
        "accent": "#3b82f6",
        "description": "International standard for information security management systems (ISMS), Annex A control set (93 controls in 4 themes).",
    },
    "bbict": {
        "id": "bbict",
        "name": "Bangladesh Bank ICT Security Guideline v2.0",
        "short": "BB ICT Guideline",
        "accent": "#10b981",
        "description": "Regulatory ICT security requirements for banks and non-bank financial institutions in Bangladesh, issued by Bangladesh Bank.",
    },
    "nistcsf": {
        "id": "nistcsf",
        "name": "NIST Cybersecurity Framework 2.0",
        "short": "NIST CSF 2.0",
        "accent": "#f59e0b",
        "description": "US NIST framework organized around GOVERN, IDENTIFY, PROTECT, DETECT, RESPOND and RECOVER functions.",
    },
}

# ---------------------------------------------------------------------------
# ISO/IEC 27001:2022 Annex A — 93 controls
# id, title, theme
# ---------------------------------------------------------------------------

ISO27001_CONTROLS = [
    ("A.5.1", "Policies for information security", "Organizational"),
    ("A.5.2", "Information security roles and responsibilities", "Organizational"),
    ("A.5.3", "Segregation of duties", "Organizational"),
    ("A.5.4", "Management responsibilities", "Organizational"),
    ("A.5.5", "Contact with authorities", "Organizational"),
    ("A.5.6", "Contact with special interest groups", "Organizational"),
    ("A.5.7", "Threat intelligence", "Organizational"),
    ("A.5.8", "Information security in project management", "Organizational"),
    ("A.5.9", "Inventory of information and other associated assets", "Organizational"),
    ("A.5.10", "Acceptable use of information and other associated assets", "Organizational"),
    ("A.5.11", "Return of assets", "Organizational"),
    ("A.5.12", "Classification of information", "Organizational"),
    ("A.5.13", "Labelling of information", "Organizational"),
    ("A.5.14", "Information transfer", "Organizational"),
    ("A.5.15", "Access control", "Organizational"),
    ("A.5.16", "Identity management", "Organizational"),
    ("A.5.17", "Authentication information", "Organizational"),
    ("A.5.18", "Access rights", "Organizational"),
    ("A.5.19", "Information security in supplier relationships", "Organizational"),
    ("A.5.20", "Addressing information security within supplier agreements", "Organizational"),
    ("A.5.21", "Managing information security in the ICT supply chain", "Organizational"),
    ("A.5.22", "Monitoring, review and change management of supplier services", "Organizational"),
    ("A.5.23", "Information security for use of cloud services", "Organizational"),
    ("A.5.24", "Information security incident management planning and preparation", "Organizational"),
    ("A.5.25", "Assessment and decision on information security events", "Organizational"),
    ("A.5.26", "Response to information security incidents", "Organizational"),
    ("A.5.27", "Learning from information security incidents", "Organizational"),
    ("A.5.28", "Collection of evidence", "Organizational"),
    ("A.5.29", "Information security during disruption", "Organizational"),
    ("A.5.30", "ICT readiness for business continuity", "Organizational"),
    ("A.5.31", "Legal, statutory, regulatory and contractual requirements", "Organizational"),
    ("A.5.32", "Intellectual property rights", "Organizational"),
    ("A.5.33", "Protection of records", "Organizational"),
    ("A.5.34", "Privacy and protection of PII", "Organizational"),
    ("A.5.35", "Independent review of information security", "Organizational"),
    ("A.5.36", "Compliance with policies, rules and standards", "Organizational"),
    ("A.5.37", "Documented operating procedures", "Organizational"),
    ("A.6.1", "Screening", "People"),
    ("A.6.2", "Terms and conditions of employment", "People"),
    ("A.6.3", "Information security awareness, education and training", "People"),
    ("A.6.4", "Disciplinary process", "People"),
    ("A.6.5", "Responsibilities after termination or change of employment", "People"),
    ("A.6.6", "Confidentiality or non-disclosure agreements", "People"),
    ("A.6.7", "Remote working", "People"),
    ("A.6.8", "Information security event reporting", "People"),
    ("A.7.1", "Physical security perimeters", "Physical"),
    ("A.7.2", "Physical entry", "Physical"),
    ("A.7.3", "Securing offices, rooms and facilities", "Physical"),
    ("A.7.4", "Physical security monitoring", "Physical"),
    ("A.7.5", "Protecting against physical and environmental threats", "Physical"),
    ("A.7.6", "Working in secure areas", "Physical"),
    ("A.7.7", "Clear desk and clear screen", "Physical"),
    ("A.7.8", "Equipment siting and protection", "Physical"),
    ("A.7.9", "Security of assets off-premises", "Physical"),
    ("A.7.10", "Storage media", "Physical"),
    ("A.7.11", "Supporting utilities", "Physical"),
    ("A.7.12", "Cabling security", "Physical"),
    ("A.7.13", "Equipment maintenance", "Physical"),
    ("A.7.14", "Secure disposal or re-use of equipment", "Physical"),
    ("A.8.1", "User endpoint devices", "Technological"),
    ("A.8.2", "Privileged access rights", "Technological"),
    ("A.8.3", "Information access restriction", "Technological"),
    ("A.8.4", "Access to source code", "Technological"),
    ("A.8.5", "Secure authentication", "Technological"),
    ("A.8.6", "Capacity management", "Technological"),
    ("A.8.7", "Protection against malware", "Technological"),
    ("A.8.8", "Management of technical vulnerabilities", "Technological"),
    ("A.8.9", "Configuration management", "Technological"),
    ("A.8.10", "Information deletion", "Technological"),
    ("A.8.11", "Data masking", "Technological"),
    ("A.8.12", "Data leakage prevention", "Technological"),
    ("A.8.13", "Information backup", "Technological"),
    ("A.8.14", "Redundancy of information processing facilities", "Technological"),
    ("A.8.15", "Logging", "Technological"),
    ("A.8.16", "Monitoring activities", "Technological"),
    ("A.8.17", "Clock synchronization", "Technological"),
    ("A.8.18", "Use of privileged utility programs", "Technological"),
    ("A.8.19", "Installation of software on operational systems", "Technological"),
    ("A.8.20", "Networks security", "Technological"),
    ("A.8.21", "Security of network services", "Technological"),
    ("A.8.22", "Segregation of networks", "Technological"),
    ("A.8.23", "Web filtering", "Technological"),
    ("A.8.24", "Use of cryptography", "Technological"),
    ("A.8.25", "Secure development life cycle", "Technological"),
    ("A.8.26", "Application security requirements", "Technological"),
    ("A.8.27", "Secure system architecture and engineering principles", "Technological"),
    ("A.8.28", "Secure coding", "Technological"),
    ("A.8.29", "Security testing in development and acceptance", "Technological"),
    ("A.8.30", "Outsourced development", "Technological"),
    ("A.8.31", "Separation of development, test and production environments", "Technological"),
    ("A.8.32", "Change management", "Technological"),
    ("A.8.33", "Test information", "Technological"),
    ("A.8.34", "Protection of information systems during audit testing", "Technological"),
]

# ---------------------------------------------------------------------------
# Bangladesh Bank ICT Security Guideline v2.0 — domains (B-xx sections)
# ---------------------------------------------------------------------------

BBICT_DOMAINS = [
    ("B-01", "ICT Governance & Security Policy", "Board-approved ICT security policy, governance committee, security steering, regulatory reporting."),
    ("B-02", "Organization & Roles", "CISO appointment, ICT security officer, segregation of duties, third-party/vendor management ownership."),
    ("B-03", "Asset Management & Classification", "Asset inventory, information classification, labelling, acceptable use."),
    ("B-04", "Human Resources Security", "Employee screening, NDAs, security awareness training, termination process."),
    ("B-05", "Physical & Environmental Security", "Data centre security, CCTV, access control, fire suppression, power backup (IPS/UPS/generator)."),
    ("B-06", "Access Control & Identity Management", "User access management, least privilege, privileged access, password policy, MFA, periodic access review."),
    ("B-07", "Network Security", "Network segmentation, DMZ, firewall, IDS/IPS, wireless security, VPN for branch connectivity."),
    ("B-08", "Endpoint & Server Security", "Hardening, anti-malware, patch management, endpoint protection, removable media control."),
    ("B-09", "Application Security & SDLC", "Secure development, application testing, change management, separation of environments."),
    ("B-10", "Cryptography & Key Management", "Encryption of data in transit/at rest, HSM, key lifecycle management, PKI for payments."),
    ("B-11", "Logging, Monitoring & SOC", "Centralized log server, SIEM/SOC, time synchronization, log retention (audit trail)."),
    ("B-12", "Incident Management & Forensics", "Incident response plan, reporting to Bangladesh Bank, forensics capability, lessons learned."),
    ("B-13", "Business Continuity & Disaster Recovery", "BCP/DRP, alternate processing site, RTO/RPO, DR drill/testing, ICT readiness."),
    ("B-14", "Outsourcing & Third-Party / Cloud", "Outsourcing approval, vendor due diligence, SLA, right-to-audit, cloud usage governance."),
    ("B-15", "Vulnerability & Patch Management", "Vulnerability assessment, penetration testing, remediation tracking, threat intelligence."),
    ("B-16", "Data Privacy & Customer Information", "Protection of customer PII, data leakage prevention, data retention and secure disposal."),
    ("B-17", "Cyber Resilience & Threat Management", "Cyber threat management, red teaming, cyber crisis simulation, resilience testing."),
    ("B-18", "Compliance, Audit & Reporting", "Internal/external ICT audit, compliance reporting to BB, regulator inspection readiness."),
]

# ---------------------------------------------------------------------------
# NIST CSF 2.0 — functions and categories
# ---------------------------------------------------------------------------

NIST_CSF_CATEGORIES = [
    ("GV", "GOVERN", None, "Organizational context, roles, policy, oversight, cybersecurity supply chain."),
    ("GV.OC", "Organizational Context", "GOVERN", "Mission, stakeholders, legal/regulatory requirements are understood."),
    ("GV.RM", "Risk Management Strategy", "GOVERN", "Risk objectives, appetite, tolerance are established and communicated."),
    ("GV.RR", "Roles, Responsibilities, and Authority", "GOVERN", "Adequate authority and resources allocated for cybersecurity risk management."),
    ("GV.PO", "Policy", "GOVERN", "Organizational cybersecurity policy is established, communicated, enforced."),
    ("GV.OV", "Oversight", "GOVERN", "Cybersecurity risk management strategy performance reviewed and adjusted."),
    ("GV.SC", "Cybersecurity Supply Chain Risk Management", "GOVERN", "Supplier risk is managed across the supply chain."),
    ("ID", "IDENTIFY", None, "Understanding of assets, risks, and the attack surface."),
    ("ID.AM", "Asset Management", "IDENTIFY", "Assets and data flows inventoried and managed."),
    ("ID.RA", "Risk Assessment", "IDENTIFY", "Vulnerabilities, threats and risks are identified and prioritized."),
    ("ID.IM", "Improvement", "IDENTIFY", "Improvements are identified from analyses and tests."),
    ("PR", "PROTECT", None, "Safeguards to prevent or limit cybersecurity incidents."),
    ("PR.AA", "Identity Management, Authentication, and Access Control", "PROTECT", "Identity, credentials and access managed with least privilege."),
    ("PR.AT", "Awareness and Training", "PROTECT", "Personnel are provided cybersecurity awareness and training."),
    ("PR.DS", "Data Security", "PROTECT", "Data is managed consistent with risk (at rest, in transit, in use)."),
    ("PR.PS", "Platform Security", "PROTECT", "Hardware, software and services are managed consistent with risk."),
    ("PR.IR", "Technology Infrastructure Resilience", "PROTECT", "Networks and infrastructure protected from unauthorized logical access."),
    ("DE", "DETECT", None, "Analysis to identify cybersecurity events and incidents."),
    ("DE.CM", "Continuous Monitoring", "DETECT", "Assets monitored to identify potential incidents."),
    ("DE.AE", "Adverse Event Analysis", "DETECT", "Anomalous activities detected and potential incidents analyzed."),
    ("RS", "RESPOND", None, "Action taken regarding a detected cybersecurity incident."),
    ("RS.MA", "Incident Management", "RESPOND", "Incidents triaged, prioritized, managed and escalated."),
    ("RS.AN", "Incident Analysis", "RESPOND", "Incidents investigated; impact and root cause understood."),
    ("RS.CO", "Incident Response Reporting and Communication", "RESPOND", "Response activities coordinated with internal and external stakeholders."),
    ("RS.MI", "Incident Mitigation", "RESPOND", "Incidents contained and eradicated."),
    ("RC", "RECOVER", None, "Activities to restore operations and reduce impact."),
    ("RC.RP", "Incident Recovery Plan Execution", "RECOVER", "Recovery activities executed per plan."),
    ("RC.CO", "Incident Recovery Communication", "RECOVER", "Recovery activities and progress communicated to stakeholders."),
]

# ---------------------------------------------------------------------------
# Keyword crosswalk: each BB domain maps to ISO Annex A controls and NIST
# categories by keyword overlap. Kept explicit for auditability.
# ---------------------------------------------------------------------------

BBICT_TO_ISO = {
    "B-01": ["A.5.1", "A.5.2", "A.5.31", "A.5.36", "A.5.37"],
    "B-02": ["A.5.2", "A.5.3", "A.5.4"],
    "B-03": ["A.5.9", "A.5.10", "A.5.12", "A.5.13", "A.5.11"],
    "B-04": ["A.6.1", "A.6.2", "A.6.3", "A.6.4", "A.6.5", "A.6.6"],
    "B-05": ["A.7.1", "A.7.2", "A.7.3", "A.7.4", "A.7.5", "A.7.6", "A.7.11"],
    "B-06": ["A.5.15", "A.5.16", "A.5.17", "A.5.18", "A.8.2", "A.8.5"],
    "B-07": ["A.8.20", "A.8.21", "A.8.22", "A.8.23"],
    "B-08": ["A.8.1", "A.8.7", "A.8.8", "A.8.9", "A.8.19"],
    "B-09": ["A.8.25", "A.8.26", "A.8.27", "A.8.28", "A.8.29", "A.8.31", "A.8.32"],
    "B-10": ["A.8.24", "A.5.33"],
    "B-11": ["A.8.15", "A.8.16", "A.8.17"],
    "B-12": ["A.5.24", "A.5.25", "A.5.26", "A.5.27", "A.5.28", "A.6.8"],
    "B-13": ["A.5.29", "A.5.30", "A.8.13", "A.8.14"],
    "B-14": ["A.5.19", "A.5.20", "A.5.21", "A.5.22", "A.5.23", "A.8.30"],
    "B-15": ["A.5.7", "A.8.8"],
    "B-16": ["A.5.34", "A.8.10", "A.8.11", "A.8.12", "A.5.14"],
    "B-17": ["A.5.7", "A.5.24", "A.8.16"],
    "B-18": ["A.5.35", "A.5.36", "A.5.31"],
}

BBICT_TO_NIST = {
    "B-01": ["GV.PO", "GV.OV", "GV.RM"],
    "B-02": ["GV.RR"],
    "B-03": ["ID.AM"],
    "B-04": ["PR.AT"],
    "B-05": ["PR.PS"],
    "B-06": ["PR.AA"],
    "B-07": ["PR.IR"],
    "B-08": ["PR.PS"],
    "B-09": ["PR.PS", "ID.IM"],
    "B-10": ["PR.DS"],
    "B-11": ["DE.CM", "DE.AE"],
    "B-12": ["RS.MA", "RS.AN", "RS.CO"],
    "B-13": ["RC.RP", "RC.CO"],
    "B-14": ["GV.SC"],
    "B-15": ["ID.RA", "ID.IM"],
    "B-16": ["PR.DS"],
    "B-17": ["ID.RA", "RS.MI"],
    "B-18": ["GV.OV", "GV.PO"],
}

# Statuses used by the assessments
STATUSES = ["Implemented", "Partially Implemented", "Planned", "Not Implemented", "Not Applicable"]

STATUS_SCORES = {
    "Implemented": 1.0,
    "Partially Implemented": 0.5,
    "Planned": 0.25,
    "Not Implemented": 0.0,
    "Not Applicable": None,
}
