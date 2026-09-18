import customtkinter as ctk

from .theme import MUTED, TEXT, font


class BaseView(ctk.CTkFrame):
    key = "base"
    title = "Base"
    subtitle = ""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._header = ctk.CTkFrame(self, fg_color="transparent")
        self._header.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 10))
        self._header.grid_columnconfigure(1, weight=1)
        self._title = ctk.CTkLabel(self._header, text=self.title, font=font(22, "bold"),
                                   text_color=TEXT, anchor="w")
        self._title.grid(row=0, column=0, sticky="w")
        self._subtitle = ctk.CTkLabel(self._header, text=self.subtitle, font=font(12),
                                      text_color=MUTED, anchor="w")
        self._subtitle.grid(row=1, column=0, sticky="w")

        self._toolbar = ctk.CTkFrame(self._header, fg_color="transparent")
        self._toolbar.grid(row=0, column=1, rowspan=2, sticky="e")

        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.grid(row=1, column=0, sticky="nsew")
        self._body.grid_columnconfigure(0, weight=1)
        self._body.grid_rowconfigure(0, weight=1)

    @property
    def body(self):
        return self._body

    @property
    def toolbar(self):
        return self._toolbar

    def append_toolbar(self, widget):
        widget.grid(row=0, column=len(self._toolbar.winfo_children()), padx=(0, 8))

    def refresh(self):
        pass

    def on_show(self):
        self.refresh()