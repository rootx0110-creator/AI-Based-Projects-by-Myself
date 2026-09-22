'use strict';
/**
 * detectors.js — rule catalogue for insecure coding patterns.
 * Each rule: declarative object. Adding a rule = adding one object here.
 * Ids are SCREAMING_SNAKE. Severity: CRITICAL | HIGH | MEDIUM | LOW.
 */

const RULES = [
  // ─── INJECTION ───────────────────────────────────────────────────────
  {
    id: 'SQLI_CONCAT',
    title: 'SQL query built with string concatenation',
    severity: 'CRITICAL', cwe: 'CWE-89', owasp: 'A03:2021 – Injection',
    languages: ['js', 'ts', 'py', 'php', 'java', 'cs'],
    pattern: /(?:query|execute|exec)\s*\(\s*["'`][^"'`]*(?:SELECT|INSERT|UPDATE|DELETE|DROP)[^"'`]*["'`]\s*\+\s*[^)]+\)/i,
    summary: 'User-controlled data is concatenated into a SQL statement, enabling SQL injection.',
  },
  {
    id: 'SQLI_TEMPLATE',
    title: 'SQL query built with template literal / f-string interpolation',
    severity: 'CRITICAL', cwe: 'CWE-89', owasp: 'A03:2021 – Injection',
    languages: ['js', 'ts', 'py', 'php'],
    pattern: /[`"'](?:SELECT|INSERT|UPDATE|DELETE|DROP)[^`"'$%]*[`$]\{[^}]+\}[^`"']*[`"']/i,
    summary: 'Interpolated values inside SQL strings are a classic injection vector.',
  },
  {
    id: 'SQLI_FSTRING',
    title: 'SQL query built with Python f-string or .format()',
    severity: 'CRITICAL', cwe: 'CWE-89', owasp: 'A03:2021 – Injection',
    languages: ['py'],
    pattern: /(?:execute|executemany)\s*\(\s*f["'][^"']*(?:SELECT|INSERT|UPDATE|DELETE|DROP)[^"']*["']/i,
    summary: 'f-strings in SQL interpolate unescaped user data directly into the statement.',
  },
  {
    id: 'CMDI_SHELL',
    title: 'Shell command built from string concatenation',
    severity: 'CRITICAL', cwe: 'CWE-78', owasp: 'A03:2021 – Injection',
    languages: ['js', 'ts'],
    pattern: /(?:exec|execSync|spawn|spawnSync)\s*\(\s*[^,)]*\+/,
    summary: 'Concatenating input into an OS command allows command injection.',
  },
  {
    id: 'CMDI_SHELL_TRUE',
    title: 'Command injection risk (shell=True / os.system with interpolation)',
    severity: 'CRITICAL', cwe: 'CWE-78', owasp: 'A03:2021 – Injection',
    languages: ['py'],
    pattern: /(?:shell\s*=\s*True|os\.system\s*\()|subprocess\.(?:call|run|Popen)\s*\([^)]*%/,
    summary: 'Running shell commands with interpolated input gives attackers a shell.',
  },
  {
    id: 'EVAL_USE',
    title: 'Use of eval() on potentially untrusted data',
    severity: 'CRITICAL', cwe: 'CWE-95', owasp: 'A03:2021 – Injection',
    languages: ['js', 'ts', 'py', 'php'],
    pattern: /\b(?:eval\s*\(|exec\s*\()/,
    summary: 'eval/exec executes arbitrary code — if input reaches it, it is game over.',
  },
  {
    id: 'XSS_INNERHTML',
    title: 'Untrusted content assigned to innerHTML / document.write',
    severity: 'HIGH', cwe: 'CWE-79', owasp: 'A03:2021 – Injection',
    languages: ['js', 'ts'],
    pattern: /(?:innerHTML\s*=|document\.write\s*\(|outerHTML\s*=)/,
    summary: 'Direct DOM sinks render attacker HTML/JS — classic XSS.',
  },
  {
    id: 'DESERIALIZE_UNSAFE',
    title: 'Unsafe deserialization (pickle / yaml.load / unserialize)',
    severity: 'CRITICAL', cwe: 'CWE-502', owasp: 'A08:2021 – Software and Data Integrity',
    languages: ['py', 'php', 'java'],
    pattern: /\b(?:pickle\.loads?\s*\(|yaml\.load\s*\((?![^)]*Loader)|unserialize\s*\(|ObjectInputStream)/,
    summary: 'Deserializing untrusted data can execute arbitrary code via gadget chains.',
  },

  // ─── PHP-SPECIFIC ────────────────────────────────────────────────────
  {
    id: 'SQLI_PHP_CONCAT',
    title: 'PHP SQL query concatenated with superglobal input',
    severity: 'CRITICAL', cwe: 'CWE-89', owasp: 'A03:2021 – Injection',
    languages: ['php'],
    pattern: /(?:mysql_query|mysqli_query|->query)\s*\(\s*["'][^"']*(?:SELECT|INSERT|UPDATE|DELETE)[^"']*["']\s*\.\s*\$_(GET|POST|REQUEST)/i,
    summary: 'Dot-concatenated $_GET/$_POST data is executed as SQL.',
  },
  {
    id: 'CMDI_PHP',
    title: 'PHP shell function fed request input',
    severity: 'CRITICAL', cwe: 'CWE-78', owasp: 'A03:2021 – Injection',
    languages: ['php'],
    pattern: /\b(?:exec|shell_exec|system|passthru|popen)\s*\([^)]*\$_(GET|POST|REQUEST)/,
    summary: 'Shell execution functions receive unfiltered request data.',
  },
  {
    id: 'PHP_LFI',
    title: 'Local file inclusion from request parameter',
    severity: 'CRITICAL', cwe: 'CWE-98', owasp: 'A03:2021 – Injection',
    languages: ['php'],
    pattern: /\b(?:include|require)(?:_once)?\s*\(?\s*\$_(GET|POST|REQUEST)/,
    summary: 'include/require over $_GET allows remote code execution via wrappers (php://input, http://).',
  },

  // ─── SECRETS ─────────────────────────────────────────────────────────
  {
    id: 'HARDCODED_SECRET',
    title: 'Hardcoded secret / API key assignment',
    severity: 'CRITICAL', cwe: 'CWE-798', owasp: 'A07:2021 – Identification and Authentication',
    languages: ['*'],
    pattern: /(?<![A-Za-z])(?:password|passwd|secret|api_?key|apikey|token|access_?key|auth_?token)[\w-]*\s*[:=]\s*["'][^"'\s]{8,}["']/i,
    summary: 'Secrets in source control leak to everyone with repo access and its history.',
  },
  {
    id: 'HARDCODED_AWS_KEY',
    title: 'Hardcoded AWS access key id',
    severity: 'CRITICAL', cwe: 'CWE-798', owasp: 'A07:2021 – Identification and Authentication',
    languages: ['*'],
    pattern: /AKIA[0-9A-Z]{16}/,
    summary: 'AWS key ids in code allow account enumeration and pair with leaked secret keys.',
  },
  {
    id: 'PRIVATE_KEY_BLOCK',
    title: 'Private key material committed to source',
    severity: 'CRITICAL', cwe: 'CWE-321', owasp: 'A02:2021 – Cryptographic Failures',
    languages: ['*'],
    pattern: /-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----/,
    summary: 'Anyone with repo read access obtains your private key.',
  },
  {
    id: 'DB_CONN_CREDENTIALS',
    title: 'Database connection string with embedded credentials',
    severity: 'HIGH', cwe: 'CWE-798', owasp: 'A07:2021 – Identification and Authentication',
    languages: ['*'],
    pattern: /(?:mysql|postgres|postgresql|mongodb(?:\+srv)?|redis|amqp):\/\/[^\/\s"'`]*:[^\/\s"'`@]+@/,
    summary: 'Credentials embedded in connection URIs end up in logs, code review, and git history.',
  },

  // ─── CRYPTO ──────────────────────────────────────────────────────────
  {
    id: 'WEAK_HASH',
    title: 'Weak hash algorithm (MD5 / SHA1)',
    severity: 'HIGH', cwe: 'CWE-327', owasp: 'A02:2021 – Cryptographic Failures',
    languages: ['js', 'ts', 'py', 'java', 'cs', 'php', 'go'],
    pattern: /\b(?:md5|sha1|MD5|SHA1)\s*\(|createHash\s*\(\s*["'](md5|sha1)["']/,
    summary: 'MD5/SHA1 are broken for security purposes; use SHA-256+ or bcrypt/argon2.',
  },
  {
    id: 'INSECURE_RANDOM',
    title: 'Math.random / random module used for security decisions',
    severity: 'MEDIUM', cwe: 'CWE-338', owasp: 'A02:2021 – Cryptographic Failures',
    languages: ['js', 'ts', 'py', 'java'],
    pattern: /\b(?:Math\.random\s*\(\s*\)|\brandom\.(?:random|randint|choice)\s*\()/,
    summary: 'PRNG output is predictable — tokens, ids, and OTPs need CSPRNG (crypto, secrets).',
  },
  {
    id: 'WEAK_CIPHER_MODE',
    title: 'Weak cipher mode (ECB) or DES/RC4',
    severity: 'HIGH', cwe: 'CWE-327', owasp: 'A02:2021 – Cryptographic Failures',
    languages: ['js', 'ts', 'py', 'java', 'cs'],
    pattern: /["'](?:aes-[0-9]+-ecb|des|rc4|blowfish)["']/i,
    summary: 'ECB leaks patterns; DES/RC4 are cryptographically broken.',
  },
  {
    id: 'JWT_NONE_ALG',
    title: 'JWT with none / weak algorithm',
    severity: 'HIGH', cwe: 'CWE-347', owasp: 'A02:2021 – Cryptographic Failures',
    languages: ['js', 'ts', 'py', 'java'],
    pattern: /algorithm[s]?\s*:\s*\[?\s*["'](none|HS1|RS1)["']/i,
    summary: '"none" alg lets anyone forge tokens; legacy algs enable downgrade attacks.',
  },

  // ─── NETWORK / SSRF / REDIRECT ───────────────────────────────────────
  {
    id: 'SSRF_URL_INPUT',
    title: 'Server-side request built from user-controlled URL',
    severity: 'HIGH', cwe: 'CWE-918', owasp: 'A10:2021 – SSRF',
    languages: ['js', 'ts', 'py', 'php', 'java'],
    pattern: /(?:fetch|axios(?:\.\w+)?|requests\.(?:get|post)|urlopen|http\.Get)\s*\(\s*(?:req\.(?:body|query|params)|request\.|user_?input|data\[)/i,
    summary: 'Requests to attacker-chosen URLs reach internal networks (SSRF) and cloud metadata.',
  },
  {
    id: 'OPEN_REDIRECT',
    title: 'Open redirect from request parameter',
    severity: 'HIGH', cwe: 'CWE-601', owasp: 'A01:2021 – Broken Access Control',
    languages: ['js', 'ts', 'py', 'php', 'java'],
    pattern: /(?:redirect|res\.redirect|sendRedirect|Redirect\(responses?)\s*\(\s*(?:req\.(?:query|body|params)|request\.GET)/i,
    summary: 'Unvalidated redirect targets enable phishing that appears to come from your domain.',
  },
  {
    id: 'TLS_VERIFY_OFF',
    title: 'TLS certificate verification disabled',
    severity: 'HIGH', cwe: 'CWE-295', owasp: 'A02:2021 – Cryptographic Failures',
    languages: ['js', 'ts', 'py', 'go', 'cs', 'php'],
    pattern: /(?:rejectUnauthorized\s*:\s*false|verify\s*=\s*False|InsecureSkipVerify\s*:\s*true|CURLOPT_SSL_VERIFYPEER\s*,\s*false)/,
    summary: 'Disabling cert verification turns HTTPS into plaintext against active attackers.',
  },
  {
    id: 'XXE_PARSER',
    title: 'XML parser with external entities enabled (XXE)',
    severity: 'CRITICAL', cwe: 'CWE-611', owasp: 'A05:2021 – Security Misconfiguration',
    languages: ['py', 'java', 'php', 'cs'],
    pattern: /(?:etree\.fromstring|xml.etree\.ElementTree\.parse|DocumentBuilderFactory\.newInstance|simplexml_load_string|XmlReader\.Create)/,
    summary: 'Without entity protections, XML parsers can read files / SSRF via DOCTYPE entities.',
  },

  // ─── FILES / PATHS ───────────────────────────────────────────────────
  {
    id: 'PATH_TRAVERSAL_JOIN',
    title: 'File path built from user input without sanitization',
    severity: 'HIGH', cwe: 'CWE-22', owasp: 'A01:2021 – Broken Access Control',
    languages: ['js', 'ts', 'py', 'php', 'java', 'go'],
    pattern: /(?:readFile|createReadStream|fs\.read|open\s*\(|sendFile|res\.download|File\.ReadAllText)\s*\(\s*(?:req\.|request\.|path\.join\s*\([^)]*req|os\.path\.join\s*\([^)]*request)/i,
    summary: '../ in user input escapes the intended directory — read or overwrite any file.',
  },

  // ─── AUTH / ACCESS ───────────────────────────────────────────────────
  {
    id: 'WILDCARD_CORS',
    title: 'CORS wildcard with credentials',
    severity: 'HIGH', cwe: 'CWE-942', owasp: 'A05:2021 – Security Misconfiguration',
    languages: ['js', 'ts', 'py', 'cs', 'java'],
    pattern: /(?:origin\s*:\s*["']\*["']|Access-Control-Allow-Origin["']?\s*[,:=]\s*["']\*["'])/i,
    summary: 'With credentials, a wildcard origin lets any site read authenticated responses.',
  },
  {
    id: 'PLAINTEXT_COMPARE',
    title: 'Non-constant-time comparison for secrets',
    severity: 'MEDIUM', cwe: 'CWE-208', owasp: 'A02:2021 – Cryptographic Failures',
    languages: ['js', 'ts', 'py'],
    pattern: /(?:===?\s*["'][^"']*(?:token|secret|sig)|password\s*===?\s*\w+|hash\.digest\s*\(\s*\)\s*===)/i,
    summary: '==/=== on secrets leaks timing information; use timingSafeEqual / compare_digest.',
  },
  {
    id: 'NO_AUTH_MIDDLEWARE_HINT',
    title: 'Sensitive route without visible auth middleware',
    severity: 'MEDIUM', cwe: 'CWE-306', owasp: 'A01:2021 – Broken Access Control',
    languages: ['js', 'ts', 'py'],
    pattern: /app\.(?:get|post|put|delete)\s*\(\s*["'][^"']*(?:admin|internal|debug|users?|export|dump)[^"']*["']\s*,\s*(?:\(|(?:async\s*)?\(\s*req)/i,
    summary: 'Routes matching sensitive names appear to lack an authentication guard.',
  },
  {
    id: 'DEBUG_MODE_ON',
    title: 'Debug mode enabled in production config',
    severity: 'MEDIUM', cwe: 'CWE-489', owasp: 'A05:2021 – Security Misconfiguration',
    languages: ['py', 'js', 'ts', 'php', 'cs'],
    pattern: /(?:DEBUG\s*=\s*True|debug\s*:\s*true|APP_DEBUG\s*=\s*true|app\.run\(.*debug\s*=\s*True)/,
    summary: 'Debug endpoints and stack traces leak source, paths, and settings.',
  },

  // ─── CLIENT / CONFIG ─────────────────────────────────────────────────
  {
    id: 'DANGEROUS_DOM_SINK',
    title: 'Dangerous DOM API sink (eval-like in browser)',
    severity: 'HIGH', cwe: 'CWE-79', owasp: 'A03:2021 – Injection',
    languages: ['js', 'ts'],
    pattern: /(?:setTimeout\s*\(\s*["']|setInterval\s*\(\s*["']|new\s+Function\s*\()/,
    summary: 'String-arg timers / Function constructor execute data as code — same as eval.',
  },
  {
    id: 'POSTMESSAGE_WILDCARD',
    title: 'postMessage with "*" target origin',
    severity: 'MEDIUM', cwe: 'CWE-79', owasp: 'A05:2021 – Security Misconfiguration',
    languages: ['js', 'ts'],
    pattern: /postMessage\s*\([^,]+,\s*["']\*["']/,
    summary: 'Any window receives this message, including hostile embedders.',
  },
  {
    id: 'COOKIES_NO_HTTPONLY',
    title: 'Cookie set without httpOnly/secure flags',
    severity: 'MEDIUM', cwe: 'CWE-1004', owasp: 'A05:2021 – Security Misconfiguration',
    languages: ['js', 'ts', 'py', 'php'],
    pattern: /Set-Cookie(?![^;\n]*(?:HttpOnly|httponly))/,
    summary: 'Without HttpOnly, XSS steals session cookies trivially.',
  },
  {
    id: 'GIT_IN_URL',
    title: 'Credential-bearing git/URL token in code',
    severity: 'HIGH', cwe: 'CWE-798', owasp: 'A07:2021 – Identification and Authentication',
    languages: ['*'],
    pattern: /(?:github|gitlab)\.com[^\s"']*x-access-token|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}/,
    summary: 'Token literals (ghp_…, xox…) grant immediate repo/workspace access.',
  },
  {
    id: 'ENV_FILE_COMMITTED',
    title: 'Secrets defined in tracked env-style file',
    severity: 'HIGH', cwe: 'CWE-798', owasp: 'A05:2021 – Security Misconfiguration',
    languages: ['env'],
    pattern: /^\s*[A-Z_]*(?:SECRET|PASSWORD|TOKEN|API_KEY|AWS_SECRET)[A-Z_0-9]*\s*=\s*\S{8,}/m,
    summary: '.env files with real values must never be committed; rotate and use a vault.',
  },
  {
    id: 'INSECURE_DESCERIALIZE_JS',
    title: 'Node child_process with shell interpolation via template',
    severity: 'CRITICAL', cwe: 'CWE-78', owasp: 'A03:2021 – Injection',
    languages: ['js', 'ts'],
    pattern: /(?:exec|execSync)\s*\(\s*`[^`]*\$\{/,
    summary: 'Template-interpolated shell commands run arbitrary injected commands.',
  },
  {
    id: 'VERBOSE_ERROR_EXPOSE',
    title: 'Raw error/stack returned to client',
    severity: 'LOW', cwe: 'CWE-209', owasp: 'A05:2021 – Security Misconfiguration',
    languages: ['js', 'ts', 'py'],
    pattern: /(?:res\.(?:json|send)\s*\(\s*(?:err(?:or)?\)|e\)|ex\))|return\s+(?:str|repr)\s*\(\s*e\s*\))/,
    summary: 'Stack traces disclose internals: paths, query text, dependency versions.',
  },
  {
    id: 'SECURITY_TODO',
    title: 'Unresolved security TODO/FIXME/HACK',
    severity: 'LOW', cwe: 'CWE-1104', owasp: 'N/A',
    languages: ['*'],
    pattern: /(?:\/\/|#|\/\*)\s*(?:TODO|FIXME|HACK|XXX)\b[^\n]*(?:secur|auth|password|token|todo:?\s*implement)/i,
    summary: 'Deferred security work is an attack-surface inventory — track and close it.',
  },
];

module.exports = { RULES };
