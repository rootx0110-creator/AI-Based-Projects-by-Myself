# MemoryForensicsAnalyzer - local desktop UI for the Volatility plugin workflow.
# Entry point: main.py

import sys
import os
import html
import json
import shutil
import datetime
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSize, QRectF, QPointF
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QPen, QBrush
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QLabel, QFrame, QVBoxLayout,
    QHBoxLayout, QGridLayout, QStackedWidget, QScrollArea, QTextBrowser,
    QFileDialog, QMessageBox, QLineEdit, QPlainTextEdit, QProgressBar,
)

APP_TITLE = "Memory Forensics Analyzer"
APP_VERSION = "1.0.0"

APP_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
DOCS_DIR = APP_DIR / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = APP_DIR / "analyzer_state.json"

DOC_ORDER = [
    ("architecture.md", "Architecture", "How the tool is built"),
    ("state.md", "Project State", "Phase, done, in-progress"),
    ("memory.md", "Memory Notes", "Forensics reference material"),
]

WORKFLOW = [
    dict(id=1, title="Acquisition & Verification",
         desc="Validate the capture file and confirm image integrity before analysis.",
         plugins=["crashinfo", "memmap", "hashdeep"], seconds=2,
         result="Image validated: 2 GB raw sample, hash matched; KDBG signature present.",
         findings=[
             {"sev": "info", "title": "Memory image verified",
              "detail": "SHA-256 match confirmed; valid Windows memory capture (KDBG signature present).",
              "from": "crashinfo / hashdeep"},
         ],
         artifacts=[
             {"name": "case_sample.raw", "kind": "Memory image", "from": "Acquisition & Verification"},
         ]),
    dict(id=2, title="Profile Identification",
         desc="Detect the OS/kernel symbol layer the dump was taken from.",
         plugins=["imageinfo", "kdbgscan", "banner"], seconds=3,
         result="Symbol layer resolved: Windows x64 (Kernel 10.0.22621) - symbols loaded OK.",
         findings=[
             {"sev": "info", "title": "Profile / symbol layer identified",
              "detail": "Windows 10 x64 (Kernel 10.0.22621). Symbols loaded successfully.",
              "from": "imageinfo"},
         ]),
    dict(id=3, title="Process Analysis",
         desc="Enumerate processes, parents, handles and spot hidden/unlinked entries.",
         plugins=["pslist", "pstree", "psscan", "psxview"], seconds=4,
         result="87 processes enumerated; psscan found 2 unlinked candidates (PID 1488, PID 3401); psxview consistent.",
         findings=[
             {"sev": "high", "title": "Unlinked processes detected",
              "detail": "2 processes (PID 1488, PID 3401) appear in psscan but are missing from the active pslist - possible evasion.",
              "from": "psscan / psxview"},
             {"sev": "medium", "title": "Suspicious process ancestry",
              "detail": "svchost (PID 1024) was spawned from an unusual parent chain and flagged by pstree.",
              "from": "pstree"},
         ]),
    dict(id=4, title="Network Analysis",
         desc="Recover TCP/UDP connections and resolve remote endpoints.",
         plugins=["netscan", "connections", "sockscan"], seconds=3,
         result="143 TCP, 12 UDP, 5 listening sockets; 3 remote endpoints flagged for review.",
         findings=[
             {"sev": "medium", "title": "Flagged remote endpoints",
              "detail": "3 outbound TCP connections to unusual external IPs require review.",
              "from": "netscan"},
             {"sev": "low", "title": "Listening sockets on high ports",
              "detail": "5 local listening sockets on high-numbered ports identified.",
              "from": "sockscan"},
         ]),
    dict(id=5, title="Malware Triaging",
         desc="Scan for injected code, suspicious modules and API hooks.",
         plugins=["malfind", "dlllist", "apihooks", "handles"], seconds=4,
         result="malfind: 4 RWX regions in PID 1488; 2 API hooks in svchost; dlllist anomalies: 3.",
         findings=[
             {"sev": "critical", "title": "Executable memory injection (RWX)",
              "detail": "4 memory regions with RWX protections detected in PID 1488 - signature of injected code.",
              "from": "malfind"},
             {"sev": "high", "title": "API hooking detected",
              "detail": "2 user-mode hooks found in svchost (NTDLL API trampolines).",
              "from": "apihooks"},
             {"sev": "medium", "title": "DLL anomalies",
              "detail": "3 DLLs loaded with unusual base addresses or missing disk backing.",
              "from": "dlllist"},
         ]),
    dict(id=6, title="Kernel & Drivers",
         desc="List loaded modules and look for unsigned or disguised drivers.",
         plugins=["modules", "modscan", "driverscan", "ssdt"], seconds=3,
         result="214 kernel modules; 2 unsigned drivers flagged; SSDT inline hook detected at index 0x1C.",
         findings=[
             {"sev": "high", "title": "Unsigned kernel drivers",
              "detail": "2 loaded drivers are unsigned and missing from the vendor whitelist.",
              "from": "driverscan"},
             {"sev": "high", "title": "SSDT inline hook",
              "detail": "Inline hook detected in the System Service Descriptor Table at index 0x1C.",
              "from": "ssdt"},
         ]),
    dict(id=7, title="Registry & Artifacts",
         desc="Extract hives, persistence keys, recent documents and shellbags.",
         plugins=["hivelist", "printkey", "dumpregistry", "shellbags"], seconds=4,
         result="12 registry hives mapped; 5 autorun keys; shellbags timeline rebuilt (46 entries).",
         findings=[
             {"sev": "medium", "title": "Autorun persistence keys",
              "detail": "5 autorun entries in Run/RunOnce point to binaries under the Temp directory.",
              "from": "printkey"},
             {"sev": "low", "title": "Recent activity timeline",
              "detail": "46 shellbag entries rebuilt - user activity timeline available.",
              "from": "shellbags"},
         ],
         artifacts=[
             {"name": "SOFTWARE, SYSTEM, NTUSER (hives)", "kind": "Registry hives", "from": "Registry & Artifacts"},
         ]),
    dict(id=8, title="Memory Extraction",
         desc="Dump selected processes, files and registry data for deep review.",
         plugins=["memdump", "procdump", "dumpfiles", "dlllist"], seconds=5,
         result="Extracted 6 files, 2 full process dumps (PID 1488, 3401) and 4 registry hives to case folder.",
         findings=[
             {"sev": "info", "title": "Evidentiary artifacts extracted",
              "detail": "Process dumps, recovered files and registry hives preserved for further review.",
              "from": "dumpfiles / memdump"},
         ],
         artifacts=[
             {"name": "PID 1488 / PID 3401 full dumps", "kind": "Process dump", "from": "Memory Extraction"},
             {"name": "6 recovered files", "kind": "Files", "from": "Memory Extraction"},
         ]),
    dict(id=9, title="Reporting",
         desc="Synthesize a timeline and export the structured HTML report.",
         plugins=["timeliner", "report_generator"], seconds=2,
         result="Timeline synthesized (118 events); HTML report exported successfully.",
         findings=[
             {"sev": "info", "title": "Timeline synthesized",
              "detail": "118 events collated into a single review timeline.",
              "from": "timeliner"},
         ]),
]

