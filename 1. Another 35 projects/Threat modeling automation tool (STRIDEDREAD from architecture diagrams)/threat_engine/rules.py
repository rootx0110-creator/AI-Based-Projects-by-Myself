"""Threat template library: STRIDE categories + base DREAD scores.

Each template has:
    title, description, mitigation, dread {damage, reproducibility,
    exploitability, affected_users, discoverability} (1-10 each).

Rules are keyed by (element_kind, element_type, stride_letter). The wildcard
type "any" supplies generic per-kind coverage. Analyzer merges the exact type
rule with the "any" rule for the same stride and dedupes by title.
"""

STRIDE = {
    "S": "Spoofing",
    "T": "Tampering",
    "R": "Repudiation",
    "I": "Information Disclosure",
    "D": "Denial of Service",
    "E": "Elevation of Privilege",
}

STRIDE_PROPERTY = {
    "S": "Authentication",
    "T": "Integrity",
    "R": "Non-repudiation",
    "I": "Confidentiality",
    "D": "Availability",
    "E": "Authorization",
}

DREAD_FACTORS = [
    ("damage", "Damage"),
    ("reproducibility", "Reproducibility"),
    ("exploitability", "Exploitability"),
    ("affected_users", "Affected Users"),
    ("discoverability", "Discoverability"),
]

# ----------------------------------------------------------------------------
# Generic rules per element kind
# ----------------------------------------------------------------------------

GENERIC = {}

# ---------------- processes (any type) ----------------
GENERIC[("process", "any", "S")] = [
    {
        "title": "Service identity spoofing",
        "description": "An attacker masquerades as this component on the network or in service-to-service calls, tricking other components and operators into trusting forged traffic.",
        "mitigation": "Use mutual TLS and strong service identities (SPIFFE/SPIRE, client certificates); isolate on private networks; verify peer identities before trusting input.",
        "dread": {"damage": 7, "reproducibility": 8, "exploitability": 6, "affected_users": 7, "discoverability": 5},
    }
]
GENERIC[("process", "any", "T")] = [
    {
        "title": "Unauthorized modification of process or configuration",
        "description": "An attacker with write access or a poisoned supply chain can tamper with the binary, runtime state, or configuration of this component, altering its behaviour.",
        "mitigation": "Sign and pin artifacts, verify supply chain integrity, run read-only filesystems, hash critical config, restrict access to runtime management interfaces.",
        "dread": {"damage": 8, "reproducibility": 7, "exploitability": 5, "affected_users": 8, "discoverability": 4},
    }
]
GENERIC[("process", "any", "R")] = [
    {
        "title": "Security actions performed without an audit trail",
        "description": "Actions taken by or against this component are not recorded in an immutable, attributed log, allowing principals to deny their activity after the fact.",
        "mitigation": "Centralize logging, write to append-only / WORM stores, bind log entries to authenticated identities, sync clocks and monitor log integrity (hash chaining).",
        "dread": {"damage": 6, "reproducibility": 8, "exploitability": 7, "affected_users": 6, "discoverability": 7},
    }
]
GENERIC[("process", "any", "I")] = [
    {
        "title": "Sensitive data exposed by the process",
        "description": "Debug endpoints, verbose errors, memory dumps, or over-broad logs can leak credentials, internal paths and sensitive data processed by this component.",
        "mitigation": "Disable debug modes in production, use custom error pages, redact PII/secrets in logs, enforce memory protections and secure deserialization.",
        "dread": {"damage": 7, "reproducibility": 6, "exploitability": 5, "affected_users": 7, "discoverability": 6},
    }
]
GENERIC[("process", "any", "D")] = [
    {
        "title": "Resource exhaustion denial of service",
        "description": "CPU, memory, sockets, threads or exhausting storage can be exhausted by excessive or malicious load, making the component unavailable.",
        "mitigation": "Impose rate limits and quotas, allow auto-scaling, isolate noisy neighbours, set connection/keep-alive limits and circuit breakers.",
        "dread": {"damage": 6, "reproducibility": 8, "exploitability": 7, "affected_users": 8, "discoverability": 5},
    }
]
GENERIC[("process", "any", "E")] = [
    {
        "title": "Privilege escalation within the process",
        "description": "Exploitable flaws or misconfigured roles allow the attacker to escalate to root/administrator or reach functions beyond their authorization level.",
        "mitigation": "Run with least privilege, apply RBAC/ABAC consistently, patch promptly, apply container hardening and kernel hardening, segregate admin functions.",
        "dread": {"damage": 9, "reproducibility": 6, "exploitability": 6, "affected_users": 8, "discoverability": 4},
    }
]

