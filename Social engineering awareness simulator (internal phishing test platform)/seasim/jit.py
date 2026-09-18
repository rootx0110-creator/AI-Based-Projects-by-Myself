"""Just-in-time training moment for SeaSim.

When a participant interacts with a simulated email (opens / clicks /
reports), SeaSim shows this educational window instead of any real
look-alike page. It explains what happened, lists the phishing
indicators for the template, and gives one concrete coaching tip.
No credentials or personal data are ever requested or stored.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from seasim.engine.models import EmailTemplate, ST_CLICKED, ST_REPORTED
from seasim.templates import jit_tip


class JITWindow(tk.Toplevel):
    """Educational landing page shown after interaction."""

    def __init__(self, master, template: EmailTemplate,
                 participant_name: str = "", status: str = ST_CLICKED,
                 on_done: Optional[callable] = None) -> None:
        super().__init__(master)
        self.template = template
        self.on_done = on_done

        clicked = status == ST_CLICKED
        reported = status == ST_REPORTED

        self.title("SeaSim - Training moment")
        self.configure(bg="#ffffff")
        self.resizable(False, False)
        w, h = 620, 560
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        # Header band: green for reported, amber for clicked.
        color = "#16a34a" if reported else "#d97706"
        head = tk.Frame(self, bg=color)
        head.pack(fill="x")
        title = ("Good catch - this was a simulation"
                 if reported else
                 ("You opened a simulated phishing email" if not clicked else
                  "You clicked a simulated phishing link"))
        tk.Label(head, text=title, fg="white", bg=color,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=24,
                                                     pady=(20, 2))
        who = f"For: {participant_name}" if participant_name else ""
        tk.Label(head, text=who, fg="#ffffff", bg=color,
                 font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(0, 16))

        body = tk.Frame(self, bg="#ffffff")
        body.pack(fill="both", expand=True)

        tk.Label(body, text="What just happened?", fg="#0f172a", bg="#ffffff",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=24,
                                                     pady=(18, 4))
        what = (
            "This email was part of an authorized awareness exercise run "
            "with SeaSim. Nothing was recorded beyond the fact that you "
            "interacted with it - no credentials, no keystrokes, no "
            "personal data. Nothing left your machine."
            if not reported else
            "You reported this message - exactly the right reaction. It was "
            "a scheduled simulation from your security team. Please keep "
            "reporting anything suspicious, real or simulated."
        )
        tk.Label(body, text=what, fg="#334155", bg="#ffffff",
                 font=("Segoe UI", 10), wraplength=560,
                 justify="left").pack(anchor="w", padx=24, pady=4)

        tk.Label(body, text="The email was simulated:", fg="#0f172a",
                 bg="#ffffff", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=24, pady=(14, 4))
        tk.Label(body, text=f'Subject: "{template.subject}"  -  '
                 f'techniques used: {", ".join(template.techniques) or "n/a"}',
                 fg="#334155", bg="#ffffff", font=("Segoe UI", 10),
                 wraplength=560, justify="left").pack(anchor="w", padx=24,
                                                      pady=4)

        tk.Label(body, text="How to spot it next time", fg="#0f172a",
                 bg="#ffffff", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=24, pady=(14, 4))
        for ind in template.phishing_indicators:
            row = tk.Frame(body, bg="#ffffff")
            row.pack(anchor="w", padx=24, pady=1)
            tk.Label(row, text="-", fg="#d97706", bg="#ffffff",
                     font=("Segoe UI", 10, "bold")).pack(side="left")
            tk.Label(row, text=" " + ind, fg="#334155", bg="#ffffff",
                     font=("Segoe UI", 10), wraplength=540,
                     justify="left").pack(side="left")

        tip = tk.Frame(self, bg="#eef2ff")
        tip.pack(fill="x", side="bottom", padx=16, pady=(6, 0))
        tk.Label(tip, text="TIP", fg="#4338ca", bg="#eef2ff",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10,
                                                    pady=(8, 0))
        tk.Label(tip, text=jit_tip(template), fg="#1e1b4b", bg="#eef2ff",
                 font=("Segoe UI", 10, "bold"), wraplength=560,
                 justify="left").pack(anchor="w", padx=10, pady=(2, 10))

        btns = tk.Frame(self, bg="#ffffff")
        btns.pack(fill="x", side="bottom", pady=12)
        ttk.Button(btns, text="Got it - close", command=self._done).pack()

        self.bind("<Escape>", lambda e: self._done())
        self.protocol("WM_DELETE_WINDOW", self._done)

    def _done(self) -> None:
        if self.on_done is not None:
            try:
                self.on_done()
            except Exception:
                pass
        self.destroy()
