"""Tkinter front end for arpscan.

This is the double-click-friendly application UI: enter targets (or scan your
own network), pick a backend, and view results in a table. Scanning runs on a
background thread so the window never freezes; results are marshaled back to
the UI thread via a queue polled by ``after()``.

Reuses the exact same logic as the CLI: ``Scanner`` + backends + formatters.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from . import __version__
from .backends import BackendError
from .localnet import detect_local_networks
from .models import Host
from .output import format_csv, format_json
from .scanner import Scanner, select_backend

DEFAULT_TIMEOUT = "2.0"
DEFAULT_RETRIES = "1"


class ArpScanApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title(f"arpscan {__version__} — ARP / live-host discovery")
        self.geometry("780x540")
        self.minsize(600, 400)

        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._hosts: List[Host] = []
        self._scanning = False

        self._build_ui()
        self.after(100, self._poll_queue)

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        # --- targets row -------------------------------------------------
        row = ttk.Frame(self, padding=(8, 8, 8, 4))
        row.pack(fill="x")
        ttk.Label(row, text="Targets:").pack(side="left")
        self.target_var = tk.StringVar()
        entry = ttk.Entry(row, textvariable=self.target_var)
        entry.pack(side="left", fill="x", expand=True, padx=6)
        self.auto_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            row, text="scan my network", variable=self.auto_var
        ).pack(side="left")
        entry.bind("<Return>", lambda _e: self.start_scan())

        # --- options row -------------------------------------------------
        row2 = ttk.Frame(self, padding=(8, 0, 8, 6))
        row2.pack(fill="x")
        ttk.Label(row2, text="Backend:").pack(side="left")
        self.backend_var = tk.StringVar(value="auto")
        ttk.Combobox(
            row2,
            textvariable=self.backend_var,
            values=("auto", "scapy", "system"),
            state="readonly",
            width=8,
        ).pack(side="left", padx=(4, 12))
        ttk.Label(row2, text="Timeout (s):").pack(side="left")
        self.timeout_var = tk.StringVar(value=DEFAULT_TIMEOUT)
        ttk.Entry(row2, textvariable=self.timeout_var, width=6).pack(
            side="left", padx=(4, 12)
        )
        ttk.Label(row2, text="Retries:").pack(side="left")
        self.retries_var = tk.StringVar(value=DEFAULT_RETRIES)
        ttk.Entry(row2, textvariable=self.retries_var, width=5).pack(
            side="left", padx=4
        )
        self.vendor_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            row2, text="show vendors", variable=self.vendor_var
        ).pack(side="left", padx=(16, 0))

        # --- scan button -------------------------------------------------
        self.scan_btn = ttk.Button(self, text="Scan", command=self.start_scan)
        self.scan_btn.pack(pady=(0, 6))

        # --- results table ----------------------------------------------
        frame = ttk.Frame(self, padding=(8, 0, 8, 6))
        frame.pack(fill="both", expand=True)
        columns = ("ip", "mac", "vendor")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")
        self.tree.heading("ip", text="IP")
        self.tree.heading("mac", text="MAC address")
        self.tree.heading("vendor", text="Vendor")
        self.tree.column("ip", width=140, stretch=False)
        self.tree.column("mac", width=210, stretch=False)
        self.tree.column("vendor", width=220)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)

        # --- bottom bar --------------------------------------------------
        row3 = ttk.Frame(self, padding=(8, 0, 8, 8))
        row3.pack(fill="x")
        ttk.Button(row3, text="Save CSV…", command=self._export_csv).pack(
            side="left"
        )
        ttk.Button(row3, text="Save JSON…", command=self._export_json).pack(
            side="left", padx=6
        )
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(row3, textvariable=self.status_var).pack(side="right")

    # --------------------------------------------------------------- scan

    def start_scan(self) -> None:
        """Validate inputs and kick off a background scan."""
        if self._scanning:
            return

        auto = self.auto_var.get()
        targets = self.target_var.get().strip()
        if auto:
            networks = detect_local_networks()
            if not networks:
                messagebox.showerror(
                    "arpscan",
                    "Could not detect your local network.\n"
                    "Enter a target manually (e.g. 192.168.1.0/24).",
                )
                return
            targets = ", ".join(str(net) for net in networks)
            self.target_var.set(targets)
        elif not targets:
            messagebox.showerror(
                "arpscan", "Enter targets (e.g. 192.168.1.0/24) or tick "
                "'scan my network'."
            )
            return

        try:
            timeout = float(self.timeout_var.get())
            retries = int(self.retries_var.get())
        except ValueError:
            messagebox.showerror("arpscan", "Timeout and retries must be numbers.")
            return
        if timeout <= 0:
            messagebox.showerror("arpscan", "Timeout must be greater than zero.")
            return

        backend_name = self.backend_var.get()
        # Read all Tk variables on the main thread; Tk vars are not
        # thread-safe and the worker thread must only get plain values.
        do_vendor = self.vendor_var.get()
        self._scanning = True
        self.scan_btn.config(state="disabled")
        self.status_var.set("Scanning…")
        thread = threading.Thread(
            target=self._run_scan,
            args=(targets, backend_name, timeout, retries, do_vendor),
            daemon=True,
        )
        thread.start()

    def _run_scan(self, targets, backend_name, timeout, retries, do_vendor) -> None:
        """Runs in a background thread; never touch Tk widgets or vars here.

        ``targets`` is a string (possibly comma-joined); wrap it in a list
        because ``Scanner.scan`` expects a sequence of target strings.
        """
        target_list = [targets]
        try:
            backend = select_backend(backend_name)
            hosts = Scanner(backend, do_vendor=do_vendor).scan(
                target_list, timeout=timeout, retries=retries
            )
            self._queue.put(("done", backend.name, hosts, None))
        except BackendError as exc:
            if backend_name == "auto":
                # e.g. scapy present but no raw-packet privileges.
                try:
                    fallback = select_backend("system")
                    hosts = Scanner(fallback, do_vendor=do_vendor).scan(
                        target_list, timeout=timeout, retries=retries
                    )
                    self._queue.put(("done", fallback.name, hosts, None))
                    return
                except BackendError as fallback_exc:
                    self._queue.put(("error", None, [], str(fallback_exc)))
                    return
            self._queue.put(("error", None, [], str(exc)))
        except Exception as exc:  # pragma: no cover - defensive
            self._queue.put(("error", None, [], f"unexpected error: {exc}"))

    def _poll_queue(self) -> None:
        """UI thread: drain scan results from the background thread."""
        try:
            while True:
                kind, backend_name, hosts, error = self._queue.get_nowait()
                if kind == "done":
                    self._show_hosts(hosts)
                    self.status_var.set(
                        f"{len(hosts)} host(s) found "
                        f"(backend: {backend_name})."
                    )
                elif kind == "error":
                    self.status_var.set("Scan failed.")
                    messagebox.showerror("arpscan", error)
        except queue.Empty:
            pass
        finally:
            self._scanning = False
            self.scan_btn.config(state="normal")
        self.after(100, self._poll_queue)

    def _show_hosts(self, hosts: List[Host]) -> None:
        self._hosts = hosts
        self.tree.delete(*self.tree.get_children())
        for host in hosts:
            self.tree.insert(
                "", "end",
                values=(host.ip, host.mac, host.vendor or ""),
            )

    # ------------------------------------------------------------- export

    def _export_csv(self) -> None:
        self._export("csv", [("CSV files", "*.csv")], "hosts.csv")

    def _export_json(self) -> None:
        self._export("json", [("JSON files", "*.json")], "hosts.json")

    def _export(self, fmt: str, filetypes, default_name: str) -> None:
        if not self._hosts:
            messagebox.showinfo("arpscan", "No results to save yet.")
            return
        path = filedialog.asksaveasfilename(
            title="Save results",
            defaultextension=f".{fmt}",
            filetypes=filetypes,
            initialfile=default_name,
        )
        if not path:
            return
        text = format_csv(self._hosts) if fmt == "csv" else format_json(self._hosts)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        except OSError as exc:
            messagebox.showerror("arpscan", f"Could not save file: {exc}")
            return
        self.status_var.set(f"Saved to {path}")


def main() -> None:
    """Entry point used by the GUI exe."""
    app = ArpScanApp()
    app.mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()