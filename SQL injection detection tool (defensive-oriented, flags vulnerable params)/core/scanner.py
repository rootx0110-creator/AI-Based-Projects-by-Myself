"""Live scanning engine.

Probes a target host with benign, canonical SQL injection test payloads and
observes behavioural deltas (error text, boolean response changes, timing).

DEFENSIVE TOOL GUARDRAILS
-------------------------
* Requires explicit user consent per scan (UI checkbox) and printed banner.
* Only ever sends a small, bounded number of requests per parameter.
* All probing is opt-in and off by default; offline log analysis needs none.
* Localhost targets are allowed only for lab/testing use, never shunned, but
  clearly surfaced in the report when encountered.
"""

import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from . import payloads as P


class ScannerError(Exception):
    pass


class LiveScanner:
    """Bounded, configurable live probber over urllib."""

    BOOLEAN_PROBES = (
        ("boolean_eq", "' AND '1'='1", "' AND '1'='2"),
        ("boolean_num", " 1 AND 1=1", " 1 AND 1=2"),
    )
    ERROR_PROBES = (
        "'",
        "' AND extractvalue(1,concat(0x7e,(select version())))#",
        "' AND 1=CONVERT(int,(SELECT @@version))--",
    )
    TIME_PROBES = (
        ("sleep", "' AND SLEEP(2)-- -"),
        ("sleep", "1' AND SLEEP(2)#"),
        ("pg_sleep", "' AND pg_sleep(2)--"),
        ("waitfor", "1'; WAITFOR DELAY '00:00:02'-- -"),
    )

    def __init__(self, timeout=8.0, post_delay_ms=0, consent=False,
                 max_probes_per_target=200, verify_ssl=False):
        if not consent:
            raise ScannerError("Live probing requires explicit consent.")
        self.timeout = timeout
        self.post_delay = post_delay_ms / 1000.0
        self.consent = consent
        self.max_probes = max_probes_per_target
        self.verify_ssl = verify_ssl
        self.last_error = None
        self._ctx = ssl.create_default_context() if verify_ssl else ssl._create_unverified_context()
        self._requests_made = 0

    # ------------------------------------------------------------------ I/O
    def _open(self, url, method="GET", data=None, headers=None):
        headers = headers or {}
        headers.setdefault("User-Agent",
                           "SQLInspect/1.0 (defensive scanner; safe probes)")
        if data is not None:
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
            body = resp.read(60_000)
        return resp.status, body, (time.perf_counter() - t0) * 1000.0

    def _safe_open(self, *a, **kw):
        self._requests_made += 1
        if self._requests_made > self.max_probes:
            raise ScannerError("Probe budget exhausted for target.")
        try:
            return self._open(*a, **kw)
        except urllib.error.HTTPError as e:
            body = e.read(20_000)
            return e.code, body, 0.0
        except (urllib.error.URLError, OSError, ConnectionError, TimeoutError) as e:
            self.last_error = str(e)
            return None, b"", 0.0
        finally:
            if self.post_delay:
                time.sleep(self.post_delay)

    # ------------------------------------------------------------ building
    def _request_for(self, target, param, value, method="GET"):
        """Inject a probe value into the request, preserving all other fields."""
        params = {k: (vs if isinstance(vs, list) else [vs])
                  for k, vs in dict(target.get("params", {})).items()}
        params[param] = [value]

        if method == "POST":
            form = []
            for k, vs in params.items():
                for v in vs:
                    form.append("%s=%s" % (urllib.parse.quote_plus(k, safe=""),
                                           urllib.parse.quote_plus(str(v), safe="")))
            return target["url"], "POST", "&".join(form).encode()
        else:
            qs = []
            for k, vs in params.items():
                for v in vs:
                    qs.append("%s=%s" % (urllib.parse.quote_plus(k, safe=""),
                                         urllib.parse.quote_plus(str(v), safe="")))
            url = urllib.parse.urlsplit(target["url"])
            new_qs = "&".join(qs)
            rebuilt = urllib.parse.urlunsplit((url.scheme, url.netloc, url.path,
                                               new_qs, url.fragment))
            return rebuilt, "GET", None

    # ------------------------------------------------------------ probing
    def probe_parameter(self, target, param, original_value):
        """Return a list of confirmed techniques discovered for a parameter.

        Each item: (technique_key, evidence, confidence)
        """
        found = []

        def _used(value, method="GET"):
            try:
                url, m, data = self._request_for(target, param, value, method)
                return self._safe_open(url, method=m, data=data)
            except ScannerError:
                raise
            except Exception as e:
                self.last_error = str(e)
                return None, b"", 0.0

        baseline = _used(original_value)
        if baseline[0] is None:
            return [("unreachable", "request to %s failed: %s"
                     % (target.get("host", "?"), self.last_error or "timeout"), 0.0)]

        b_status, b_body, _b_lat = baseline
        b_signs = self._error_signatures(b_body)

        # --- boolean-blind -------------------------------------------------
        for key, probe_true, probe_false in self.BOOLEAN_PROBES:
            t = _used(probe_true)
            f = _used(probe_false)
            if t[0] is None or f[0] is None:
                continue
            if self._boolean_delta(b_body, t[1], f[1], b_status, t[0], f[0]):
                found.append(("boolean_blind",
                              "consistent response delta for '%s'/%s" %
                              (probe_true, key), 0.9))

        # --- error-based -----------------------------------------------------
        for probe in self.ERROR_PROBES:
            s, body, _lat = _used(probe)
            if s is None:
                continue
            signs = self._error_signatures(body)
            new = [x for x in signs if x not in b_signs]
            if new:
                found.append(("error_signature",
                              "DBMS error echoed after %r: %s" % (probe, new[0][0]),
                              0.95))
                break

        # --- time-based -------------------------------------------------------
        for key, probe in self.TIME_PROBES:
            _s, _b, lat = _used(probe)
            if lat >= 1500:
                found.append(("time_based",
                              "latency %.0fms with %s probe (%s)" % (lat, probe, key),
                              0.92))
                break

        # --- union / generic behaviour ----------------------------------------
        s, body, _lat = _used("1' UNION SELECT NULL-- -")
        if s is not None and self._boolean_delta(b_body, body, b_body, b_status, s, b_status,
                                                 tolerant=True):
            found.append(("signature", "behavioural delta on UNION probe", 0.6))

        return found

    # ------------------------------------------------------------ helpers
    @staticmethod
    def _boolean_delta(base_body, a_body, b_body, base_status, a_status, b_status,
                       tolerant=False):
        la, lb, lbase = len(a_body), len(b_body), len(base_body)
        if a_status != b_status:
            return True
        if tolerant:
            return la != lb or abs(lbase - la) > 40
        return (la != lb) and abs(la - lb) >= 15

    @staticmethod
    def _error_signatures(body):
        text = body.decode("utf-8", "replace")
        hits = []
        for dbms in ("mysql", "mssql", "oracle", "postgres", "sqlite", "java", "generic"):
            for sig in P.ERROR_SIGNATURES[dbms]:
                m = re.search(sig, text, re.I)
                if m:
                    hits.append((m.group(0)[:120], dbms))
        return hits[:4]


def classify_time_dbms(probe):
    if "sleep(" in probe:
        return "mysql"
    if "pg_sleep" in probe:
        return "postgres"
    if "waitfor" in probe:
        return "mssql"
    return "unknown"