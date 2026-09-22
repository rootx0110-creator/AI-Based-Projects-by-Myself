# Architecture — Custom Subnet Calculator & VLSM Planner

## 1. Overview

A local desktop application (Windows `.exe`) for IP subnetting:

1. **Custom Subnet Calculator** — given an IP address and a prefix
   (`/1` .. `/32`), derive the network address, broadcast address, usable
   host ranges, subnet mask, wildcard mask, class information, borrow bits,
   subnets-per classful-block, binary representation and a visual 32-bit map.
   Also supports reverse modes: "pick number of subnets" or "hosts per
   subnet" to derive the prefix, and lists all derived subnets in a table.

2. **VLSM Planner** — given a base network and a list of named segments with
   required usable-host counts, allocate the address space with
   Variable-Length Subnet Masking (largest demand first), producing per-segment
   block sizes, prefixes, network/first/last/broadcast addresses, masks and
   an address-space utilization metric.

3. **HTML Reporting** — export any calculation (subnet, derived-subnet list,
   VLSM plan, or a combined report) as a self-contained, styled,
   print-friendly HTML document.

Everything runs locally; there is no network access and no telemetry.

## 2. Runtime and packaging

- Language/runtime: **Python 3.14** (standard library only in `app/`, plus
  Pillow at build time to generate the application icon).
- GUI toolkit: **Tkinter / ttk (Tk 9.0)** — ships with CPython on Windows.
- Packaging: **PyInstaller 6.22.3**, `--onefile --windowed`, producing a
  single portable executable. No third-party runtime dependencies inside the
  bundle.

## 3. Module layout

```
project root/
├── main.py               # entry point; bootstraps the GUI
├── app/
│   ├── core.py           # pure networking logic (IP crunches + VLSM engine)
│   ├── report.py         # HTML report generators
│   ├── theme.py          # design tokens: colors, fonts, font sizes
│   ├── widgets.py        # reusable styled widgets (cards, labels, buttons)
│   ├── pages.py          # the three tab panes (calculator / VLSM / reports)
│   └── gui.py            # MainWindow: header, notebook, status bar, settings
├── tests/
│   └── test_core.py      # unittest suite for app/core.py
├── assets/               # build-time generated app icon
├── architecture.md
├── state.md
├── memory.md
├── todo.txt
└── readme.txt
```

## 4. Component responsibilities

### 4.1 `app/core.py` — pure logic (no GUI dependencies)

- `ip_to_int(str) -> int`, `int_to_ip(int) -> str`, IP validation.
- `cycle_class(int) -> dict` — A/B/C/D/E class, default mask, host bits.
- `calculate_subnet(ip_or_int, prefix) -> dict` — full numeric+string details
  for one subnet:
  - subnet mask decimal + binary, wildcard mask
  - network, broadcast, first usable, last usable
  - total addresses, usable hosts (RFC 3021 handling for /31 and /32)
  - class, borrowed bits, subnets per classful block
- `prefix_from_subnets(n) / prefix_from_hosts(n)` — reverse modes.
- `derive_subnets(base_network, prefix) -> list[dict]` — list all subnets of a
  fixed prefix (capped for very large counts).
- `vlsm_plan(base_network, prefix, segments) -> VlsmResult` — the VLSM engine:

  1. normalize the base to its network address;
  2. block size per segment = `next_power_of_two(required_hosts + 2)`
     (network + broadcast reserved);
  3. sort segments by required hosts, descending (largest demand first);
  4. allocate blocks contiguously from the base network;
  5. mark the plan as overflowing with the deficit listed when demand
     exceeds the base capacity.

- `VlsmSegment` / `VlsmResult` — small dataclasses with an `.to_dict()`
  for JSON persistence and reporting.

Property-based invariants are unit tested (see §8).

### 4.2 `app/report.py` — HTML generation

- `subnet_report_payload(subnet, extra=None) -> dict`
- `vlsm_report_payload(plan) -> dict`
- `render_html(payload) -> str` — single self-contained document:
  - embedded CSS with `@media print` rules;
  - header with title, generated timestamp, app version, page count;
  - summary "metric cards";
  - subnet detail table incl. binary notation;
  - derived-subnet or VLSM tables with zebra striping + color-coded status;
  - footer with tool identity.
- No templates files — everything is triple-quoted f-string methods so the
  one-file executable stays self-contained.

### 4.3 `app/theme.py` — design tokens

Central source for the visual language (a light, professional palette —
planner uses deep navy `#0F172A` only for the *header*, never as a full
background; the user-facing background is a soft blue-grey):