# ---------------- data stores (any type) ----------------
GENERIC[("data_store", "any", "S")] = [
    {
        "title": "Data store impersonation or credential abuse",
        "description": "A rogue client or a stolen credential can impersonate a legitimate owner of the data, or impersonate the store itself in replication/cluster chatter.",
        "mitigation": "Enforce strong authentication (mutual TLS, client certificates, per-application credentials), avoid shared/default passwords, rotate secrets automatically.",
        "dread": {"damage": 8, "reproducibility": 7, "exploitability": 5, "affected_users": 8, "discoverability": 4},
    }
]
GENERIC[("data_store", "any", "T")] = [
    {
        "title": "Unauthorized modification of stored data",
        "description": "Data in this store can be altered, inserted or deleted without authorization, corrupting business logic and downstream consumers.",
        "mitigation": "Restrict write access to minimal roles, validate at the application layer, enable encryption at rest, control physical and logical access, use integrity checks.",
        "dread": {"damage": 9, "reproducibility": 7, "exploitability": 4, "affected_users": 8, "discoverability": 3},
    }
]
GENERIC[("data_store", "any", "R")] = [
    {
        "title": "Data changes without audit or attribution",
        "description": "Reads and writes to this store are not reliably attributed to an identity, so culpability for breaches or corruption cannot be established.",
        "mitigation": "Enable native audit logging, capture change-data-capture streams, require attributed application credentials, review and retain audit evidence.",
        "dread": {"damage": 6, "reproducibility": 7, "exploitability": 6, "affected_users": 6, "discoverability": 6},
    }
]
GENERIC[("data_store", "any", "I")] = [
    {
        "title": "Unauthorized disclosure of stored data",
        "description": "Backups, snapshots, mis-scoped queries, or over-broad grants expose the data to people and systems that should not see it.",
        "mitigation": "Encrypt at rest, apply column/field-level encryption for sensitive values, grant least-privilege in read paths, mask backups and anomaly-alert on bulk reads.",
        "dread": {"damage": 9, "reproducibility": 8, "exploitability": 5, "affected_users": 8, "discoverability": 5},
    }
]
GENERIC[("data_store", "any", "D")] = [
    {
        "title": "Storage exhaustion or lock contention",
        "description": "Filling disk, exhausting connections, or long-running transactions can degrade or halt service for every consumer of the store.",
        "mitigation": "Provision capacity with headroom, set storage quotas, use partitioning and read replicas, query timeouts, connection pooling and monitoring.",
        "dread": {"damage": 6, "reproducibility": 7, "exploitability": 6, "affected_users": 8, "discoverability": 4},
    }
]
GENERIC[("data_store", "any", "E")] = [
    {
        "title": "Over-privileged accounts reach restricted data",
        "description": "Shared admin/DBA accounts or over-broad grants allow a compromised lower-tier principal to read or change data far above its privilege level.",
        "mitigation": "Apply RBAC/row-level security, use just-in-time elevation, separate duties, rotate and audit privileged accounts continuously.",
        "dread": {"damage": 9, "reproducibility": 6, "exploitability": 5, "affected_users": 8, "discoverability": 3},
    }
]

# ---------------- external entities (any type) ----------------
GENERIC[("external_entity", "any", "S")] = [
    {
        "title": "External entity impersonation",
        "description": "An attacker can impersonate the external user or partner system, gaining the trust and privileges that genuinely belong to it.",
        "mitigation": "Require strong authentication (MFA, federated identity), verify signer identity on incoming requests, and enroll/register high-value partners.",
        "dread": {"damage": 8, "reproducibility": 8, "exploitability": 6, "affected_users": 7, "discoverability": 5},
    }
]
GENERIC[("external_entity", "any", "T")] = [
    {
        "title": "Malicious input from external entity",
        "description": "Content supplied by the external entity is processed without validation, allowing injection, tampered payloads, or malformed data into the system.",
        "mitigation": "Validate and normalise input at every trust boundary, apply allowlists, verify signatures/checksums on payloads and sanitise before use.",
        "dread": {"damage": 8, "reproducibility": 8, "exploitability": 7, "affected_users": 7, "discoverability": 6},
    }
]
GENERIC[("external_entity", "any", "R")] = [
    {
        "title": "External actions without non-repudiation",
        "description": "Requests and instructions received from the entity carry no proof of origin, so legitimate or malicious actions can later be denied.",
        "mitigation": "Require signed requests / webhook signatures, issue receipts and sequence numbers, keep attributed audit records of external interactions.",
        "dread": {"damage": 5, "reproducibility": 7, "exploitability": 7, "affected_users": 5, "discoverability": 7},
    }
]
GENERIC[("external_entity", "any", "I")] = [
    {
        "title": "Data over-sharing to the external entity",
        "description": "The system returns more data than the entity needs, or fails to filter sensitive fields, disclosing information it should never receive.",
        "mitigation": "Apply data minimisation, return field-filtered responses, enforce need-to-know in integrations and review API contracts annually.",
        "dread": {"damage": 7, "reproducibility": 6, "exploitability": 6, "affected_users": 6, "discoverability": 6},
    }
]
GENERIC[("external_entity", "any", "D")] = [
    {
        "title": "External entity flooding the system",
        "description": "The entity, or an attacker posing as it, floods the platform with requests, uploads or transactions, exhausting capacity for everyone.",
        "mitigation": "Rate limit per identity and IP, apply quotas and bot management, throttle large uploads and alert on anomalous volumes.",
        "dread": {"damage": 5, "reproducibility": 8, "exploitability": 8, "affected_users": 7, "discoverability": 6},
    }
]
GENERIC[("external_entity", "any", "E")] = [
    {
        "title": "External entity granted excessive privileges",
        "description": "The external principal can reach functionality or data reserved for internal roles, effectively elevating its own authority.",
        "mitigation": "Enforce least privilege server-side, never trust client-sent roles, scope API tokens to specific capabilities and periodically audit entitlements.",
        "dread": {"damage": 8, "reproducibility": 7, "exploitability": 6, "affected_users": 8, "discoverability": 5},
    }
]

