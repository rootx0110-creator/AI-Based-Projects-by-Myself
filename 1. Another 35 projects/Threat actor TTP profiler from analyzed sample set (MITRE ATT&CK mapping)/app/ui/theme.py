"""UI theme constants for the TTP profiler application."""

BG = "#0b1220"            # application background
BG_2 = "#0f172a"          # panels
SIDEBAR = "#0d1526"       # sidebar background
SIDEBAR_ACTIVE = "#1d4ed8"
FRAME = "#14203a"         # frames / cards
FRAME_2 = "#1a2745"       # nested frames
BORDER = "#233252"
TEXT = "#e2e8f0"
TEXT_MUTED = "#8ea0c0"
ACCENT = "#2563eb"
ACCENT_HOVER = "#3b82f6"
GOOD = "#22c55e"
WARN = "#f59e0b"
BAD = "#ef4444"
HEAT = "#f97316"

FONT = "Segoe UI"
FONT_MONO = "Cascadia Mono"

PADDING = 20
SIDEBAR_WIDTH = 264

# ---------------------------------------------------------------------------
# Type scale — single source of truth for every font size in the UI.
# CustomTkinter does not follow Windows display scaling for explicit fonts,
# so sizes were previously hardcoded at 10-11px and felt cramped.
# Bump SCALE if text feels small on a given display.
# ---------------------------------------------------------------------------
SCALE = 1.15


def _pt(n: int) -> int:
    return max(9, round(n * SCALE))


FS_H1 = _pt(20)        # page titles
FS_H2 = _pt(15)        # card titles, section heads, actor names
FS_BODY = _pt(13)      # default body text, buttons
FS_SMALL = _pt(12)     # secondary text, field labels
FS_TINY = _pt(11)      # hints, footnotes, meta rows
FS_KPI = _pt(30)       # dashboard KPI numbers
FS_MONO = _pt(12)      # monospace detail text
FS_MONO_SM = _pt(12)   # monospace table cells / evidence