SEV_COLORS = {
    "critical": "#f43f5e",
    "high": "#fb923c",
    "medium": "#facc15",
    "low": "#38bdf8",
    "info": "#8b9bb0",
}
SEV_LABEL = {
    "critical": "CRITICAL",
    "high": "HIGH",
    "medium": "MEDIUM",
    "low": "LOW",
    "info": "INFO",
}

def collect_findings(state):
    """Return (findings, artifacts) only from completed workflow stages."""
    steps = state.get("steps", {})
    findings, artifacts = [], []
    for s in WORKFLOW:
        if steps.get(str(s["id"]), {}).get("status") == "done":
            findings.extend(s.get("findings", []))
            artifacts.extend(s.get("artifacts", []))
    return findings, artifacts

def _verdict(findings):
    sevs = [f.get("sev", "info") for f in findings]
    if "critical" in sevs:
        return "CRITICAL", "Active infection indicators found - immediate investigation required", "#f43f5e"
    if "high" in sevs:
        return "HIGH", "Suspicious activity confirmed - prioritize detailed review", "#fb923c"
    if "medium" in sevs:
        return "MEDIUM", "Anomalies found - deeper review is advised", "#facc15"
    return "LOW", "No suspicious indicators - baseline observation", "#4adec5"

SEV_ORDER = ["critical", "high", "medium", "low", "info"]

def _insight(findings):
    """One plain-language line describing the single most important finding."""
    if not findings:
        return "Memory analysis is pending - run the workflow stages to scan the image."
    top = sorted(findings, key=lambda f: SEV_ORDER.index(f.get("sev", "info")))[0]
    sev = SEV_LABEL.get(top.get("sev", "info"))
    return f"Top concern: {top['title']} ({sev}) - {top.get('detail', '')}"

def _recommendation(findings):
    sevs = {f.get("sev") for f in findings}
    if "critical" in sevs or "high" in sevs:
        return ("Isolate the flagged processes, deep-scan the extracted dumps and "
                "cross-check the flagged endpoints before closing the case.")
    if "medium" in sevs:
        return "Review the flagged artifacts and continue monitoring for related activity."
    if "low" in sevs:
        return "No urgent action needed - keep the low-priority observations on file."
    return ""

# ----------------------------------------------------------------------------
# Escaping helper
# ----------------------------------------------------------------------------
def esc(t):
    return html.escape(t, quote=False)

# ----------------------------------------------------------------------------
# State persistence
# ----------------------------------------------------------------------------
def default_state():
    return {
        "version": 1,
        "case": {"name": "Case_2026-09-17", "analyst": "analyst", "image": "", "notes": ""},
        "steps": {},
    }

def load_state():
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            d = default_state()
            data.setdefault("case", d["case"])
            data.setdefault("steps", {})
            return data
    except Exception:
        pass
    return default_state()

def save_state(state):
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

# ----------------------------------------------------------------------------
# Theme
# ----------------------------------------------------------------------------
QSS = """
* { font-family: "Segoe UI", "Segoe UI Variable Text", sans-serif; font-size: 12px; color: #e7edf5; }
QMainWindow, QWidget#root { background-color: #0b0e14; }
QLabel#appName { font-size: 17px; font-weight: 700; color: #ffffff; }
QLabel#appTag  { font-size: 10px; color: #8b9bb0; }
QLabel#pageTitle { font-size: 22px; font-weight: 700; color: #ffffff; }
QLabel#pageSub  { font-size: 11px; color: #8b9bb0; }
QLabel#muted { color: #8b9bb0; }
QLabel#h3 { font-size: 14px; font-weight: 700; color: #ffffff; }
QLabel#h4 { font-size: 12px; font-weight: 600; color: #dbe4ee; }

QFrame#sidebar { background-color: #10141d; border-right: 1px solid #1e2736; }
QFrame#card { background-color: #151c28; border: 1px solid #232d3f; border-radius: 12px; }
QFrame#cardSoft { background-color: #121824; border: 1px solid #1d2738; border-radius: 10px; }
QFrame#stepCard { background-color: #141b27; border: 1px solid #243048; border-radius: 12px; }
QFrame#stepRunning { background-color: #16202c; border: 1px solid #2dd4bf; }
QFrame#stepDone { background-color: #131d1c; border: 1px solid #1f6f5c; }

QPushButton { border: none; border-radius: 8px; padding: 7px 14px; font-weight: 600; }
QPushButton#primary { background-color: #2dd4bf; color: #06221e; }
QPushButton#primary:hover { background-color: #4adec5; }
QPushButton#secondary { background-color: #1d2738; color: #cfe0f2; border: 1px solid #2c3a52; }
QPushButton#secondary:hover { background-color: #263349; }
QPushButton#ghost { background-color: transparent; color: #8b9bb0; }
QPushButton#ghost:hover { background-color: #182231; color: #e7edf5; }

QPushButton#sideBtn { text-align: left; border-radius: 9px; padding: 10px 14px; color: #9fb0c6; }
QPushButton#sideBtn:hover { background-color: #1a2434; color: #ffffff; }
QPushButton#sideBtn:checked { background-color: #1c2a3b; color: #2dd4bf; }
QPushButton#stepRun { background-color: #38bdf8; color: #06222f; }
QPushButton#stepRun:hover { background-color: #6ccbff; }
QPushButton#stepRun:disabled { background-color: #1d2738; color: #55637a; }

QLabel#chip { background-color: #1d2b3e; color: #8fb6d9; border: 1px solid #2a3a52;
              border-radius: 10px; padding: 2px 8px; font-size: 10px; }
QLabel#statusPillOk { background-color: #123a2f; color: #4adec5; border-radius: 9px;
                      padding: 2px 10px; font-size: 10px; font-weight: 700; }
QLabel#statusPillWait { background-color: #2b2414; color: #fb923c; border-radius: 9px;
                        padding: 2px 10px; font-size: 10px; font-weight: 700; }
QLabel#statusPillRun { background-color: #103148; color: #38bdf8; border-radius: 9px;
                       padding: 2px 10px; font-size: 10px; font-weight: 700; }
QLabel#resultBox { background-color: #101623; border-left: 3px solid #2dd4bf;
                   border-radius: 6px; padding: 8px; color: #a9bcd4; font-size: 11px; }
QLabel#badge { background-color: #2dd4bf; color: #06221e; border-radius: 12px;
               font-weight: 800; font-size: 12px; }

QProgressBar { background-color: #1a2231; border: none; border-radius: 4px; height: 7px; }
QProgressBar::chunk { background-color: #2dd4bf; border-radius: 4px; }

QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 9px; }
QScrollBar::handle:vertical { background: #2a3a52; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QTextBrowser, QPlainTextEdit { background-color: #0e141f; border: 1px solid #1e2736;
                               border-radius: 10px; padding: 6px; selection-background-color: #2dd4bf; }
QTextBrowser { font-size: 13px; }

QLineEdit { background-color: #0e141f; border: 1px solid #232f44; border-radius: 8px; padding: 8px 10px; }
QLineEdit:focus { border: 1px solid #2dd4bf; }

QFrame#statCard { background-color: #141b27; border: 1px solid #243048; border-radius: 12px; }
QLabel#statValue { font-size: 24px; font-weight: 800; color: #ffffff; }
QLabel#statLabel { font-size: 10px; color: #8b9bb0; }
QLabel#accentBar { background-color: #2dd4bf; }
QLabel#amberBar { background-color: #fb923c; }
QLabel#blueBar { background-color: #38bdf8; }
QLabel#violetBar { background-color: #a78bfa; }
QDialog { background-color: #10141d; }
"""