# ---------------- data flows (any type) ----------------
GENERIC[("data_flow", "any", "S")] = [
    {
        "title": "Endpoint spoofing on the data flow (MITM)",
        "description": "An attacker intercepts the communication and impersonates one of the endpoints (ARP/DNS spoofing, rogue intermediate), gaining the trust of both sides.",
        "mitigation": "Use TLS with certificate verification and pinning for critical clients, mutual auth where appropriate, and keep traffic on private, controlled networks.",
        "dread": {"damage": 8, "reproducibility": 7, "exploitability": 6, "affected_users": 7, "discoverability": 5},
    }
]
GENERIC[("data_flow", "any", "T")] = [
    {
        "title": "In-transit modification of messages",
        "description": "Messages exchanged over this flow can be altered, reordered or replayed without detection, changing the meaning of the data.",
        "mitigation": "Protect integrity with TLS and signed/HMAC message payloads, include sequence numbers and anti-replay nonces, validate at the receiving end.",
        "dread": {"damage": 8, "reproducibility": 7, "exploitability": 5, "affected_users": 7, "discoverability": 4},
    }
]
GENERIC[("data_flow", "any", "R")] = [
    {
        "title": "Exchanged messages without non-repudiation evidence",
        "description": "Neither endpoint can prove what was sent/received over this flow, allowing denial of transactions or commands.",
        "mitigation": "Sign payloads, log activities at both ends with attributed identities, and maintain tamper-evident audit trails of the exchange.",
        "dread": {"damage": 5, "reproducibility": 7, "exploitability": 7, "affected_users": 5, "discoverability": 6},
    }
]
GENERIC[("data_flow", "any", "I")] = [
    {
        "title": "Eavesdropping / cleartext transit",
        "description": "Data travelling over this flow can be observed by anyone on the path (sniffing, rogue WAN, misconfigured proxies) if it is not encrypted.",
        "mitigation": "Encrypt all traffic in transit (TLS 1.2+, HSTS for web, VPN for private links), avoid plaintext protocols, and encrypt highly sensitive payloads end-to-end.",
        "dread": {"damage": 9, "reproducibility": 8, "exploitability": 5, "affected_users": 8, "discoverability": 5},
    }
]
GENERIC[("data_flow", "any", "D")] = [
    {
        "title": "Flow flooding / link saturation",
        "description": "Amplified or excessive traffic on the flow saturates bandwidth or the receiver, causing dropped message handling and outages.",
        "mitigation": "Limit message size and rate, apply throttling and QoS, use retry/backoff at the edge, and design for graceful degradation.",
        "dread": {"damage": 6, "reproducibility": 8, "exploitability": 7, "affected_users": 7, "discoverability": 6},
    }
]
GENERIC[("data_flow", "any", "E")] = [
    {
        "title": "Flow used to bypass trust boundary controls",
        "description": "Data crossing a trust boundary is accepted without re-authentication of the sender, allowing forged internal messages to reach trusted zones.",
        "mitigation": "Re-authenticate and re-authorize across every boundary, validate message-level identity, apply network segmentation and prioritize defense-in-depth.",
        "dread": {"damage": 9, "reproducibility": 7, "exploitability": 6, "affected_users": 8, "discoverability": 4},
    }
]

