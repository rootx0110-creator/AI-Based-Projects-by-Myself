"""Playbook execution engine.

Walks a playbook graph step-by-step in a background worker thread, executing
integration calls against the bus, recording per-step results, and persisting
the run after every step mutation. Designed to be resilient: a single failed
step does not kill the run (marker: completed_with_errors) unless the step
declares abort_on_error.
"""

import re
import threading
import time
import uuid

from .integrations import IntegrationBus
from .playbook import resolve_templates
from .storage import utcnow

EXEC_STATUSES = ("queued", "running", "completed", "completed_with_errors", "failed", "cancelled")
STEP_STATUSES = ("pending", "running", "completed", "failed", "skipped")


def new_execution_id():
    return f"exec_{uuid.uuid4().hex[:12]}"


class ExecutionEngine:
    def __init__(self, store, playbook_service, incident_service):
        self.store = store
        self.pb = playbook_service
        self.incidents = incident_service
        self.bus = IntegrationBus(store)
        self._threads = {}

    # ------------------------------------------------------------------ run
    def start(self, incident, playbook_id, ioc_id=None):
        pb = self.pb.get(playbook_id)
        if not pb:
            return None, f"playbook {playbook_id} not found"
        incident["playbook_id"] = pb.id
        execution = self._new_execution(incident, pb, ioc_id)
        self.incidents.set_phase(incident["id"], "contained")
        t = threading.Thread(target=self._worker, args=(execution["id"],), daemon=True)
        self._threads[execution["id"]] = t
        t.start()
        return execution, None

    def cancel(self, execution_id):
        execution = self.get(execution_id)
        if not execution or execution["status"] not in ("queued", "running"):
            return False
        self._mark_status(execution_id, "cancelled")

        def cancel_step(coll):
            for ex in coll:
                if ex["id"] == execution_id:
                    for s in ex.get("steps", []):
                        if s["status"] == "pending":
                            s["status"] = "skipped"
                    return True, coll
            return False, coll
        self.store.mutate("executions", cancel_step)

        incident = self.incidents.get(execution["incident_id"])
        if incident:
            self.incidents.add_note(incident["id"],
                                    f"Playbook run {execution_id} cancelled by analyst.",
                                    by="analyst")
            if incident["phase"] == "contained":
                self.incidents.set_phase(incident["id"], "triage")
        return True

    # ------------------------------------------------------------------ get
    def get(self, execution_id):
        return self.store.find("executions", execution_id)

    def list(self):
        return sorted(self.store.get("executions"),
                      key=lambda e: e.get("created_at", ""), reverse=True)

    def list_for_incident(self, incident_id):
        return [e for e in self.store.get("executions") if e.get("incident_id") == incident_id]

    # ------------------------------------------------------------------ new
    def _new_execution(self, incident, pb, ioc_id):
        steps = []
        idx = 0
        for s in pb.steps:
            steps.append({
                "pos": idx,
                "id": f"step_{uuid.uuid4().hex[:8]}",
                "pb_step_id": s["id"],
                "kind": s["kind"],
                "label": s.get("label") or s.get("text", "")[:60],
                "action": s.get("action"),
                "depends_on": (s.get("on") if s["kind"] == "condition" else None),
                "status": "pending",
                "input": None,
                "output": None,
                "error": None,
                "latency_ms": 0,
                "started_at": None,
                "finished_at": None,
            })
            idx += 1

        execution = {
            "id": new_execution_id(),
            "incident_id": incident["id"],
            "ref_no": incident.get("ref_no"),
            "playbook_id": pb.id,
            "playbook_name": pb.name,
            "status": "queued",
            "current_pb_step": pb.first_step()["id"] if pb.first_step() else None,
            "ioc_id": ioc_id,
            "created_at": utcnow(),
            "started_at": None,
            "finished_at": None,
            "was_interrupted": False,
            "steps": steps,
            "notes": [
                {"ts": utcnow(), "by": "system",
                 "text": f"Run created against playbook '{pb.name}'."}
            ],
            "summary": None,
        }
        self.store.update("executions", self.store.get("executions") + [execution])
        return execution

    # ------------------------------------------------------------------ work
    def _worker(self, execution_id):
        execution = self.get(execution_id)
        if not execution:
            return
        self._mark_status(execution_id, "running", started_at=utcnow())
        execution = self.get(execution_id)
        work = [s for s in (execution.get("steps") or []) if s["status"] == "pending"]
        incident = self.incidents.get(execution["incident_id"])
        pb = self.pb.get(execution["playbook_id"])
        if not incident or not pb:
            self._mark_status(execution_id, "failed")
            return

        ioc = None
        if execution.get("ioc_id"):
            ioc = self.incidents.iocs_for(incident)  # fallback below
            ioc = next((x for x in ioc if x["id"] == execution["ioc_id"]), None)

        if ioc is None:
            cands = self.incidents.iocs_for(incident)
            ioc = cands[0] if cands else None

        context = {
            "incident": incident,
            "ioc": ioc or {},
            "execution": execution,
        }

        by_pos = {s["pb_step_id"]: s for s in work}
        index_of = {s["pb_step_id"]: i for i, s in enumerate(work)}
        step_refs = {s["id"]: s for s in pb.steps}

        pos = 0
        seen = set()
        terminal = False
        final_ok = True

        while pos < len(work) and not terminal:
            rs = work[pos]
            if rs["id"] in seen:
                # cycle guard
                break
            seen.add(rs["id"])
            self._set_step_status(execution_id, rs["id"], "running")
            rs = self.get_step(execution_id, rs["id"])
            if rs is None:
                break

            step_def = step_refs.get(rs["pb_step_id"]) or {}
            kind = rs["kind"]
            outcome = "ok"
            rs["started_at"] = utcnow()

            if kind == "title":
                rs["output"] = {"message": step_def.get("text", "")}

            elif kind == "task":
                rs["output"] = {
                    "assigned": step_def.get("assign", "Analyst"),
                    "instruction": step_def.get("text", ""),
                }

            elif kind == "delay":
                secs = float(step_def.get("seconds", 1) or 0)
                time.sleep(min(secs, 5))
                rs["output"] = {"waited_s": secs}

            elif kind == "integration":
                action = step_def.get("action")
                resolved_params = resolve_templates(step_def.get("params") or {}, context)
                rs["input"] = {"action": action, "params": resolved_params}
                retries = int(step_def.get("retry", 1) or 1)
                result = None
                fatal = False
                for attempt in range(max(retries, 1)):
                    result = self.bus.execute(action, resolved_params)
                    if result.get("ok") or attempt + 1 >= retries:
                        break
                rs["latency_ms"] = result.get("latency_ms", 0)
                if result.get("ok"):
                    rs["output"] = result["output"]
                    self._absorb_ioc_verdict(execution_id, rs, result, ioc)
                else:
                    rs["error"] = result.get("output", {}).get("error", "unknown")
                    rs["output"] = {"verdict": "failed", "error": rs["error"]}
                    outcome = "fail"
                    rs["status"] = "failed"
                    if step_def.get("abort_on_error"):
                        final_ok = False
                        fatal = True
                if fatal:
                    rs["status"] = "failed"
                    rs["finished_at"] = utcnow()
                    self._write_step(execution_id, rs)
                    terminal = True
                    continue

            elif kind == "condition":
                deps_id = rs.get("depends_on")
                prior = next((s for s in work if s.get("pb_step_id") == deps_id), None)
                prior_output = prior.get("output") or {} if prior else {}
                test = step_def.get("test") or {}
                m = self._evaluate(test, prior_output)
                rs["output"] = {"test": test, "matched": m,
                                "source": prior["pb_step_id"] if prior else None}
                rs["input"] = {"condition": test, "evaluated": m}
            else:
                rs["output"] = {"note": f"unknown kind {kind}"}

            if rs["status"] != "failed":
                rs["status"] = "completed"
            rs["finished_at"] = utcnow()
            self._write_step(execution_id, rs)

            # ---------------- navigation ----------------
            nxt = self._next_step(execution_id, rs, step_def, work, index_of, outcome)
            if nxt is None:
                terminal = True
            else:
                pos = nxt
            self._set_current(execution_id, step_def.get("id"))

        # ---------------- wrap up ----------------
        execution = self.get(execution_id)
        steps = execution.get("steps") or []
        failed = [s for s in steps if s["status"] == "failed"]
        # mark branch-skipped steps so logs read cleanly
        if any(s["status"] == "pending" for s in steps):

            def tidy(coll):
                for ex in coll:
                    if ex["id"] == execution_id:
                        for s in ex.get("steps", []):
                            if s["status"] == "pending":
                                s["status"] = "skipped"
                                s["finished_at"] = utcnow()
                                s["output"] = {"note": "branch not taken"}
                        return True, coll
                return False, coll

            self.store.mutate("executions", tidy)
        self._mark_status(execution_id,
                          "failed" if not final_ok else
                          ("completed_with_errors" if failed else "completed"),
                          finished_at=utcnow())
        self._finalize(execution_id, failed=bool(failed or not final_ok))

    # ------------------------------------------------------------------ nav
    def _evaluate(self, test, output):
        op = test.get("op")
        field = test.get("field")
        expected = test.get("value")
        def walk(d, path):
            cur = d
            for part in (path or "").split("."):
                if isinstance(cur, dict):
                    cur = cur.get(part)
                else:
                    return None
                if cur is None:
                    return None
            return cur
        actual = walk(output, field)
        try:
            if op == "eq":
                return str(actual).lower() == str(expected).lower()
            if op == "neq":
                return str(actual).lower() != str(expected).lower()
            if op == "contains":
                return expected and expected.lower() in str(actual or "").lower()
            if op == "regex":
                return bool(re.search(str(expected), str(actual or "")))
            if op == "exists":
                return actual not in (None, "", [], {})
            if op == "gt":
                try:
                    return float(actual) > float(expected)
                except (TypeError, ValueError):
                    return False
        except Exception:
            return False
        return False

    def _next_step(self, execution_id, rs, step_def, work, index_of, outcome):
        if step_def.get("goto"):
            return index_of.get(step_def["goto"])

        if step_def.get("kind") == "condition":
            matched = (rs.get("output") or {}).get("matched")
            target = step_def.get("then" if matched else "else")
            if target is None:
                return self._default_next(index_of, rs["pb_step_id"], work)
            if target == "end":
                return None
            return index_of.get(target)

        if step_def.get("kind") == "integration":
            for branch in (step_def.get("on") or []):
                key = branch.get("result") or branch.get("verdict")
                if key and self._branch_matches(key, rs, step_def):
                    if branch.get("next") == "end":
                        return None
                    return index_of.get(branch.get("next"))

        if step_def.get("next") == "end":
            return None
        if step_def.get("next"):
            return index_of.get(step_def["next"])
        return self._default_next(index_of, rs["pb_step_id"], work)

    def _default_next(self, index_of, current_id, work):
        idx = index_of.get(current_id)
        if idx is None:
            return None
        nxt = idx + 1
        return nxt if nxt < len(work) else None

    def _branch_matches(self, key, rs, step_def):
        out = rs.get("output") or {}
        v = out.get("verdict") or out.get("status") or ""
        return str(v).lower() == str(key).lower()

    # ------------------------------------------------------------------ absorb
    def _absorb_ioc_verdict(self, execution_id, rs, result, ioc):
        out = result.get("output") or {}
        verdict = out.get("verdict")
        if ioc and verdict and rs.get("action"):
            if rs["action"].startswith("ti.") or rs["action"] in ("sandbox.submit", "mail.trace"):
                self.incidents.set_ioc_verdict(ioc["id"], verdict, out.get("score"))

    # ------------------------------------------------------------------ io
    def get_step(self, execution_id, step_id):
        ex = self.get(execution_id)
        if not ex:
            return None
        for s in ex.get("steps", []):
            if s["id"] == step_id:
                return s
        return None

    def _write_step(self, execution_id, updated):
        def fn(coll):
            for ex in coll:
                if ex["id"] == execution_id:
                    for i, s in enumerate(ex.get("steps", [])):
                        if s["id"] == updated["id"]:
                            ex["steps"][i] = updated
                            return True, coll
            return False, coll
        self.store.mutate("executions", fn)

    def _set_step_status(self, execution_id, step_id, status):
        def fn(coll):
            for ex in coll:
                if ex["id"] == execution_id:
                    for s in ex.get("steps", []):
                        if s["id"] == step_id:
                            s["status"] = status
                            if status == "running":
                                s["started_at"] = utcnow()
                            if status in ("completed", "failed", "skipped"):
                                s["finished_at"] = utcnow()
                            return True, coll
            return False, coll
        self.store.mutate("executions", fn)

    def _set_current(self, execution_id, pb_step_id):
        def fn(coll):
            for ex in coll:
                if ex["id"] == execution_id:
                    ex["current_pb_step"] = pb_step_id
                    return True, coll
            return False, coll
        self.store.mutate("executions", fn)

    def _mark_status(self, execution_id, status, started_at=None, finished_at=None):
        def fn(coll):
            for ex in coll:
                if ex["id"] == execution_id:
                    ex["status"] = status
                    if started_at and not ex.get("started_at"):
                        ex["started_at"] = started_at
                    if finished_at:
                        ex["finished_at"] = finished_at
                    return True, coll
            return False, coll
        self.store.mutate("executions", fn)

    def _finalize(self, execution_id, failed=False):
        execution = self.get(execution_id)
        if not execution:
            return
        incident = self.incidents.get(execution["incident_id"])
        if not incident:
            return
        steps = execution.get("steps") or []
        ok_steps = [s for s in steps if s["status"] == "completed"]
        if failed:
            self.incidents.add_note(
                incident["id"],
                f"Run {execution_id} finished with errors ({len(steps) - len(ok_steps)} steps failed).",
                by="engine")
            return
        self.incidents.add_note(incident["id"],
                                f"Playbook '{execution['playbook_name']}' completed. "
                                "Recommended next phase: eradication.", by="engine")
        if incident["phase"] == "contained":
            self.incidents.set_phase(incident["id"], "eradicated")