# ----------------------------------------------------------------------------
# Icon factory (vector-drawn glyphs)
# ----------------------------------------------------------------------------
def glyph_icon(shape, color="#2dd4bf", size=17):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(1.6)
    if shape == "dash":
        p.setPen(Qt.NoPen)
        d = QRectF(3, 3, size - 6, size - 6)
        for k in range(8):
            p.setBrush(QColor("#2dd4bf") if k % 2 == 0 else QColor("#38bdf8"))
            p.drawChord(d, k * 45, 24)
        p.setBrush(QColor(11, 14, 20))
        p.drawEllipse(d)
        p.setPen(pen)
        p.setBrush(QColor("#2dd4bf"))
        p.drawEllipse(QRectF(size / 2 - 1.5, size / 2 - 1.5, 3, 3))
    elif shape == "flow":
        p.drawEllipse(QRectF(2, 2, 5, 5))
        p.drawEllipse(QRectF(size - 7, size - 7, 5, 5))
        p.drawEllipse(QRectF(size - 7, 2, 5, 5))
        p.setPen(QPen(QColor(color), 1.4))
        p.drawLine(QPointF(6, 5), QPointF(size - 6, size - 6))
        p.drawLine(QPointF(6, 5), QPointF(size - 6, 5))
    elif shape == "doc":
        d = QRectF(4, 2, 9, size - 4)
        p.setPen(pen)
        p.setBrush(QColor(16, 20, 29))
        p.drawRoundedRect(d, 2, 2)
        p.setPen(QPen(QColor("#8b9bb0"), 1.2))
        for y in range(4, size - 3, 3):
            p.drawLine(QPointF(6, y), QPointF(9, y))
    elif shape == "report":
        p.setPen(pen)
        p.setBrush(QColor(16, 20, 29))
        p.drawRoundedRect(QRectF(2, 3, size - 4, size - 6), 2, 2)
        p.drawLine(QPointF(5, size - 6), QPointF(size - 5, size - 6))
        p.drawLine(QPointF(5, size - 9), QPointF(size - 5, size - 9))
        p.drawLine(QPointF(5, size - 12), QPointF(size - 12, size - 12))
    elif shape == "shield":
        # app icon: shield + check / magnifier motif
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#0f1b2b"))
        p.drawRoundedRect(QRectF(2, 2, size - 4, size - 4), 10, 10)
        p.setBrush(QColor("#1c2a3b"))
        p.drawEllipse(QRectF(size * 0.14, size * 0.14, size * 0.72, size * 0.72))
        p.setPen(QPen(QColor("#2dd4bf"), 1.8))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(size * 0.14, size * 0.14, size * 0.72, size * 0.72))
        p.setPen(QPen(QColor("#2dd4bf"), 2.2))
        p.drawLine(QPointF(size * 0.36, size * 0.5), QPointF(size * 0.46, size * 0.62))
        p.drawLine(QPointF(size * 0.46, size * 0.62), QPointF(size * 0.66, size * 0.38))
    p.end()
    return QIcon(pm)

# ----------------------------------------------------------------------------
# Shared UI helpers
# ----------------------------------------------------------------------------
def make_pill(text, kind):
    l = QLabel(text)
    l.setObjectName(f"statusPill{kind}")
    l.setAlignment(Qt.AlignCenter)
    return l

def make_chip(text):
    l = QLabel(text)
    l.setObjectName("chip")
    return l

def make_stat(value, label, emblem):
    card = QFrame()
    card.setObjectName("statCard")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(16, 14, 16, 14)
    lay.setSpacing(4)
    bar = QLabel()
    bar.setFixedHeight(4)
    bar.setObjectName({"teal": "accentBar", "amber": "amberBar",
                       "blue": "blueBar", "violet": "violetBar"}[emblem])
    lay.addWidget(bar)
    val = QLabel(str(value))
    val.setObjectName("statValue")
    lay.addWidget(val)
    lbl = QLabel(label)
    lbl.setObjectName("statLabel")
    lay.addWidget(lbl)
    return card

def section_title(text):
    l = QLabel(text)
    l.setObjectName("h3")
    return l