# ----------------------------------------------------------------------------
# Type-specific rules (adds detail on top of the generic ones)
# ----------------------------------------------------------------------------

TYPE_SPECIFIC = {}

# ---------------- processes: web_application ----------------
TYPE_SPECIFIC[("process", "web_application", "S")] = [
    {
        "title": "Session hijacking / credential replay",
        "description": "Session tokens or user credentials against the web application can be stolen (XSS, leaked cookies) or replayed, impersonating authenticated users.",
        "mitigation": "HttpOnly/Secure cookies, short-lived sessions with rotation, CSRF protections, MFA and device/behavioural signals for high-risk actions.",
        "dread": {"damage": 8, "reproducibility": 7, "exploitability": 7, "affected_users": 8, "discoverability": 6},
    }
]
TYPE_SPECIFIC[("process", "web_application", "T")] = [
    {
        "title": "Injection attacks manipulating application logic",
        "description": "SQL, command, LDAP or server-side template injection in user inputs can modify data or execute arbitrary operations against the application database.",
        "mitigation": "Parameterized queries, output encoding, strict input validation, a WAF for defense-in-depth, and least-privilege DB accounts.",
        "dread": {"damage": 9, "reproducibility": 8, "exploitability": 7, "affected_users": 9, "discoverability": 7},
    }
]
TYPE_SPECIFIC[("process", "web_application", "R")] = [
    {
        "title": "User actions not attributable",
        "description": "Web requests and state changes are not tied to verifiable identities, so misuse cannot be attributed to a specific account.",
        "mitigation": "Persist attributed access logs, tie sessions to audit identities, add non-repudiation for sensitive transactions (confirm dialogs + signed records).",
        "dread": {"damage": 6, "reproducibility": 7, "exploitability": 7, "affected_users": 7, "discoverability": 7},
    }
]
TYPE_SPECIFIC[("process", "web_application", "I")] = [
    {
        "title": "Broken access control exposing data (IDOR)",
        "description": "Direct object references and client-controlled identifiers let users request objects they do not own, disclosing other users' data.",
        "mitigation": "Server-side authorization on every object access, opaque references (UUIDs), enforce tenant isolation and test with horizontal/vertical privilege tests.",
        "dread": {"damage": 8, "reproducibility": 8, "exploitability": 7, "affected_users": 8, "discoverability": 6},
    }
]
TYPE_SPECIFIC[("process", "web_application", "D")] = [
    {
        "title": "Application-layer DDoS / slowloris",
        "description": "HTTP floods, slow reads and expensive request chains exhaust worker threads and backend connections, denying service to legitimate users.",
        "mitigation": "Edge CDN/WAF filtering, connection limits and keep-alive timeouts, request size limits, autoscaling and throttling of costly endpoints.",
        "dread": {"damage": 5, "reproducibility": 8, "exploitability": 7, "affected_users": 8, "discoverability": 6},
    }
]
TYPE_SPECIFIC[("process", "web_application", "E")] = [
    {
        "title": "Missing function-level authorization",
        "description": "Admin or privileged functions are reachable by normal users because authorization is checked inconsistently or only client-side.",
        "mitigation": "Enforce role checks server-side for every privileged route, apply a default-deny policy and harden admin surfaces with extra factors.",
        "dread": {"damage": 9, "reproducibility": 7, "exploitability": 6, "affected_users": 8, "discoverability": 5},
    }
]

