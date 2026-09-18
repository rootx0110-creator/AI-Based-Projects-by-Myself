"""Runtime consent gate for SeaSim.

A modal dialog that must be completed before a campaign can launch.
Three independent confirmations are collected and stored on the
campaign + settings consent log:

  1. Scope   - recipients are internal, template is AI-themed-aware
  2. Policy  - the authorized-use policy was read and the ack phrase typed
  3. Identity - operator signs with name + role

No consent record -> the engine refuses to start delivery.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Tuple

from seasim import constants as C
from seasim.engine import models as M
from seasim.safety import POLICY_TEXT


class ConsentDialog(tk.Toplevel):
    """Step-by-step consent workflow (3 pages). Returns consent tuple."""

    def __init__(self, master, engine, campaign: M.Campaign,
                 block: bool = True,
                 on_complete: Optional[Callable[[Optional[Tuple[str, str]]], None]] = None) -> None:
        super().__init__(master)
        self.engine = engine
        self.campaign = campaign
        self.on_complete = on_complete
        # None = cancelled/incomplete; (name, role) = authorized.
        self.result: Optional[Tuple[str, str]] = None

        tpl = engine.get_template(campaign.template_id)
        self.tpl = tpl

        self.title("Authorization required - SeaSim")
        self.configure(bg="#ffffff")
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)

        w, h = 680, 640
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        # Make sure the dialog is impossible to miss: centered, on top,
        # and focused. (A modal hidden behind the main window reads as
        # 'there is no way to authorize'.)
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.after(250, lambda: self.attributes("-topmost", False))

        self._build()
        self._show_scope()
        self.bind("<Escape>", lambda e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        if block:
            self.wait_window(self)

    # ------------------------------------------------------------------ UI

    def _build(self) -> None:
        head = tk.Frame(self, bg="#0f172a")
        head.pack(fill="x")
        tk.Label(head, text="AUTHORIZATION WORKFLOW", fg="#93c5fd",
                 bg="#0f172a", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", padx=24, pady=(18, 2))
        tk.Label(head, text=f"Campaign: {self.campaign.name}", fg="white",
                 bg="#0f172a", font=("Segoe UI", 15, "bold")).pack(
            anchor="w", padx=24, pady=(0, 14))

        self.body = tk.Frame(self, bg="#ffffff")
        self.body.pack(fill="both", expand=True)

        foot = tk.Frame(self, bg="#f1f5f9")
        foot.pack(fill="x", side="bottom")
        self.step_lbl = tk.Label(foot, text="Step 1 of 3", fg="#64748b",
                                 bg="#f1f5f9", font=("Segoe UI", 9))
        self.step_lbl.pack(side="left", padx=16, pady=10)
        self.back_btn = ttk.Button(foot, text="< Back", command=self._back,
                                   state="disabled")
        self.back_btn.pack(side="right", padx=(0, 8), pady=10)
        self.next_btn = ttk.Button(foot, text="Next >", command=self._next)
        self.next_btn.pack(side="right", padx=8, pady=10)

    def _clear(self) -> None:
        for w in self.body.winfo_children():
            w.destroy()

    def _head(self, text: str) -> None:
        tk.Label(self.body, text=text, fg="#0f172a", bg="#ffffff",
                 font=("Segoe UI", 13, "bold"), wraplength=600,
                 justify="left").pack(anchor="w", padx=24, pady=(20, 6))

    def _text(self, text: str) -> None:
        tk.Label(self.body, text=text, fg="#334155", bg="#ffffff",
                 font=("Segoe UI", 10), wraplength=600,
                 justify="left").pack(anchor="w", padx=24, pady=4)

    def _tick(self, var: tk.BooleanVar, text: str) -> tk.Checkbutton:
        """Classic checkbutton with guaranteed-visible tick square.

        ttk/clam indicators can render white-on-white on light pages and
        look like plain text - classic widgets with explicit colors do
        not have that problem.
        """
        return tk.Checkbutton(
            self.body, variable=var, text=text,
            bg="#ffffff", fg="#0f172a", selectcolor="#ffffff",
            activebackground="#ffffff", activeforeground="#0f172a",
            font=("Segoe UI", 10), wraplength=560, justify="left",
            anchor="w", highlightthickness=0,
        )

    # Page 1: scope ---------------------------------------------------------

    def _show_scope(self) -> None:
        self._clear()
        self.page = 1
        self.step_lbl.config(text="Step 1 of 3 - Scope & content")
        self._head("Confirm simulation scope")
        self._text(
            "Review the recipients and email content below. Every address "
            "must belong to your own organization.")

        rec = tk.Frame(self.body, bg="#ffffff")
        rec.pack(anchor="w", padx=24, pady=(8, 4))
        n = len(self.campaign.participant_ids)
        tk.Label(rec, text=f"Recipients: {n}", fg="#0f172a", bg="#ffffff",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        if self.tpl is not None:
            tk.Label(rec, text=f"Template: {self.tpl.name} "
                     f"({self.tpl.category}, difficulty {self.tpl.difficulty})",
                     fg="#334155", bg="#ffffff",
                     font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))
            tk.Label(rec, text=f"Subject: {self.tpl.subject}", fg="#334155",
                     bg="#ffffff", font=("Segoe UI", 10)).pack(anchor="w")

        self.scope_var = tk.BooleanVar(value=False)
        self._tick(
            self.scope_var,
            "All recipients are internal staff covered by an authorized "
            "awareness program (no external or personal addresses).",
        ).pack(fill="x", anchor="w", padx=24, pady=(14, 4))

        self.ai_var = tk.BooleanVar(value=False)
        ai_needed = (self.tpl is not None
                     and self.tpl.category == M.CATEGORY_AI)
        self.ai_chk = self._tick(
            self.ai_var,
            "If any content is AI-generated / AI-themed, I confirm it "
            "complies with internal AI-use rules.")
        self.ai_chk.pack(fill="x", anchor="w", padx=24, pady=4)
        if not ai_needed:
            self.ai_chk.config(state="disabled")
            self.ai_var.set(True)

        self.rem_var = tk.BooleanVar(value=not self.campaign.scheduled)
        self._tick(
            self.rem_var,
            "I scheduled this launch at an appropriate time (or it is "
            "immediate) and will monitor it while it runs.",
        ).pack(fill="x", anchor="w", padx=24, pady=4)

    # Page 2: policy ----------------------------------------------------

    def _show_policy(self) -> None:
        self._clear()
        self.page = 2
        self.step_lbl.config(text="Step 2 of 3 - Authorized-use policy")
        self._head("Read the authorized-use policy")
        txt = tk.Text(self.body, height=15, wrap="word", font=("Consolas", 9),
                      bg="#f8fafc", fg="#334155", relief="flat", padx=12,
                      pady=10)
        txt.insert("1.0", POLICY_TEXT)
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True, padx=24, pady=8)

        self.policy_var = tk.BooleanVar(value=False)
        self._tick(
            self.policy_var,
            "I have read the authorized-use policy above and agree to "
            "follow it for this campaign.",
        ).pack(fill="x", anchor="w", padx=24, pady=(6, 4))

    # Page 3: identity --------------------------------------------------

    def _show_identity(self) -> None:
        self._clear()
        self.page = 3
        self.step_lbl.config(text="Step 3 of 3 - Sign-off")
        self._head("Sign off as the authorizing operator")
        self._text("Your name and role are written to the immutable consent "
                   "log stored with this campaign.")

        form = tk.Frame(self.body, bg="#ffffff")
        form.pack(anchor="w", padx=24, pady=12)
        tk.Label(form, text="Full name:", fg="#334155", bg="#ffffff",
                 font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w",
                                             pady=4)
        self.name_entry = tk.Entry(form, font=("Segoe UI", 11), width=34,
                                   bg="white")
        self.name_entry.grid(row=0, column=1, padx=8, pady=4)
        pre = self.engine.store.settings.operator_name
        if pre:
            self.name_entry.insert(0, pre)
        tk.Label(form, text="Role / team:", fg="#334155", bg="#ffffff",
                 font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w",
                                             pady=4)
        self.role_entry = tk.Entry(form, font=("Segoe UI", 11), width=34,
                                   bg="white")
        self.role_entry.grid(row=1, column=1, padx=8, pady=4)
        self.role_entry.insert(0, "Security Awareness Team")

        self.final_var = tk.BooleanVar(value=False)
        self._tick(
            self.final_var,
            "I am authorized to run this simulation and accept "
            "responsibility for this launch.",
        ).pack(fill="x", anchor="w", padx=24, pady=(10, 4))
        self.next_btn.config(text="Launch simulation")

    # Navigation ----------------------------------------------------------

    def _can_leave_page1(self) -> bool:
        if not self.scope_var.get():
            return False
        if not self.rem_var.get():
            return False
        if (self.tpl is not None and self.tpl.category == M.CATEGORY_AI
                and not self.ai_var.get()):
            return False
        return True

    def _next(self) -> None:
        if self.page == 1:
            if not self._can_leave_page1():
                self._warn("Please confirm every checkbox on this page "
                           "before continuing.")
                return
            self._show_policy()
            self.back_btn.config(state="normal")
        elif self.page == 2:
            if not self.policy_var.get():
                self._warn("Please confirm that you have read and agree to "
                           "the authorized-use policy before continuing.")
                return
            self._show_identity()
        elif self.page == 3:
            name = self.name_entry.get().strip()
            role = self.role_entry.get().strip()
            if not name or not role:
                self._warn("Enter your name and role to sign off.")
                return
            if not self.final_var.get():
                self._warn("Confirm the authorization checkbox to launch.")
                return
            self.result = (name, role)
            self._close()

    def _back(self) -> None:
        if self.page == 2:
            self._show_scope()
            self.back_btn.config(state="disabled")
        elif self.page == 3:
            self._show_policy()

    def _warn(self, msg: str) -> None:
        from tkinter import messagebox

        messagebox.showwarning("SeaSim consent", msg, parent=self)

    def _cancel(self) -> None:
        # An accidental X or Escape must not silently discard a half-done
        # authorization - confirm first.
        from tkinter import messagebox

        really = messagebox.askyesno(
            "Cancel authorization",
            "Authorization is NOT complete - the campaign stays a Draft "
            "and cannot launch.\n\nCancel anyway?",
            parent=self,
        )
        if not really:
            return
        self.result = None
        self._close()

    def _close(self) -> None:
        try:
            self.grab_release()
        except Exception:
            pass
        cb = self.on_complete
        self.destroy()
        if cb is not None:
            try:
                cb(self.result)
            except Exception:
                # Never silent: a swallowed error here made completed
                # authorizations look like no-ops (Draft forever).
                import traceback
                traceback.print_exc()