| Token               | Value      | Use                                |
|---------------------|------------|------------------------------------|
| `BG`                | `#EAF0F6`  | window background                  |
| `PANEL` / card      | `#FFFFFF`  | cards, table areas                 |
| `INK`               | `#0F172A`  | primary text                       |
| `MUTED`             | `#5B6B7B`  | secondary text                     |
| `ACCENT` / primary  | `#1D4ED8`  | buttons, active tabs, links        |
| `ACCENT_HOVER`      | `#1E40AF`  | button hover                       |
| `TEAL`              | `#0F766E`  | VLSM accent, success states        |
| `WARN`              | `#B45309`  | warnings (overflow, /31, /32)      |
| `ZEBRA`             | `#F4F8FC`  | alternating table row colour       |
| `GRID`              | `#D9E2EC`  | borders / separators               |

Fonts: `Segoe UI` (primary) with `Consolas` for IP/binary displays. Sizing
is defined once in `theme.py` so all widgets share it.

### 4.4 `app/widgets.py` — styled primitives

- `Card(container, title, icon_hint=None)` — white rounded-feel panel with a
  muted header strip.
- `Metric(label, value, accent)` — label/value pair for the result grid.
- `SectionTitle`, `SecondaryButton`, `PrimaryButton` — consistent composables
  built on ttk with normal/bold font and hover behavior.
- `ResultTable` — a `ttk.Treeview` wrapper that applies the zebra striping,
  header styling, column sizing, alternating strut columns (for printable
  reports) … no, struts only, everything else is plain Treeview styling.

### 4.5 `app/pages.py` — the three tabs

- `SubnetPage`:
  - masks entry (dotted mask ⇔ prefix ⇔ hosts-per-subnet ⇔ subnets) bound to
    one canonical `prefix` value so any of the four lenses stays in sync;
  - **Calculate** button → `app/core.calculate_subnet`; result rendered in a
    Metric grid + a color-coded 32-bit canvas map (network bits vs host bits);
  - derived-subnet table (all subnets for the resolved prefix, capped at 256
    rows with an on-screen note; the report can include the full list);
  - "Add to report" silent flag auto-tracks this as the current subnet.
- `VlsmPage`:
  - base network + prefix inputs; live capacity read-out;
  - segment editor: name + required hosts grid with add/remove/move rows,
    sample-data loader, import/export JSON;
  - **Allocate (VLSM)** button → plans via `app/core.vlsm_plan`; results in an
    `ResultTable`; overflow warnings surfaced in the status strip;
  - utilization bar (used address space / base capacity).
- `ReportPage`:
  - preview of the last calculated objects;
  - **Export HTML** (file chooser → writes self-contained HTML),
  - **Export Combined Report** (subnet + VLSM in one document),
  - **Open in browser** helper, and a list of previously exported reports.

### 4.6 `app/gui.py` — shell

- header banner (app icon, name, version, theme accent),
- `ttk.Notebook` with the three pages,
- status bar (last action, warnings, export path),
- persistence in `~/.subnetplanner/settings.json` (window geometry, last tab,
  last-used inputs), tolerating corrupt/missing settings.

## 5. Data flow

```
             +----------------- core.py (pure, tested) ------------------+
 User input ─►  validate/parse ─► calculate_subnet / vlsm_plan           │
 Bookkeeping: current_subnet, current_plan held by MainWindow            │
             +----------------- report.py -------------------------------+
  current_subnet/plan ─► payload ─► render_html(...) ─► .html on disk    │
```

- The GUI never computes subnet math; it only calls `core.py` and formats
  results. This keeps logic unit-testable without a display.
- `report.py` receives plain dicts/dataclasses, so reports can be generated
  from the CLI or tests too.

## 6. Error handling

- `core.py` raises `ValueError` for any malformed IP/mask/prefix and an
  `OverflowError`-style `ValueError` subclass `PlanOverflowError` when the
  base network cannot host the VLSM demand; callers catch and display a
  `WARN`-colored status message rather than tracebacks.
- GUI dialogs wrap input parsing; invalid digits are rejected at the
  keystroke level where possible.

## 7. Build pipeline

```
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --icon assets/app.ico --name SubnetPlanner main.py
```

See `readme.txt`/`memory.md` for the exact commands and `state.md` for build
status.

## 8. Testing strategy

- `tests/test_core.py` — `unittest`, runs headless:
  - round-trips ip⇄int, valid/invalid IP and mask parsing;
  - golden subnet scenarios (e.g. `192.168.1.5/26`,
    `10.1.2.3/8`, `172.16.0.1/12`, `/31`, `/32`);
  - reverse modes agree with forward prefixes;
  - VLSM textbook case and overflow case;
  - derived-subnet table breadth matches `2^(32-prefix)`.
- GUI smoke test: instantiate `MainWindow`, force `update_idletasks`,
  destroy — run once during CI to prove imports/theme/ttk wiring.

## 9. Security & privacy

- No network calls; all input/output local.
- Report HTML is generated with element escaping for user-entered segment
  names and addresses (no HTML injection via inputs).
- Readme instructs that IP details in saved reports may be network-sensitive
  information — export to trusted locations only.

## 10. Versioning

Semantic versioning on the app constant `APP_VERSION` in `main.py`.
This document describes the initial 1.0 architecture.