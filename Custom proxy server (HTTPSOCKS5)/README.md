# Custom Proxy Server

A local **HTTP + HTTPS (CONNECT) + SOCKS5** forward proxy for Windows with an
eye-catchy desktop GUI. One window shows live traffic, throughput and logs;
Settings lets you chain through an upstream proxy, require client
authentication, and more. Ships as a single portable `.exe` — no install,
no telemetry.

![tabs](https://img.shields.io/badge/tabs-dashboard%20·%20connections%20·%20log%20·%20settings-blue)

## Quick start

```bash
# 1) create venv and install dependencies
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 2) run from source
.venv\Scripts\python main.py

# 3) build the .exe
build_exe.bat        # -> dist\CustomProxyServer.exe
```

> **Windows Firewall** will prompt the first time you bind a port — click
> *Allow access*. For *LAN* binding this is required so other devices can reach you.

## Using the proxy

| App setting | Value |
|---|---|
| HTTP proxy | `127.0.0.1:8080` |
| SOCKS5 proxy | `127.0.0.1:1080` |

- **Windows:** Settings → Network → Proxy → Manual proxy setup
- **Browsers:** extensions like FoxyProxy or switchyomega
- **CLI tools:** `curl -x http://127.0.0.1:8080 https://example.com`
  or `curl --socks5 127.0.0.1:1080 https://example.com`

## Features

- **HTTP/1.1 proxying** — absolute-URI requests + `CONNECT` tunneling (TLS is
  end-to-end; the proxy never sees decrypted traffic)
- **SOCKS5** (RFC 1928) — IPv4/IPv6/domain targets, CONNECT command
- **Optional client auth** — Basic auth for HTTP, username/password (RFC 1929)
  for SOCKS5
- **Upstream chaining** — route through another HTTP CONNECT or SOCKS5 proxy,
  with optional upstream credentials
- **Live dashboard** — requests, active connections, transferred bytes, errors,
  download/upload rates and a 90-second throughput chart
- **Connection list + activity log** — every request logged with stable error
  codes (`E1xxx` network, `E2xxx` auth, `E3xxx` config); rotating log file in
  `logs/proxy.log`
- **Pause/resume** — refuse new requests without losing your settings
- **LAN binding** — share the proxy with other devices on your network
- **Settings persist** to `config.json` next to the `.exe`

## Configuration

All settings live in the GUI; `config.json` is written next to the executable
(or project root when running from source). Delete the file to reset defaults.

## Development notes

- Python 3.11+ (tested on 3.14), CustomTkinter for the UI, asyncio core on a
  dedicated thread (ADR-002 in `deepseek_markdown_20260912_cf526a.md`)
- `make_icon.py` regenerates `assets/icon.ico` (Pillow)
- PyInstaller needs `--hidden-import=encodings.idna` (already in the spec)

## Troubleshooting

| Symptom | Fix |
|---|---|
| `E3002 bind failed` on start | Port already in use — change HTTP/SOCKS port in Settings |
| Firewall prompt every start | Allow on **private networks**, or add an inbound rule for the `.exe` |
| Browser shows 407 | Proxy auth is enabled — enter the credentials set in Settings |
| `E1003` in the log | DNS failure for the target host |