# ---------------- processes: api_service / microservice ----------------
for _app in ("api_service", "microservice"):
    TYPE_SPECIFIC[("process", _app, "S")] = [
        {
            "title": "API credential / JWT forgery",
            "description": "Stolen, weakly-signed or confused-deputy tokens can authenticate as a legitimate service or user against this API.",
            "mitigation": "OAuth2/OIDC with short-lived signed tokens, audience/issuer validation, token rotation and revocation, strong key mgmt and secure storage.",
            "dread": {"damage": 8, "reproducibility": 8, "exploitability": 7, "affected_users": 8, "discoverability": 5},
        }
    ]
    TYPE_SPECIFIC[("process", _app, "T")] = [
        {
            "title": "Request payload tampering / mass assignment",
            "description": "Clients can override protected fields or pollute parameters (mass assignment, parameter pollution) because schemas are not enforced strictly.",
            "mitigation": "Strict schema/allowlist validation, DTOs and explicit field allowlists, reject unknown fields, and sign sensitive payloads where integrity matters.",
            "dread": {"damage": 7, "reproducibility": 8, "exploitability": 7, "affected_users": 7, "discoverability": 6},
        }
    ]
    TYPE_SPECIFIC[("process", _app, "I")] = [
        {
            "title": "Excessive data exposure in API responses",
            "description": "Responses return more fields than required (over-fetching), leaking internal fields, foreign keys or user data not needed by the caller.",
            "mitigation": "Shape responses with DTOs/field filters, audit response schemas, and mask sensitive attributes unless explicitly requested with authorization.",
            "dread": {"damage": 6, "reproducibility": 7, "exploitability": 7, "affected_users": 6, "discoverability": 6},
        }
    ]
    TYPE_SPECIFIC[("process", _app, "D")] = [
        {
            "title": "Expensive endpoint abuse",
            "description": "Unpaginated, unbounded or computation-heavy endpoints can be hammered to exhaust compute, memory or backend connections.",
            "mitigation": "Enforce pagination and query-cost limits, per-tenant rate quotas, caching of hot responses and payload/result-size caps.",
            "dread": {"damage": 5, "reproducibility": 8, "exploitability": 7, "affected_users": 7, "discoverability": 6},
        }
    ]
    TYPE_SPECIFIC[("process", _app, "E")] = [
        {
            "title": "Lateral movement from a compromised service",
            "description": "If this service is compromised, its credentials and reachable neighbours allow the attacker to move laterally across the fleet.",
            "mitigation": "Per-service credentials (never shared secrets), network policy isolation/cross-zone egress control, service mesh mTLS and blast-radius reduction.",
            "dread": {"damage": 9, "reproducibility": 6, "exploitability": 5, "affected_users": 8, "discoverability": 3},
        }
    ]

# ---------------- processes: identity_provider ----------------
TYPE_SPECIFIC[("process", "identity_provider", "S")] = [
    {
        "title": "IdP impersonation / phishing for tokens",
        "description": "Lookalike domains and malicious OAuth consent screens impersonate the identity provider to harvest credentials or authorization grants.",
        "mitigation": "Phishing-resistant MFA (FIDO2/WebAuthn), registrable-domain checks on redirect URIs, branded login surfaces and domain/web reputation monitoring.",
        "dread": {"damage": 10, "reproducibility": 7, "exploitability": 6, "affected_users": 9, "discoverability": 8},
    }
]
TYPE_SPECIFIC[("process", "identity_provider", "I")] = [
    {
        "title": "Token/session secret exposure",
        "description": "Signing keys, tokens or session stores of the identity provider are exposed through logs, misconfigured storage, or memory dumps.",
        "mitigation": "Key management service (HSM) for signing keys, token encryption, secret scanning, tight access to session stores and memory dumps prevention.",
        "dread": {"damage": 10, "reproducibility": 5, "exploitability": 4, "affected_users": 9, "discoverability": 4},
    }
]
TYPE_SPECIFIC[("process", "identity_provider", "D")] = [
    {
        "title": "Authentication service outage",
        "description": "An outage or DoS of the identity provider cascades — every dependent system that validates tokens becomes unavailable.",
        "mitigation": "Stateless/offline token validation where possible, redundant/idempotent IdP deployments, and cache verified sessions to survive brief outages.",
        "dread": {"damage": 9, "reproducibility": 7, "exploitability": 6, "affected_users": 9, "discoverability": 5},
    }
]
TYPE_SPECIFIC[("process", "identity_provider", "E")] = [
    {
        "title": "Self-service account takeover vector",
        "description": "Flaws in password reset, MFA enrollment or magic-link flows let attackers take over accounts or escalate to privileged roles.",
        "mitigation": "Rate limit and risk-check self-service flows, verify channel ownership, separate high-privilege MFA, and monitor account takeover signals.",
        "dread": {"damage": 9, "reproducibility": 7, "exploitability": 6, "affected_users": 9, "discoverability": 7},
    }
]

# ---------------- processes: load_balancer / firewall ----------------
for _app in ("load_balancer", "firewall"):
    TYPE_SPECIFIC[("process", _app, "T")] = [
        {
            "title": "Routing or rule tampering",
            "description": "Altered load-balancing/firewall rules, or poisoned routing tables, silently redirect, drop or expose traffic.",
            "mitigation": "Immutable infrastructure controls, signed rule/config updates, dedicated management plane, and change auditing with rollback.",
            "dread": {"damage": 9, "reproducibility": 6, "exploitability": 4, "affected_users": 9, "discoverability": 3},
        }
    ]
    TYPE_SPECIFIC[("process", _app, "D")] = [
        {
            "title": "Edge capacity exhaustion",
            "description": "Volumetric attacks overwhelm the edge device, dropping traffic for the entire site regardless of backend health.",
            "mitigation": "Global rate limiting, CDN/WAF shielding, anycast and geo-distribution, resource isolation and alert-based autoscale.",
            "dread": {"damage": 7, "reproducibility": 8, "exploitability": 8, "affected_users": 9, "discoverability": 6},
        }
    ]

