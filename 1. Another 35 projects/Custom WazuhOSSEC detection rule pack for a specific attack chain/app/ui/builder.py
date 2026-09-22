"""Rule Builder: form-driven rule authoring with live local_rules.xml preview."""
from __future__ import annotations

import customtkinter as ctk

from ..rules_core import LOG_SOURCES, STAGES, STAGE_BY_KEY, build_rule, render_builder_xml, toxml_escape
from . import theme
from .widgets import Panel, make_button

DECODERS = ["windows_eventchannel", "syslog", "apache", "syscheck", "audit", "(none)"]
CONDITIONS = ["match", "regex", "field", "(none)"]


class BuilderView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.app = app
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)
        self._level = 5

        self._build_form()
        self._build_preview()

    # ---------------------------------------------------------------- form
    def _build_form(self):
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        panel = Panel(box, "Rule properties", border_width=0, corner_radius=12)
        panel.pack(fill="x")
        body = panel.content
        for i in range(3):
            body.grid_columnconfigure(i, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, weight=1)

        def lbl(parent, text, r, c):
            ctk.CTkLabel(parent, text=text, text_color=theme.MUTED,
                         font=theme.font(11), anchor="w").grid(
                row=r, column=c, sticky="w", padx=12, pady=(8, 0))
            return None

        def ent(parent, ph="", w=10):
            e = ctk.CTkEntry(parent, placeholder_text=ph, fg_color=theme.PANEL2,
                             border_color=theme.LINE, font=theme.font(12),
                             width=w)
            return e

        r = 0
        lbl(body, "RULE ID", r, 0)
        self.f_id = ent(body, "auto", 12)
        self.f_id.grid(row=r + 1, column=0, sticky="ew", padx=12, pady=(0, 4))

        lbl(body, "SEVERITY LEVEL (0-16)", r, 1)
        self.f_level = ctk.CTkSlider(body, from_=0, to=16, number_of_steps=16,
                                     height=16, progress_color=theme.ACCENT,
                                     button_color=theme.ACCENT,
                                     button_hover_color=theme.ACCENT_HOVER,
                                     command=self._on_level)
        self.f_level.grid(row=r + 1, column=1, sticky="ew", padx=12, pady=(10, 4))
        self.f_level_val = ctk.CTkLabel(body, text=str(self._level),
                                        text_color=theme.FG, width=46,
                                        font=theme.font(12, "bold"))
        self.f_level_val.grid(row=r + 1, column=2, sticky="w", padx=(0, 12))

        r = 2
        lbl(body, "ATTACK STAGE", r, 0)
        self.f_stage = ctk.CTkOptionMenu(
            body, values=[s["name"] for s in STAGES],
            fg_color=theme.PANEL2, button_color=theme.PANEL3,
            button_hover_color=theme.ACCENT, text_color=theme.FG,
            dropdown_fg_color=theme.PANEL2, dropdown_hover_color=theme.ACCENT,
            font=theme.font(12), height=34, corner_radius=8)
        self.f_stage.set(STAGES[1]["name"])
        self.f_stage.grid(row=r + 1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 4))

        lbl(body, "LOG SOURCE", r, 2)
        self.f_source = ctk.CTkOptionMenu(
            body, values=LOG_SOURCES, fg_color=theme.PANEL2,
            button_color=theme.PANEL3, button_hover_color=theme.ACCENT,
            text_color=theme.FG, dropdown_fg_color=theme.PANEL2,
            dropdown_hover_color=theme.ACCENT, font=theme.font(12),
            height=34, corner_radius=8)
        self.f_source.set("windows_security")
        self.f_source.grid(row=r + 1, column=2, sticky="ew", padx=12, pady=(0, 4))

        r = 4
        lbl(body, "MITRE TECHNIQUE", r, 0)
        self.f_mitre = ent(body, "T1190")
        self.f_mitre.grid(row=r + 1, column=0, sticky="ew", padx=12, pady=(0, 4))

        lbl(body, "DECODED AS", r, 1)
        self.f_decoder = ctk.CTkOptionMenu(
            body, values=DECODERS, fg_color=theme.PANEL2, button_color=theme.PANEL3,
            button_hover_color=theme.ACCENT, text_color=theme.FG,
            dropdown_fg_color=theme.PANEL2, dropdown_hover_color=theme.ACCENT,
            font=theme.font(12), height=34, corner_radius=8)
        self.f_decoder.set("windows_eventchannel")
        self.f_decoder.grid(row=r + 1, column=1, columnspan=2, sticky="ew", padx=12, pady=(0, 4))

        r = 6
        lbl(body, "PARENT RULE (if_sid)", r, 0)
        self.f_parent = ent(body, "empty for standalone", 12)
        self.f_parent.grid(row=r + 1, column=0, sticky="ew", padx=12, pady=(0, 4))

        lbl(body, "Condition kind", r, 1)
        self.f_cond_kind = ctk.CTkOptionMenu(
            body, values=CONDITIONS, fg_color=theme.PANEL2,
            button_color=theme.PANEL3, button_hover_color=theme.ACCENT,
            text_color=theme.FG, dropdown_fg_color=theme.PANEL2,
            dropdown_hover_color=theme.ACCENT, font=theme.font(12),
            height=34, corner_radius=8, command=lambda _v: self._preview())
        self.f_cond_kind.set("match")
        self.f_cond_kind.grid(row=r + 1, column=1, sticky="ew", padx=12, pady=(0, 4))

        lbl(body, "GROUP", r, 2)
        self.f_group = ent(body, "local")
        self.f_group.grid(row=r + 1, column=2, sticky="ew", padx=12, pady=(0, 4))

        # condition value row
        ctk.CTkLabel(body, text="CONDITION", text_color=theme.MUTED,
                     font=theme.font(11), anchor="w").grid(
            row=8, column=0, sticky="w", padx=12, pady=(8, 0))
        self.f_pattern = ent(body, "match / regex pattern or value e.g. powershell")
        self.f_pattern.grid(row=9, column=0, columnspan=3, sticky="ew",
                            padx=12, pady=(0, 4))
        ctk.CTkLabel(body, text="FIELD NAME (when kind=field)",
                     text_color=theme.MUTED, font=theme.font(11), anchor="w").grid(
            row=10, column=0, sticky="w", padx=12, pady=(8, 0))
        self.f_field = ent(body, "e.g. win.system.eventID")
        self.f_field.grid(row=11, column=0, columnspan=3, sticky="ew",
                          padx=12, pady=(0, 4))

        ctk.CTkLabel(body, text="DESCRIPTION (required)",
                     text_color=theme.MUTED, font=theme.font(11), anchor="w").grid(
            row=12, column=0, sticky="w", padx=12, pady=(8, 0))
        self.f_desc = ctk.CTkTextbox(body, height=72, fg_color=theme.PANEL2,
                                     border_color=theme.LINE, border_width=1,
                                     font=theme.font(12), corner_radius=8)
        self.f_desc.grid(row=13, column=0, columnspan=3, sticky="ew",
                         padx=12, pady=(0, 10))

        # bind change events -> live preview
        for w in (self.f_id, self.f_mitre, self.f_pattern, self.f_field,
                  self.f_parent, self.f_group):
            w.bind("<KeyRelease>", lambda _e: self._preview())
        self.f_desc.bind("<KeyRelease>", lambda _e: self._preview())

        actions = ctk.CTkFrame(box, fg_color="transparent")
        actions.pack(fill="x", pady=(10, 0))
        self.btn_add = make_button(actions, "Add rule to pack", self._add_rule,
                                   "accent")
        self.btn_add.pack(side="left", padx=(0, 8))
        make_button(actions, "Reset form", self._reset, "ghost")\
            .pack(side="left", padx=8)
        self.feedback = ctk.CTkLabel(actions, text="", text_color=theme.GOOD,
                                     font=theme.font(12))
        self.feedback.pack(side="left", padx=(18, 0))

    # -------------------------------------------------------------- preview
    def _build_preview(self):
        panel = Panel(self, "Local rules preview")
        panel.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 0))
        body = panel.content
        body.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=1)
        note = ctk.CTkLabel(body, text="Generated <rule> block (live)",
                            text_color=theme.MUTED, font=theme.font(11))
        note.grid(row=0, column=0, sticky="w", padx=18, pady=(10, 0))
        self.preview = ctk.CTkTextbox(body, fg_color="#0a0e18",
                                      text_color="#c8f0d0",
                                      font=theme.mono(13), corner_radius=8,
                                      border_width=1, border_color=theme.LINE)
        self.preview.grid(row=1, column=0, sticky="nsew", padx=18, pady=(4, 16))

    def _on_level(self, _v=None):
        self._level = int(round(self.f_level.get()))
        self.f_level_val.configure(text=str(self._level))
        self._preview()

    # -------------------------------------------------------------- helpers
    def _stage_of_current(self) -> str:
        name = self.f_stage.get()
        for s in STAGES:
            if s["name"] == name:
                return s["key"]
        return "execution"

    def _selected_rule_xml(self) -> str:
        rid = self._rid()
        level = self._level
        desc = self.f_desc.get("1.0", "end").strip()
        group = self.f_group.get().strip() or "local"
        parser = self.f_decoder.get()
        decoder = "" if parser == "(none)" else parser
        kind = self.f_cond_kind.get()
        pattern = self.f_pattern.get().strip()
        field = self.f_field.get().strip()
        parent = self.f_parent.get().strip()
        return render_builder_xml(
            rid=rid, level=level, description=desc or "...",
            group=group, decoder=decoder, pattern_kind=kind,
            pattern=pattern, field=field,
            value=pattern if kind == "field" else "",
            parent_id=parent or "")

    def _rid(self) -> int:
        raw = self.f_id.get().strip()
        if raw:
            try:
                return int(raw)
            except ValueError:
                pass
        return self.app.rulepack.allocate_id()

    def _preview(self):
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", self._selected_rule_xml())

    def _reset(self):
        self.f_id.delete(0, "end")
        self.f_mitre.delete(0, "end")
        self.f_pattern.delete(0, "end")
        self.f_field.delete(0, "end")
        self.f_parent.delete(0, "end")
        self.f_group.delete(0, "end")
        self.f_group.insert(0, "local")
        self.f_desc.delete("1.0", "end")
        self.f_level.set(5)
        self._on_level()
        self._preview()

    def _add_rule(self):
        desc = self.f_desc.get("1.0", "end").strip()
        if not desc:
            self.feedback.configure(text="Description is required.",
                                    text_color=theme.DANGER)
            return
        stage = self._stage_of_current()
        st = STAGE_BY_KEY[stage]
        rid = self._rid()
        if self.app.rulepack.get(rid):
            self.feedback.configure(text=f"Rule {rid:06d} already exists.",
                                    text_color=theme.DANGER)
            return
        rule = build_rule(
            rid=rid, level=self._level, stage=stage,
            mitre=(self.f_mitre.get().strip() or f"{st['tactic']}-custom"),
            source=self.f_source.get(),
            description=desc,
            xml=self._selected_rule_xml(),
            group=self.f_group.get().strip() or "local",
            created_by="builder")
        self.app.rulepack.add(rule)
        self.app.save_pack(f"Added rule {rule.rid} to the pack.")
        self.feedback.configure(text=f"Rule {rule.rid} added.",
                                text_color=theme.GOOD)
        self._reset()

    def refresh(self):
        self._preview()