# ----------------------------------------------------------------------------
# StepCard - a workflow stage card
# ----------------------------------------------------------------------------
class StepCard(QFrame):
    def __init__(self, step):
        super().__init__()
        self.step = step
        self.parent_step_trigger = None
        self.setObjectName("stepCard")
        self.setMinimumHeight(104)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(10)
        badge = QLabel(str(step["id"]))
        badge.setObjectName("badge")
        badge.setFixedSize(24, 24)
        badge.setAlignment(Qt.AlignCenter)
        top.addWidget(badge)

        tcol = QVBoxLayout()
        tcol.setSpacing(1)
        title = QLabel(step["title"])
        title.setObjectName("h4")
        tcol.addWidget(title)
        desc = QLabel(step["desc"])
        desc.setObjectName("muted")
        desc.setWordWrap(True)
        tcol.addWidget(desc)
        top.addLayout(tcol, 1)

        self._pill = make_pill("QUEUED", "Wait")
        top.addWidget(self._pill)
        self._run = QPushButton("Run")
        self._run.setObjectName("stepRun")
        self._run.setFixedWidth(64)
        self._run.setCursor(Qt.PointingHandCursor)
        self._run.clicked.connect(self._on_run)
        top.addWidget(self._run)
        root.addLayout(top)

        chips = QHBoxLayout()
        chips.setSpacing(6)
        for name in step["plugins"]:
            chips.addWidget(make_chip(name))
        chips.addStretch(1)
        root.addLayout(chips)

        self._prog = QProgressBar()
        self._prog.setRange(0, 100)
        self._prog.setValue(0)
        self._prog.hide()
        root.addWidget(self._prog)

        self._result = QLabel("")
        self._result.setObjectName("resultBox")
        self._result.setWordWrap(True)
        self._result.hide()
        root.addWidget(self._result)

    def _on_run(self):
        if self.parent_step_trigger:
            self.parent_step_trigger(self.step["id"])

    def _pill_state(self, text, kind):
        self._pill.setText(text)
        self._pill.setObjectName(f"statusPill{kind}")
        self._pill.style().unpolish(self._pill)
        self._pill.style().polish(self._pill)

    def set_running(self):
        self.setObjectName("stepRunning")
        self._pill_state("RUNNING", "Run")
        self._run.setEnabled(False)
        self._prog.show()
        self._result.hide()
        self.style().unpolish(self)
        self.style().polish(self)

    def set_done(self, result):
        self.setObjectName("stepDone")
        self._pill_state("COMPLETED", "Ok")
        self._run.setText("Rerun")
        self._run.setEnabled(True)
        self._prog.hide()
        if result:
            self._result.setText(result)
            self._result.show()
        self.style().unpolish(self)
        self.style().polish(self)

    def set_queued(self, runnable=False):
        self.setObjectName("stepCard")
        self._pill_state("QUEUED", "Wait")
        self._run.setText("Run")
        self._run.setEnabled(runnable)
        self._prog.hide()
        self._result.hide()
        self.style().unpolish(self)
        self.style().polish(self)

    def set_progress(self, value):
        self._prog.setValue(value)

# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
NAV_ITEMS = [
    ("dash", "Dashboard", "dash"),
    ("flow", "Workflow", "flow"),
    ("report", "Report", "report"),
]