# ---------------- processes: worker / batch ----------------
TYPE_SPECIFIC[("process", "worker", "T")] = [
    {
        "title": "Poisoned jobs / queue tampering",
        "description": "Malformed or malicious job payloads are picked from the queue and executed without validation, corrupting output or triggering arbitrary behaviour.",
        "mitigation": "Validate job schemas, version job processors, isolate execution environments and apply dead-letter and retry policies with signing.",
        "dread": {"damage": 7, "reproducibility": 7, "exploitability": 6, "affected_users": 6, "discoverability": 5},
    }
]
TYPE_SPECIFIC[("process", "worker", "D")] = [
    {
        "title": "Worker starvation or backlog flooding",
        "description": "A flood or a stuck job drains workers, backlog builds up and legitimate work is delayed or dropped.",
        "mitigation": "Concurrency caps, per-queue priorities, dead-letter handling, autoscaling workers and alerting on backlog age.",
        "dread": {"damage": 5, "reproducibility": 7, "exploitability": 6, "affected_users": 7, "discoverability": 5},
    }
]
TYPE_SPECIFIC[("process", "worker", "E")] = [
    {
        "title": "Privileged job execution",
        "description": "Jobs run with an over-privileged service account, escalating an injection into full backend/data compromise.",
        "mitigation": "Run workers with least privilege per job type, isolate per-tenant execution contexts, and rotate worker credentials continuously.",
        "dread": {"damage": 8, "reproducibility": 6, "exploitability": 6, "affected_users": 8, "discoverability": 4},
    }
]

# ---------------- processes: mobile_client / desktop_client / frontend ----------------
for _app in ("mobile_client", "desktop_client", "frontend"):
    TYPE_SPECIFIC[("process", _app, "S")] = [
        {
            "title": "Local session/credential theft",
            "description": "Credentials or session tokens stored by the client can be exfiltrated by co-installed malware or device compromise, allowing remote impersonation.",
            "mitigation": "Store secrets in OS keychains with biometric gate, prefer remote sessions, short TTLs and rotate tokens; flag high-risk contexts.",
            "dread": {"damage": 7, "reproducibility": 7, "exploitability": 7, "affected_users": 7, "discoverability": 5},
        }
    ]
    TYPE_SPECIFIC[("process", _app, "T")] = [
        {
            "title": "Client binary tampering / patching",
            "description": "The client can be repacked, patched or otherwise modified to behave maliciously; if the server trusts the client, that tampering extends into the backend.",
            "mitigation": "Code signing, integrity checks, runtime attestation (best effort), but ALWAYS treat the client as untrusted and enforce logic server-side.",
            "dread": {"damage": 6, "reproducibility": 8, "exploitability": 7, "affected_users": 6, "discoverability": 5},
        }
    ]
    TYPE_SPECIFIC[("process", _app, "I")] = [
        {
            "title": "Local sensitive data leakage",
            "description": "Caches, logs, screenshots or backups on the client device leak sensitive data to anyone with access to the device or its backups.",
            "mitigation": "Minimise local data, encrypt local stores, disable local logging of sensitive values, and purge data on logout.",
            "dread": {"damage": 6, "reproducibility": 6, "exploitability": 6, "affected_users": 6, "discoverability": 5},
        }
    ]

# ---------------- processes: iot_device ----------------
TYPE_SPECIFIC[("process", "iot_device", "S")] = [
    {
        "title": "Device identity spoofing",
        "description": "Weak or shared device credentials allow an attacker to impersonate a device and inject fake telemetry or commands.",
        "mitigation": "Per-device certificates/keys, secure element provisioning, and cryptographically verifiable device identity in registries.",
        "dread": {"damage": 7, "reproducibility": 8, "exploitability": 7, "affected_users": 5, "discoverability": 6},
    }
]
TYPE_SPECIFIC[("process", "iot_device", "T")] = [
    {
        "title": "Firmware tampering",
        "description": "Unsigned or updatable firmware can be modified to run arbitrary code, persist undetected, or target other devices on the network.",
        "mitigation": "Secure boot, signed firmware updates with rollback protection, removed debug interfaces and tamper-evident hardware.",
        "dread": {"damage": 8, "reproducibility": 8, "exploitability": 6, "affected_users": 5, "discoverability": 6},
    }
]

