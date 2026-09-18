import json
import os
import tempfile

from .models import Case, Evidence, CustodyEntry, Settings, utcnow, new_id


class Store:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.images_dir = os.path.join(data_dir, "images")
        self.reports_dir = os.path.join(data_dir, "reports")
        for d in (data_dir, self.images_dir, self.reports_dir):
            os.makedirs(d, exist_ok=True)

        self.cases_path = os.path.join(data_dir, "cases.json")
        self.custody_path = os.path.join(data_dir, "custody.json")
        self.settings_path = os.path.join(data_dir, "settings.json")

        self.cases: list[Case] = []
        self.evidence: list[Evidence] = []
        self.custody: list[CustodyEntry] = []
        self.settings = Settings()

        self._load()

    # ---------- persistence helpers ----------

    @staticmethod
    def _atomic_write(path: str, data) -> None:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _load(self) -> None:
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, encoding="utf-8") as f:
                    self.settings = Settings.from_dict(json.load(f))
            except (OSError, json.JSONDecodeError):
                pass
        if os.path.exists(self.cases_path):
            try:
                with open(self.cases_path, encoding="utf-8") as f:
                    payload = json.load(f)
                self.cases = [Case.from_dict(c) for c in payload.get("cases", [])]
                self.evidence = [Evidence.from_dict(e) for e in payload.get("evidence", [])]
            except (OSError, json.JSONDecodeError):
                self.cases, self.evidence = [], []
        if os.path.exists(self.custody_path):
            try:
                with open(self.custody_path, encoding="utf-8") as f:
                    self.custody = [CustodyEntry.from_dict(c) for c in json.load(f)]
            except (OSError, json.JSONDecodeError):
                self.custody = []

    def save_cases(self) -> None:
        self._atomic_write(self.cases_path, {
            "cases": [c.to_dict() for c in self.cases],
            "evidence": [e.to_dict() for e in self.evidence],
        })

    def save_settings(self) -> None:
        self._atomic_write(self.settings_path, self.settings.to_dict())

    def save_custody(self) -> None:
        self._atomic_write(self.custody_path, [c.to_dict() for c in self.custody])

    # ---------- cases ----------

    def add_case(self, case: Case) -> None:
        self.cases.append(case)
        self.save_cases()

    def update_case(self, case: Case) -> None:
        case.touch()
        for i, c in enumerate(self.cases):
            if c.id == case.id:
                self.cases[i] = case
                break
        self.save_cases()

    def delete_case(self, case_id: str) -> None:
        self.cases = [c for c in self.cases if c.id != case_id]
        self.evidence = [e for e in self.evidence if e.case_id != case_id]
        self.save_cases()

    def get_case(self, case_id: str) -> Case | None:
        for c in self.cases:
            if c.id == case_id:
                return c
        return None

    # ---------- evidence ----------

    def add_evidence(self, ev: Evidence) -> None:
        self.evidence.append(ev)
        self.save_cases()

    def update_evidence(self, ev: Evidence) -> None:
        for i, e in enumerate(self.evidence):
            if e.id == ev.id:
                self.evidence[i] = ev
                break
        self.save_cases()

    def get_evidence_for_case(self, case_id: str) -> list[Evidence]:
        return [e for e in self.evidence if e.case_id == case_id]

    def get_evidence(self, ev_id: str) -> Evidence | None:
        for e in self.evidence:
            if e.id == ev_id:
                return e
        return None

    # ---------- custody chain ----------

    def append_custody(self, actor: str, role: str, action: str, detail: str, secret: str) -> CustodyEntry:
        prev = self.custody[-1] if self.custody else None
        prev_hmac = prev.hmac if prev else ("0" * 64)
        entry = CustodyEntry(
            seq=len(self.custody) + 1,
            timestamp=utcnow(),
            actor=actor or "",
            role=role or "",
            action=action,
            detail=detail,
            hmac="",
            prev_hmac=prev_hmac,
        )
        import hmac as hmac_mod
        import hashlib
        payload = "|".join([
            str(entry.seq), entry.timestamp, entry.actor, entry.role,
            entry.action, entry.detail, prev_hmac,
        ]).encode("utf-8")
        entry.hmac = hmac_mod.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        self.custody.append(entry)
        self.save_custody()
        return entry

    def verify_chain(self, secret: str) -> tuple[bool, list[str]]:
        import hmac as hmac_mod
        import hashlib
        problems: list[str] = []
        prev_hmac = "0" * 64
        ok = True
        for entry in self.custody:
            payload = "|".join([
                str(entry.seq), entry.timestamp, entry.actor, entry.role,
                entry.action, entry.detail, prev_hmac,
            ]).encode("utf-8")
            expected = hmac_mod.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
            if entry.hmac != expected:
                ok = False
                problems.append(f"Entry #{entry.seq} tampered (HMAC mismatch at {entry.timestamp}).")
            if entry.prev_hmac != prev_hmac:
                ok = False
                problems.append(f"Entry #{entry.seq} broken chain reference.")
            prev_hmac = entry.hmac
        return ok, problems