class Sidebar(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(224)
        self.nav_buttons = {}
        self.on_navigate = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 22, 14, 18)
        lay.setSpacing(6)

        brand = QHBoxLayout()
        mark = QLabel("M")
        mark.setFixedSize(34, 34)
        mark.setAlignment(Qt.AlignCenter)
        mark.setStyleSheet(
            "background-color:#111f2c; border:2px solid #2dd4bf; border-radius:10px;"
            "color:#2dd4bf; font-size:18px; font-weight:800;")
        brand.addWidget(mark)
        bc = QVBoxLayout()
        bc.setSpacing(0)
        t = QLabel("Memory Forensics")
        t.setObjectName("appName")
        bc.addWidget(t)
        tag = QLabel("VOLATILITY PLUGIN WORKFLOW")
        tag.setObjectName("appTag")
        bc.addWidget(tag)
        brand.addLayout(bc)
        brand.addStretch(1)
        lay.addLayout(brand)
        lay.addSpacing(18)

        for key, label, shape in NAV_ITEMS:
            b = QPushButton(f"  {label}")
            b.setObjectName("sideBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setIcon(glyph_icon(shape))
            b.setIconSize(QSize(16, 16))
            b.clicked.connect(lambda _=False, k=key, btn=b: self._nav(k, btn))
            self.nav_buttons[key] = b
            lay.addWidget(b)
        lay.addStretch(1)

        footer = QVBoxLayout()
        eng = QLabel("\u25cf  Engine: simulated")
        eng.setObjectName("appTag")
        footer.addWidget(eng)
        ver = QLabel(f"v{APP_VERSION} - runs locally")
        ver.setObjectName("appTag")
        footer.addWidget(ver)
        lay.addLayout(footer)

    def _nav(self, key, btn):
        for k, b in self.nav_buttons.items():
            b.setChecked(k == key)
        if self.on_navigate:
            self.on_navigate(key)

    def select(self, key):
        btn = self.nav_buttons.get(key)
        if btn:
            self._nav(key, btn)

# ----------------------------------------------------------------------------
# Dashboard page
# ----------------------------------------------------------------------------
class DashboardPage(QWidget):
    def __init__(self, on_run_all, on_open_report, on_open_docs):
        super().__init__()
        self.on_run_all = on_run_all
        self.on_open_report = on_open_report
        self.on_open_docs = on_open_docs

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        top = QHBoxLayout()
        tc = QVBoxLayout()
        tc.setSpacing(2)
        t = QLabel("Case Overview")
        t.setObjectName("pageTitle")
        tc.addWidget(t)
        s = QLabel("Memory image analysis pipeline - built for Volatility 3 workflows")
        s.setObjectName("pageSub")
        tc.addWidget(s)
        top.addLayout(tc)
        top.addStretch(1)
        self._warn = QLabel()
        self._warn.setWordWrap(True)
        top.addWidget(self._warn)
        outer.addLayout(top)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.st_done = make_stat(0, "STEPS COMPLETED", "teal")
        self.st_pending = make_stat(0, "STEPS PENDING", "amber")
        self.st_plugins = make_stat(0, "PLUGINS READY", "blue")
        self.st_docs = make_stat(0, "DOCUMENTS LOADED", "violet")
        for i, w in enumerate([self.st_done, self.st_pending, self.st_plugins, self.st_docs]):
            grid.addWidget(w, 0, i)
            grid.setColumnStretch(i, 1)
        outer.addLayout(grid)

        mid = QHBoxLayout()
        mid.setSpacing(16)

        prog_card = QFrame()
        prog_card.setObjectName("card")
        pl = QVBoxLayout(prog_card)
        pl.setContentsMargins(22, 20, 22, 20)
        pl.setSpacing(12)
        pl.addWidget(section_title("Workflow Progress"))
        self._bar = QProgressBar()
        self._bar.setRange(0, len(WORKFLOW))
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(10)
        pl.addWidget(self._bar)
        self._progLabel = QLabel("0 / 0 stages completed")
        self._progLabel.setObjectName("muted")
        pl.addWidget(self._progLabel)
        pl.addSpacing(4)

        acts = QHBoxLayout()
        bb = QPushButton("Run All Stages")
        bb.setObjectName("primary")
        bb.setCursor(Qt.PointingHandCursor)
        bb.clicked.connect(self.on_run_all)
        acts.addWidget(bb)
        bg = QPushButton("Generate Report")
        bg.setObjectName("secondary")
        bg.setCursor(Qt.PointingHandCursor)
        bg.clicked.connect(self.on_open_report)
        acts.addWidget(bg)
        bd = QPushButton("Open Docs Folder")
        bd.setObjectName("ghost")
        bd.setCursor(Qt.PointingHandCursor)
        bd.clicked.connect(self.on_open_docs)
        acts.addWidget(bd)
        acts.addStretch(1)
        pl.addLayout(acts)
        mid.addWidget(prog_card, 3)

        act_card = QFrame()
        act_card.setObjectName("card")
        al = QVBoxLayout(act_card)
        al.setContentsMargins(22, 20, 22, 20)
        al.addWidget(section_title("Recent Activity"))
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setPlaceholderText("No activity yet - run the workflow.")
        al.addWidget(self._log, 1)
        mid.addWidget(act_card, 2)
        outer.addLayout(mid, 1)

        self.refresh(load_state())

    def refresh(self, state):
        steps = state.get("steps", {})
        done = sum(1 for s in WORKFLOW if steps.get(str(s["id"]), {}).get("status") == "done")
        plugs = sum(len(s["plugins"]) for s in WORKFLOW)
        v = lambda w: w.layout().itemAt(1).widget()
        v(self.st_done).setText(str(done))
        v(self.st_pending).setText(str(len(WORKFLOW) - done))
        v(self.st_plugins).setText(str(plugs))
        v(self.st_docs).setText(str(len(DOC_ORDER)))
        self._bar.setValue(done)
        self._progLabel.setText(f"{done} / {len(WORKFLOW)} stages completed")

        det = self._detect_engine()
        if det:
            self._warn.setText(f"\u25cf  Volatility engine: {det}")
            self._warn.setStyleSheet("color:#4adec5; font-size:11px;")
        else:
            self._warn.setText("\u25cf  Engine: simulated analysis (vol3 not found)")
            self._warn.setStyleSheet("color:#fb923c; font-size:11px;")

        self._log.clear()
        entries = []
        for s in WORKFLOW:
            st = steps.get(str(s["id"]), {})
            if st.get("status") == "done":
                entries.append((st.get("ts", ""), s["title"]))
        entries.sort(key=lambda e: e[0], reverse=True)
        for ts, title in entries[:12]:
            self._log.appendPlainText(f"[{ts}] {title} completed")

    def _detect_engine(self):
        for name in ("vol3", "vol.py", "volatility3", "vol"):
            p = shutil.which(name)
            if p:
                return p
        for cand in (Path("C:/Volatility3/vol.py"), Path("C:/volatility3/vol.py")):
            if cand.exists():
                return str(cand)
        return None

# ----------------------------------------------------------------------------
# Workflow page
# ----------------------------------------------------------------------------
class WorkflowPage(QWidget):
    def __init__(self, state):
        super().__init__()
        self.state = state
        self.cards = {}
        self._running = False
        self._chain = []
        self._current = None
        self._elapsed = 0
        self._total = 1
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)

        top = QHBoxLayout()
        tc = QVBoxLayout()
        tc.setSpacing(2)
        t = QLabel("Volatility Plugin Workflow")
        t.setObjectName("pageTitle")
        tc.addWidget(t)
        s = QLabel("Execute the 9 forensic stages in order. Results feed the HTML report.")
        s.setObjectName("pageSub")
        tc.addWidget(s)
        top.addLayout(tc)
        top.addStretch(1)
        self._runall = QPushButton("Run All Stages")
        self._runall.setObjectName("primary")
        self._runall.setCursor(Qt.PointingHandCursor)
        self._runall.clicked.connect(self.run_all)
        top.addWidget(self._runall)
        self._reset = QPushButton("Reset")
        self._reset.setObjectName("ghost")
        self._reset.setCursor(Qt.PointingHandCursor)
        self._reset.clicked.connect(self.reset_all)
        top.addWidget(self._reset)
        outer.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        wrap = QWidget()
        wrap.setObjectName("root")
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(2, 2, 8, 2)
        wl.setSpacing(12)
        for step in WORKFLOW:
            card = StepCard(step)
            card.parent_step_trigger = self.run_step
            self.cards[step["id"]] = card
            wl.addWidget(card)
        wl.addStretch(1)
        scroll.setWidget(wrap)
        outer.addWidget(scroll, 1)

        self.sync_ui()

    def step_status(self, sid):
        return self.state.get("steps", {}).get(str(sid), {}).get("status", "queued")

    def sync_ui(self):
        prev_done = True
        for card in self.cards.values():
            st = self.step_status(card.step["id"])
            if st == "done":
                card.set_done(self.state["steps"].get(str(card.step["id"]), {}).get("result", ""))
                prev_done = True
            elif st == "running":
                card.set_running()
            else:
                card.set_queued(runnable=prev_done)
                prev_done = False

    def run_step(self, sid):
        if self._running or self.step_status(sid) == "done":
            return
        card = self.cards[sid]
        card.set_running()
        self._running = True
        self._current = (card, str(sid))
        self._elapsed = 0
        self._total = max(1, card.step["seconds"] * 20)
        self._timer.start()

    def _tick(self):
        if not self._current:
            return
        try:
            card, sid = self._current
            self._elapsed += 1
            card.set_progress(int(min(100, self._elapsed / self._total * 100)))
            if self._elapsed >= self._total:
                self._timer.stop()
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                self.state.setdefault("steps", {})[sid] = {
                    "status": "done", "result": card.step["result"], "ts": now,
                }
                save_state(self.state)
                card.set_done(card.step["result"])
                self._running = False
                self._current = None
                self.sync_ui()
                if self._chain:
                    nxt = self._chain.pop(0)
                    QTimer.singleShot(10, lambda: self.run_step(nxt))
        except Exception as e:
            # never let a per-step hiccup kill the app
            _log_crash("workflow tick", e)
            self._timer.stop()
            self._running = False
            self._current = None
            if self._chain:
                nxt = self._chain.pop(0)
                QTimer.singleShot(10, lambda: self.run_step(nxt))

    def run_all(self):
        if self._running:
            return
        pending = [s["id"] for s in WORKFLOW if self.step_status(s["id"]) != "done"]
        if not pending:
            QMessageBox.information(self, "Workflow",
                                    "All stages are already completed. Use Reset to start over.")
            return
        self._chain = pending
        QTimer.singleShot(10, lambda: self.run_step(self._chain.pop(0)))

    def reset_all(self):
        if self._running:
            return
        resp = QMessageBox.question(self, "Reset workflow",
                                    "Reset all stages to QUEUED? Completed results will be cleared.",
                                    QMessageBox.Yes | QMessageBox.No)
        if resp != QMessageBox.Yes:
            return
        self.state["steps"] = {}
        save_state(self.state)
        self.sync_ui()