# ---------------- data stores: database / nosql_database ----------------
for _app in ("database", "nosql_database"):
    TYPE_SPECIFIC[("data_store", _app, "S")] = [
        {
            "title": "Stolen database credentials / rogue SQL client",
            "description": "Hardcoded or over-shared DB credentials let an attacker connect directly as a legitimate application or admin.",
            "mitigation": "Secret management (Vault/cloud KMS) with rotation, per-application logins, IP/host allowlists and monitoring for unusual direct connections.",
            "dread": {"damage": 9, "reproducibility": 7, "exploitability": 7, "affected_users": 8, "discoverability": 6},
        }
    ]
    TYPE_SPECIFIC[("data_store", _app, "T")] = [
        {
            "title": "SQL injection writing data",
            "description": "Injection through the application layer can INSERT/UPDATE/DELETE directly, silently altering records beyond the attacker's permissions.",
            "mitigation": "Parameterized queries everywhere, least-privilege DB accounts (read-only for reads), validate writes and monitor schema changes.",
            "dread": {"damage": 9, "reproducibility": 8, "exploitability": 7, "affected_users": 8, "discoverability": 6},
        }
    ]
    TYPE_SPECIFIC[("data_store", _app, "I")] = [
        {
            "title": "Unencrypted sensitive columns and broad grants",
            "description": "Sensitive fields (PII, secrets) are stored in plaintext and readable with common select grants, including by analytics and support roles.",
            "mitigation": "Encrypt sensitive columns/fields (TDE + field-level), enforce column-level or row-level security, and routinely review grants.",
            "dread": {"damage": 9, "reproducibility": 7, "exploitability": 5, "affected_users": 8, "discoverability": 5},
        }
    ]
    TYPE_SPECIFIC[("data_store", _app, "D")] = [
        {
            "title": "Runaway queries / lock storms",
            "description": "Unindexed or unbounded queries hold locks and saturate connections, stalling every dependent request.",
            "mitigation": "Query timeouts, required indexes, read replicas for reporting, connection pooling and robust error backoff.",
            "dread": {"damage": 6, "reproducibility": 7, "exploitability": 6, "affected_users": 8, "discoverability": 5},
        }
    ]
    TYPE_SPECIFIC[("data_store", _app, "E")] = [
        {
            "title": "DBA-level access abused",
            "description": "Shared superuser/DBA accounts or promotion paths let compromised lower-trust contexts escalate to full data control.",
            "mitigation": "Separation of duties, just-in-time privileged elevation with approval, audit all privileged sessions, and eliminate shared accounts.",
            "dread": {"damage": 9, "reproducibility": 6, "exploitability": 5, "affected_users": 8, "discoverability": 4},
        }
    ]

# ---------------- data stores: cache ----------------
TYPE_SPECIFIC[("data_store", "cache", "I")] = [
    {
        "title": "Sensitive data cached in plaintext",
        "description": "Cached responses or sessions may contain PII and secrets readable by anyone with cache access or across neighbouring tenants.",
        "mitigation": "Encrypt sensitive cache values, keep TTLs short, use tenant-isolated cache instances, and avoid caching unbound sensitive objects.",
        "dread": {"damage": 7, "reproducibility": 6, "exploitability": 6, "affected_users": 7, "discoverability": 5},
    }
]
TYPE_SPECIFIC[("data_store", "cache", "T")] = [
    {
        "title": "Cache poisoning",
        "description": "An attacker can inject crafted objects (HTTP cache poisoning, cache key collisions) served to many consumers.",
        "mitigation": "Validate and sign cache entries, use safe cache keys, canonicalize inputs and purge on suspicious writes.",
        "dread": {"damage": 7, "reproducibility": 8, "exploitability": 6, "affected_users": 7, "discoverability": 6},
    }
]
TYPE_SPECIFIC[("data_store", "cache", "D")] = [
    {
        "title": "Cache eviction storm / store exhaustion",
        "description": "Uncontrolled misses or memory exhaustion force constant evictions and refills, collapsing backend performance.",
        "mitigation": "Monitor hit-rates and memory, set maxmemory policies, hot/warm tiering and capacity headroom.",
        "dread": {"damage": 5, "reproducibility": 7, "exploitability": 6, "affected_users": 7, "discoverability": 5},
    }
]

