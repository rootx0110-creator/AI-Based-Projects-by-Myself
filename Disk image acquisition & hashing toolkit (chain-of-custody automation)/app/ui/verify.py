import os
import time
from tkinter import filedialog

import customtkinter as ctk

from ..core.hasher import hash_file, CancelError
from ..core.models import format_bytes
from .base import BaseView
from .theme import (PANEL2, PANEL, BORDER, ACCENT, ACCENT2, GOOD, BAD, MUTED,
                    TEXT, font, ACCENT_BTN, WARN)


class VerifyView(BaseView):
    key = "verify"
    title = "Verification"
    subtitle = "Confirm acquired images still match their recorded integrity hashes"

    def __init__(self, master, app):
        super().__init__(master, app)
        self._busy = False
        body = self.body
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(3, weight=1)

        card = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=12, border_width=1,
                            border_color=BORDER)
        card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Target", font=font(13, 'bold'), text_color=ACCENT).grid(
            row=0, column=0, sticky="w", padx=16, pady=12)
        self.combo = ctk.CTkOptionMenu(card, values=["Registered evidence…"], width=420,
                                       fg_color=PANEL2, button_color=ACCENT_BTN,
                                       button_hover_color="#1b7180", text_color=TEXT,
                                       font=font(12), command=self._combo_change)
        self.combo.grid(row=0, column=1, sticky="w")
        self.browse_btn = ctk.CTkButton(card, text="Browse image…", font=font(12),
                                        fg_color="transparent", border_width=1,
                                        border_color=BORDER, text_color=ACCENT2, height=30,
                                        command=self._browse)
        self.browse_btn.grid(row=0, column=2, sticky="e", padx=16)

        self.info_card = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=12,
                                      border_width=1, border_color=BORDER)
        self.info_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.info_card.grid_columnconfigure(0, weight=1)
        self.info_text = ctk.CTkLabel(self.info_card, text="Select registered evidence or browse an image file.",
                                      font=font(12.5), text_color=MUTED, anchor="w",
                                      justify="left")
        self.info_text.grid(row=0, column=0, sticky="w", padx=16, pady=12)

        ctl_card = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=12, border_width=1,
                                border_color=BORDER)
        ctl_card.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        ctl_card.grid_columnconfigure(1, weight=1)
        self.start_btn = ctk.CTkButton(ctl_card, text="✓  Verify Integrity", font=font(14, "bold"),
                                       fg_color=ACCENT_BTN, hover_color="#1b7180", height=38,
                                       width=190, command=self._start)
        self.start_btn.grid(row=0, column=0, padx=16, pady=12, sticky="w")
        self.prog = ctk.CTkProgressBar(ctl_card, fg_color=PANEL2, progress_color=ACCENT,
                                       height=10)
        self.prog.set(0)
        self.prog.grid(row=0, column=1, sticky="ew", padx=16, pady=12)
        self.status = ctk.CTkLabel(ctl_card, text="Idle", font=font(12), text_color=MUTED)
        self.status.grid(row=0, column=2, padx=16, pady=12, sticky="e")

        self.res_card = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=12,
                                     border_width=1, border_color=BORDER)
        self.res_card.grid(row=3, column=0, sticky="nsew")
        self.res_card.grid_columnconfigure(0, weight=1)
        self.res_card.grid_rowconfigure(1, weight=1)
        self.res_head = ctk.CTkLabel(self.res_card, text="Result", font=font(14, "bold"),
                                     text_color=TEXT, anchor="w")
        self.res_head.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))
        self.res_text = ctk.CTkTextbox(self.res_card, fg_color="#0e141d", border_color=BORDER,
                                       border_width=1, corner_radius=8, font=font(13),
                                       text_color="#d7e2ee", wrap="word")
        self.res_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.res_text.configure(state="disabled")

        self._selected_evidence = None
        self._browsed_path = None

    def refresh(self):
        case = self.app.store.get_case(self.app.active_case_id)
        evs = self.app.store.get_evidence_for_case(case.id) if case else []
        labels = [self._ev_label(e) for e in evs]
        if not labels:
            labels = ["Registered evidence…"]
        self.combo.configure(values=labels)
        cur = self.combo.get()
        if self._selected_evidence and self._selected_evidence.item_label in labels:
            pass
        elif labels and cur not in labels:
            self.combo.set(labels[0])
            self._combo_change(labels[0])

    def _ev_label(self, e):
        return f"{e.item_label}  [{format_bytes(e.size_bytes)}]"

    def _find_evidence_by_label(self, label):
        for e in self.app.store.evidence:
            if self._ev_label(e) == label:
                return e
        return None

    def _combo_change(self, value):
        if value == "Registered evidence…":
            self._selected_evidence = None
            self.info_text.configure(text="Select registered evidence or browse an image file.")
            return
        ev = self._find_evidence_by_label(value)
        if not ev:
            return
        self._selected_evidence = ev
        self._browsed_path = None
        self.info_text.configure(
            text=f"Evidence: {ev.item_label}\n"
                 f"Image: {ev.target_image or '—'}\n"
                 f"Source: {ev.source or '—'}  ·  Acquired {ev.acquired_at[:19].replace('T', ' ')}  by  {ev.acquired_by or '—'}\n"
                 f"Recorded SHA-256: {(ev.hashes.get('sha256') or '—')}",
            text_color=TEXT)

    def _browse(self):
        p = filedialog.askopenfilename(title="Select image to verify",
                                       filetypes=[("Images", "*.img *.dd *.raw *.zip"), ("All", "*.*")])
        if not p:
            return
        self._selected_evidence = None
        self._browsed_path = p
        self.combo.set("Registered evidence…")
        self.info_text.configure(text=f"Standalone image file:\n{p}\n(no recorded hashes — verifying against file itself)",
                                 text_color=TEXT)

    def _start(self):
        if self._busy:
            return
        ev = self._selected_evidence
        path = self._browsed_path
        if not path:
            path = ev.target_image if ev else None
            expected = dict(ev.hashes) if ev else {}
        else:
            expected = {}
        if not path or not os.path.isfile(path):
            self.app.notify("Select a valid evidence image first.", BAD)
            return
        self._task_path, self._task_expected, self._task_ev = path, expected, ev
        self._busy = True
        self.start_btn.configure(state="disabled")
        self.prog.set(0)
        self.status.configure(text="Hashing…", text_color=ACCENT2)
        self._write_result("Computing integrity hashes — do not power off.\n")
        self._task_id = f"ver_{int(time.time())}"
        self.app.run_task(self._task_id, self._worker)

    def _worker(self, cancel):
        def prog(done, total):
            self.app.emit_progress("verify", self._task_id,
                                   done / total if total else 0.0,
                                   f"{format_bytes(done)} of {format_bytes(total or 0)}")
        hashes, size = hash_file(self._task_path, progress=prog, cancel=cancel)
        return hashes, size

    def on_progress(self, task_id, value, text):
        if task_id != getattr(self, "_task_id", ""):
            return
        self.prog.set(value or 0)
        self.status.configure(text=text, text_color=ACCENT2)

    def on_task_done(self, task_id, result, error):
        if task_id != getattr(self, "_task_id", ""):
            return
        self._busy = False
        self.start_btn.configure(state="normal")
        self.app.cancel_task(task_id)
        if error:
            self.prog.set(0)
            self.status.configure(text="Failed", text_color=BAD)
            self._write_result(f"ERROR: {error}\n")
            self.app.notify("Verification failed.", BAD)
            return
        hashes, size = result
        self.prog.set(1)
        expected = self._task_expected
        ev = self._task_ev
        lines = [f"Image: {self._task_path}\nSize: {format_bytes(size)}", "=" * 64]
        all_ok = bool(expected)
        for alg in ("md5", "sha1", "sha256"):
            actual = hashes.get(alg, "")
            if not actual:
                continue
            if expected.get(alg):
                match = actual.lower() == expected[alg].lower()
                all_ok = all_ok and match
                tag = "MATCH  ✔" if match else "NO-MATCH  ✘"
                color = GOOD if match else BAD
            else:
                tag, color, match = "(no recorded ref)", ACCENT2, True
            lines.append(f"{'MD5':7} {actual}    [{tag}]")
        verdict = "VERIFIED — image integrity confirmed" if all_ok else (
            "NOT VERIFIED — hashes differ from recorded values")
        self.status.configure(text="Verified" if all_ok else "Mismatch",
                              text_color=GOOD if all_ok else BAD)
        self.res_head.configure(text="Result — " + verdict,
                                text_color=GOOD if all_ok else BAD)
        self._write_result("\n".join(lines))

        if ev is not None:
            ev.verified = bool(all_ok)
            ev.verified_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.app.store.update_evidence(ev)
        self.app.store.append_custody(
            self.app.store.settings.operator, self.app.store.settings.role,
            "VERIFICATION_" + ("PASSED" if all_ok else "FAILED"),
            f"{ev.item_label if ev else os.path.basename(self._task_path)} — "
            f"MD5 {hashes.get('md5', '—')[:12]}… SHA256 {hashes.get('sha256', '—')[:12]}…",
            self.app.secret)
        self.app.notify("Verification recorded in custody log.",
                        GOOD if all_ok else BAD)
        self.app.refresh_all()

    def _write_result(self, text):
        self.res_text.configure(state="normal")
        self.res_text.delete("1.0", "end")
        self.res_text.insert("1.0", text)
        self.res_text.configure(state="disabled")