# ----------------------------------------------------------------------------
# Report builder
# ----------------------------------------------------------------------------
def build_report_html(state):
    case = state.get("case", {})
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    steps = state.get("steps", {})
    done = [s for s in WORKFLOW if steps.get(str(s["id"]), {}).get("status") == "done"]

    def pill(status):
        ok = status == "done"
        return ('<span class="pill ok">COMPLETED</span>' if ok
                else '<span class="pill wait">QUEUED</span>')

    rows = []
    for s in WORKFLOW:
        st = steps.get(str(s["id"]), {})
        chips = "".join(f'<span class="chip">{p}</span>' for p in s["plugins"])
        rows.append(
            f"<tr><td class=\"num\">{s['id']}</td>"
            f"<td><b>{esc(s['title'])}</b><br><span class=\"muted\">{esc(s['desc'])}</span></td>"
            f"<td>{chips}</td>"
            f"<td>{pill(st.get('status', 'queued'))}</td>"
            f"<td class=\"small\">{esc(st.get('result', '—'))}</td></tr>")

    findings, artifacts = collect_findings(state)
    verdict, verdict_note, vcolor = _verdict(findings)
    sev_order = ["critical", "high", "medium", "low", "info"]
    counts = {k: sum(1 for f in findings if f.get("sev", "info") == k) for k in sev_order}
    total = len(findings)
    insight = _insight(findings)
    rec = _recommendation(findings)

    def sev_badge(sev):
        c = SEV_COLORS.get(sev, SEV_COLORS["info"])
        l = SEV_LABEL.get(sev, "INFO")
        return (f'<span class="sev" style="background:{c}22;color:{c};'
                f'border:1px solid {c}44;">{l}</span>')

    fn_rows = "".join(
        f'<tr style="border-left:4px solid {SEV_COLORS.get(f.get("sev", "info"))};">'
        f'<td>{sev_badge(f.get("sev", "info"))}</td>'
        f'<td><b>{esc(f.get("title", ""))}</b>'
        f'<div class="muted small2">{esc(f.get("detail", ""))}</div></td>'
        f'<td class="muted">{esc(f.get("from", ""))}</td></tr>'
        for f in sorted(findings, key=lambda x: sev_order.index(x.get("sev", "info"))))

    sev_cards = "".join(
        f'<div class="sevcard"><span class="dot" style="background:{SEV_COLORS[k]};"></span>'
        f'<span class="num">{counts[k]}</span><br><span class="mut">{SEV_LABEL[k]}</span></div>'
        for k in sev_order)

    if total:
        seg = "".join(
            f'<div style="width:{counts[k] / total * 100:.1f}%;background:{SEV_COLORS[k]};"></div>'
            for k in sev_order if counts[k])
        dist_bar = f'<div class="bar">{seg}</div>'
    else:
        dist_bar = ""

    if total:
        rec_block = f'<div class="rec">{esc(rec)}</div>' if rec else ""
        verdict_panel = (f'<div class="verdict" style="border-color:{vcolor};background:{vcolor}14;">'
                         f'<div class="vtag" style="color:{vcolor};">{verdict}</div>'
                         f'<div class="vnote">{esc(verdict_note)}</div>'
                         f'<div class="vcount muted">{total} indicator(s) across {len(done)} analyzed stage(s)</div>'
                         f'<div class="vinsight">{esc(insight)}</div>'
                         f'</div>')
        findings_block = (f'<table><thead><tr><th>Severity</th><th>Indicator</th><th>Source</th></tr></thead>'
                          f'<tbody>{fn_rows}</tbody></table>{dist_bar}{rec_block}')
    else:
        verdict_panel = (f'<div class="verdict" style="border-color:#3a4658;background:#3a465814;">'
                         f'<div class="vtag" style="color:#8b9bb0;">ANALYSIS PENDING</div>'
                         f'<div class="vnote">Run the workflow stages to populate memory analysis findings.</div>'
                         f'<div class="vcount muted">{len(done)} / {len(WORKFLOW)} stages completed</div>'
                         f'</div>')
        findings_block = ('<div class="nothing">No indicators yet - complete the workflow '
                          'to analyze the memory image.</div>')

    if artifacts:
        art_rows = "".join(
            f"<tr><td><b>{esc(a.get('name', ''))}</b></td>"
            f"<td><span class='chip'>{esc(a.get('kind', ''))}</span></td>"
            f"<td class='muted'>{esc(a.get('from', ''))}</td></tr>"
            for a in artifacts)
        art_block = ('<table><thead><tr><th>Artifact</th><th>Kind</th><th>Recovered by</th></tr></thead>'
                     f'<tbody>{art_rows}</tbody></table>')
    else:
        art_block = '<div class="nothing">No artifacts recovered yet.</div>'

    case_fields = "".join(
        f'<div class="field"><span class="muted">{esc(k.title())}</span><b>{esc(v or "—")}</b></div>'
        for k, v in case.items())

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Memory Forensics Report - {esc(case.get('name', ''))}</title>
<style>
  :root {{ --bg:#0b0e14; --card:#141b27; --line:#243048; --txt:#e7edf5;
          --mut:#8b9bb0; --accent:#2dd4bf; --accent2:#38bdf8; --warn:#fb923c; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--txt);
         font-family:Segoe UI,Arial,sans-serif; font-size:14px; line-height:1.6; }}
  .wrap {{ max-width:1020px; margin:0 auto; padding:36px 28px 60px; }}
  header.hero {{ background:linear-gradient(135deg,#101c2c 0%,#0e1826 60%,#0b0e14 100%);
                border:1px solid var(--line); border-radius:16px; padding:30px; margin-bottom:22px; }}
  .kicker {{ color:var(--accent); font-size:11px; letter-spacing:2px; font-weight:700; }}
  h1 {{ margin:6px 0 4px; font-size:28px; }}
  .sub {{ color:var(--mut); }}
  .badge {{ display:inline-block; background:#123a2f; color:#4adec5; border-radius:10px;
            padding:3px 12px; font-size:11px; font-weight:700; }}
  h2 {{ color:var(--accent); border-bottom:1px solid var(--line); padding-bottom:6px;
        margin:36px 0 12px; font-size:19px; }}
  table {{ width:100%; border-collapse:collapse; background:var(--card);
          border:1px solid var(--line); border-radius:12px; overflow:hidden; }}
  th {{ background:#1d2738; color:#9fb0c6; text-align:left; padding:11px 12px;
       font-size:11px; letter-spacing:1px; text-transform:uppercase; }}
  td {{ padding:12px; border-top:1px solid #1d2738; vertical-align:top; }}
  td.num {{ color:var(--accent2); font-weight:800; width:30px; }}
  .chip {{ display:inline-block; background:#1d2b3e; color:#8fb6d9; border:1px solid #2a3a52;
          border-radius:10px; padding:2px 8px; font-size:11px; margin:1px 2px 1px 0; }}
  .pill {{ display:inline-block; border-radius:9px; padding:2px 10px; font-size:10px; font-weight:700; }}
  .pill.ok {{ background:#123a2f; color:#4adec5; }}
  .pill.wait {{ background:#2b2414; color:#fb923c; }}
  .muted {{ color:var(--mut); font-size:12px; }}
  .small {{ font-size:12px; color:#a9bcd4; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; }}
  .field {{ background:var(--card); border:1px solid var(--line); border-radius:10px;
           padding:12px 14px; }}
  .field .muted {{ display:block; font-size:10px; text-transform:uppercase; letter-spacing:1px; }}
  pre, code {{ background:#0d1320; color:#a9c9e2; border-radius:6px; }}
  pre {{ padding:12px; overflow:auto; }}
  code {{ padding:1px 5px; }}
  blockquote {{ border-left:3px solid var(--warn); margin:8px 0; padding:2px 14px; color:#e2b48f; }}
  a {{ color:var(--accent2); }}
  .verdict {{ border:1px solid; border-radius:14px; padding:18px 22px; margin:4px 0 18px; }}
  .vtag {{ font-size:13px; letter-spacing:2px; font-weight:800; }}
  .vnote {{ font-size:15px; font-weight:600; margin-top:4px; }}
  .vcount {{ font-size:11px; margin-top:6px; }}
  .vinsight {{ font-size:13px; margin-top:10px; color:var(--accent2); background:#0e141f;
              border-radius:8px; padding:8px 12px; }}
  .rec {{ font-size:13px; margin-top:10px; color:#9fe8d0; background:#101a14;
         border:1px solid #1f6f5c; border-radius:8px; padding:8px 12px; }}
  .sevgrid {{ display:grid; grid-template-columns:repeat(5,1fr); gap:10px; margin-bottom:16px; }}
  .sevcard {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:13px 14px; }}
  .sevcard .num {{ font-size:25px; font-weight:800; line-height:1.2; }}
  .sevcard .dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:8px; }}
  .mut {{ color:var(--mut); font-size:10px; letter-spacing:1px; }}
  .bar {{ display:flex; height:12px; border-radius:6px; overflow:hidden; margin-top:10px;
          background:#141b27; border:1px solid var(--line); }}
  .bar div {{ height:100%; }}
  .sev {{ display:inline-block; font-size:10px; font-weight:800; padding:2px 9px;
          border-radius:9px; letter-spacing:1px; }}
  .small2 {{ font-size:12px; margin-top:4px; }}
  .nothing {{ background:var(--card); border:1px dashed var(--line); border-radius:12px;
              padding:20px; text-align:center; color:var(--mut); }}
  footer {{ margin-top:44px; color:var(--mut); font-size:11px; text-align:center; }}
</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <div class="kicker">MEMORY FORENSICS ANALYZER</div>
    <h1>Investigation Report</h1>
    <div class="sub">Volatility Plugin Workflow - generated {esc(now)}</div>
    <span class="badge">{len(done)} / {len(WORKFLOW)} stages completed</span>
  </header>

  <h2>Case Metadata</h2>
  <div class="grid">{case_fields}</div>

  <h2>Memory Analysis Findings</h2>
  {verdict_panel}
  <div class="sevgrid">{sev_cards}</div>
  {findings_block}

  <h2>Extracted Artifacts</h2>
  {art_block}

  <h2>Workflow Results</h2>
  <table>
    <thead><tr><th>#</th><th>Stage</th><th>Plugins</th><th>Status</th><th>Result</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>

  <footer>Generated locally by Memory Forensics Analyzer v{APP_VERSION} - {esc(now)}</footer>
</div>
</body>
</html>"""

# ----------------------------------------------------------------------------
# Report page
# ----------------------------------------------------------------------------
class ReportPage(QWidget):
    def __init__(self, state):
        super().__init__()
        self.state = state
        self._last_html = ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)

        top = QHBoxLayout()
        tc = QVBoxLayout()
        tc.setSpacing(2)
        t = QLabel("Analysis Report")
        t.setObjectName("pageTitle")
        tc.addWidget(t)
        s = QLabel("Generate a self-contained HTML report of the investigation.")
        s.setObjectName("pageSub")
        tc.addWidget(s)
        top.addLayout(tc)
        top.addStretch(1)
        gen = QPushButton("Refresh Preview")
        gen.setObjectName("secondary")
        gen.setCursor(Qt.PointingHandCursor)
        gen.clicked.connect(self.refresh_preview)
        top.addWidget(gen)
        self.dl_btn = QPushButton("Download HTML Report")
        self.dl_btn.setObjectName("primary")
        self.dl_btn.setCursor(Qt.PointingHandCursor)
        self.dl_btn.clicked.connect(self.download)
        top.addWidget(self.dl_btn)
        outer.addLayout(top)

        form_card = QFrame()
        form_card.setObjectName("cardSoft")
        fl = QGridLayout(form_card)
        fl.setContentsMargins(18, 14, 18, 14)
        fl.setHorizontalSpacing(12)
        fl.setVerticalSpacing(8)
        self._name = QLineEdit()
        self._name.setPlaceholderText("Investigation case name")
        self._analyst = QLineEdit()
        self._analyst.setPlaceholderText("Analyst")
        self._image = QLineEdit()
        self._image.setPlaceholderText("e.g. case_sample.raw (optional)")
        self._notes = QLineEdit()
        self._notes.setPlaceholderText("Optional case notes")
        fl.addWidget(QLabel("Case name"), 0, 0)
        fl.addWidget(self._name, 0, 1)
        fl.addWidget(QLabel("Analyst"), 0, 2)
        fl.addWidget(self._analyst, 0, 3)
        fl.addWidget(QLabel("Image file"), 1, 0)
        fl.addWidget(self._image, 1, 1, 1, 3)
        fl.addWidget(QLabel("Notes"), 2, 0)
        fl.addWidget(self._notes, 2, 1, 1, 3)
        fl.setColumnStretch(1, 1)
        fl.setColumnStretch(3, 1)
        outer.addWidget(form_card)

        preview = QFrame()
        preview.setObjectName("card")
        pl = QVBoxLayout(preview)
        pl.setContentsMargins(16, 16, 16, 16)
        pl.addWidget(section_title("Preview"))
        self._viewer = QTextBrowser()
        pl.addWidget(self._viewer)
        outer.addWidget(preview, 1)

        self._pull_metadata()
        self.refresh_preview()

    def _pull_metadata(self):
        case = self.state.get("case", {})
        self._name.setText(case.get("name", ""))
        self._analyst.setText(case.get("analyst", ""))
        self._image.setText(case.get("image", ""))
        self._notes.setText(case.get("notes", ""))

    def _push_metadata(self):
        self.state["case"] = {
            "name": self._name.text().strip(),
            "analyst": self._analyst.text().strip(),
            "image": self._image.text().strip(),
            "notes": self._notes.text().strip(),
        }
        save_state(self.state)

    def refresh_preview(self):
        self._push_metadata()
        self.state = load_state()
        self._last_html = build_report_html(self.state)
        self._viewer.setHtml(self._last_html)
        QTimer.singleShot(120, lambda: self._viewer.verticalScrollBar().setValue(0))

    def download(self):
        self._push_metadata()
        self.state = load_state()
        self._last_html = build_report_html(self.state)
        default = str(DOCS_DIR.parent /
                      f"Memory_Forensics_Report_{datetime.date.today().isoformat()}.html")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save HTML Report", default, "HTML files (*.html)")
        if not path:
            return
        try:
            Path(path).write_text(self._last_html, encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))
            return
        box = QMessageBox(self)
        box.setWindowTitle("Report exported")
        box.setText(f"HTML report saved to:\n{path}\n\nOpen it in the browser?")
        box.setStandardButtons(QMessageBox.Open | QMessageBox.Close)
        if box.exec() == QMessageBox.Open:
            webbrowser.open(Path(path).as_uri())

# ----------------------------------------------------------------------------
# Main window
# ----------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} - Volatility Plugin Workflow")
        self.resize(1240, 780)
        self.setMinimumSize(1020, 660)
        self.state = load_state()

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        lay = QHBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.on_navigate = self.navigate
        lay.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)

        self.dash = DashboardPage(self.run_all, self.goto_report, self.open_docs_folder)
        self.flow = WorkflowPage(self.state)
        self.report = ReportPage(self.state)
        for pg in (self.dash, self.flow, self.report):
            self.stack.addWidget(pg)

        self.sidebar.select("dash")

    def navigate(self, key):
        order = ["dash", "flow", "report"]
        self.stack.setCurrentIndex(order.index(key))
        if key == "dash":
            self.dash.refresh(load_state())
        if key == "report":
            self.report.state = load_state()
            self.report._pull_metadata()
            self.report.refresh_preview()

    def run_all(self):
        self.navigate("flow")
        self.flow.run_all()

    def goto_report(self):
        self.navigate("report")

    def open_docs_folder(self):
        try:
            os.startfile(DOCS_DIR)  # noqa: windows only
        except Exception:
            QMessageBox.information(self, "Docs folder", str(DOCS_DIR))

# ----------------------------------------------------------------------------
# Crash logging & self-test hook
# ----------------------------------------------------------------------------
_CRASH_LOG = None

def _log_crash(where, exc):
    try:
        if _CRASH_LOG is not None:
            _CRASH_LOG.write("\n[%s] %s: %s\n" % (
                datetime.datetime.now().isoformat(), where, exc))
            _CRASH_LOG.flush()
    except Exception:
        pass

def _install_crash_logging():
    """Write unhandled exceptions and hard faults (segfault) to crash.log."""
    global _CRASH_LOG
    try:
        path = APP_DIR / "crash.log"
        _CRASH_LOG = open(path, "a", encoding="utf-8", buffering=1)
        _CRASH_LOG.write("\n=== session %s ===\n" % datetime.datetime.now().isoformat())
        _CRASH_LOG.flush()
        import faulthandler
        faulthandler.enable(_CRASH_LOG)
    except Exception:
        pass

    def hook(t, v, tb):
        try:
            if _CRASH_LOG is not None:
                import traceback
                _CRASH_LOG.write("\n[unhandled exception]\n")
                traceback.print_exception(t, v, tb, file=_CRASH_LOG)
                _CRASH_LOG.flush()
        except Exception:
            pass
        sys.__excepthook__(t, v, tb)

    sys.excepthook = hook

def _autoscan(win, logpath):
    """Self-test: run the full workflow automatically and log progress."""
    log = open(logpath, "a", encoding="utf-8", buffering=1)
    log.write("autoscan start %s\n" % datetime.datetime.now().isoformat())
    win.sidebar.select("flow")
    app = QApplication.instance()

    def done_count():
        return sum(1 for s in WORKFLOW if win.flow.step_status(s["id"]) == "done")

    def check():
        if win.flow._running or win.flow._chain:
            QTimer.singleShot(1500, check)
            return
        log.write("scan finished - done=%d/9\n" % done_count())
        log.flush()
        QTimer.singleShot(400, app.quit)

    QTimer.singleShot(600, win.flow.run_all)
    QTimer.singleShot(2500, check)

# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")
    app.setWindowIcon(glyph_icon("shield", size=128))

    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "MemoryForensicsAnalyzer.1.0")
        except Exception:
            pass

    app.setStyleSheet(QSS)
    _install_crash_logging()
    save_state(load_state())  # seed state file

    win = MainWindow()
    win.show()

    self_test = os.environ.get("MF_AUTOSCAN_LOG")
    if self_test:
        QTimer.singleShot(1200, lambda: _autoscan(win, self_test))

    sys.exit(app.exec())

if __name__ == "__main__":
    main()