# ---------------- data stores: message_queue ----------------
TYPE_SPECIFIC[("data_store", "message_queue", "T")] = [
    {
        "title": "Message injection from unauthenticated producers",
        "description": "Any actor able to reach the broker can publish forged messages that downstream consumers will trust and act on.",
        "mitigation": "Authenticate producers (ACLs, client certs), sign message envelopes and validate content schemas before consumption.",
        "dread": {"damage": 7, "reproducibility": 7, "exploitability": 7, "affected_users": 7, "discoverability": 6},
    }
]
TYPE_SPECIFIC[("data_store", "message_queue", "I")] = [
    {
        "title": "Message payload disclosure from broker",
        "description": "Plaintext messages in queues are readable by broker admins, poor ACLs, or via logs, disclosing business data in transit.",
        "mitigation": "Encrypt messages/queues at the broker, restrictive ACLs per topic, minimal retention and encrypted logging.",
        "dread": {"damage": 7, "reproducibility": 6, "exploitability": 5, "affected_users": 7, "discoverability": 4},
    }
]
TYPE_SPECIFIC[("data_store", "message_queue", "D")] = [
    {
        "title": "Broker flood / queue backlog",
        "description": "Unbounded publishing floods the broker or inflates backlog, delaying or dropping legitimate business events.",
        "mitigation": "Publisher throttling and quotas, retention caps, broker redundancy, backpressure and consumer autoscaling.",
        "dread": {"damage": 6, "reproducibility": 7, "exploitability": 7, "affected_users": 8, "discoverability": 5},
    }
]

# ---------------- data stores: file_storage ----------------
TYPE_SPECIFIC[("data_store", "file_storage", "S")] = [
    {
        "title": "Misconfigured public storage",
        "description": "Storage buckets/containers once misconfigured can be read or written by anyone on the internet - a widely exploited misconfiguration class.",
        "mitigation": "Default-deny buckets, signed URLs with short expiry, block public ACLs (block public access at the platform level), and continuous scanning.",
        "dread": {"damage": 9, "reproducibility": 9, "exploitability": 7, "affected_users": 9, "discoverability": 9},
    }
]
TYPE_SPECIFIC[("data_store", "file_storage", "T")] = [
    {
        "title": "Object overwrite / path traversal writes",
        "description": "Unsigned or signer-unsafe URLs allow overwriting objects (ransom-style) or writing outside the intended key space.",
        "mitigation": "Validate keys strictly, enforce object versioning and immutability where required, restrict write scopes, and monitor deleted/overwritten objects.",
        "dread": {"damage": 7, "reproducibility": 7, "exploitability": 6, "affected_users": 6, "discoverability": 5},
    }
]

# ---------------- external entities ----------------
TYPE_SPECIFIC[("external_entity", "user", "S")] = [
    {
        "title": "Account takeover via credential stuffing",
        "description": "Bulk attempts with breached passwords against the user population can compromise accounts and reach their data.",
        "mitigation": "MFA, breached-password screening, per-account lockout/backoff, bot detection and alerting on impossible travel.",
        "dread": {"damage": 8, "reproducibility": 8, "exploitability": 8, "affected_users": 7, "discoverability": 6},
    }
]
TYPE_SPECIFIC[("external_entity", "admin", "S")] = [
    {
        "title": "Administrator impersonation",
        "description": "Compromised or spoofed administrator identity grants full platform control to the attacker.",
        "mitigation": "Phishing-resistant MFA for admins, dedicated admin accounts (no daily-driver), just-in-time elevation, session risk checks.",
        "dread": {"damage": 10, "reproducibility": 6, "exploitability": 5, "affected_users": 9, "discoverability": 4},
    }
]
TYPE_SPECIFIC[("external_entity", "admin", "E")] = [
    {
        "title": "Excessive admin privileges / shadow admins",
        "description": "Over-broad admin roles or pervasive gatekeepers create a single compromised identity that can elevate everything.",
        "mitigation": "Least privilege + least accounts, entitlement reviews, shared-administration workflows and break-glass processes.",
        "dread": {"damage": 9, "reproducibility": 5, "exploitability": 5, "affected_users": 8, "discoverability": 4},
    }
]
TYPE_SPECIFIC[("external_entity", "third_party", "S")] = [
    {
        "title": "Compromised third-party identity",
        "description": "A partner/plugin that the platform trusts sends malicious payloads or reads data after its own compromise - supply-chain style trust abuse.",
        "mitigation": "Verify partner identity per call (signatures, OAuth), scope partner tokens narrowly, validate all payloads and monitor partner behaviour.",
        "dread": {"damage": 9, "reproducibility": 7, "exploitability": 6, "affected_users": 8, "discoverability": 5},
    }
]

# ----------------------------------------------------------------------------
# Public lookup
# ----------------------------------------------------------------------------

def rules_for(element_kind, element_type, stride):
    """Merge type-specific and generic rules for the given key (dedupe by title)."""
    out = {}
    for key in ((element_kind, element_type, stride), (element_kind, "any", stride)):
        for rule in GENERIC.get(key, []) + TYPE_SPECIFIC.get(key, []):
            out.setdefault(rule["title"], rule)
    return list(out.values())


ALL_KINDS = ("process", "data_store", "external_entity", "data_flow")