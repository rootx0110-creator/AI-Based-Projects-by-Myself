# Project Memory

## Conventions
- Log format: `[ISO8601] [LEVEL] [component] message`
- Error codes: E1xxx = network, E2xxx = auth, E3xxx = config
- Files: snake_case.py, PascalCase classes, UPPER_SNAKE constants

## Design Decisions (ADR)

### ADR-001: Python + CustomTkinter over Electron
**Context:** Need a lightweight .exe < 30 MB.
**Decision:** Python 3.11 + PyInstaller.
**Consequences:** Fast dev, small binary; requires Python bundling.

### ADR-002: asyncio for proxy core
**Context:** Thousands of concurrent connections.
**Decision:** asyncio on a dedicated thread, not threads-per-connection.
**Consequences:** High scalability; GUI must never touch loop directly.

## Constants
| Name              | Value    |
|-------------------|----------|
| DEFAULT_HTTP_PORT | 8080     |
| DEFAULT_SOCKS_PORT| 1080     |
| BUFFER_SIZE       | 65536    |
| CONNECT_TIMEOUT   | 10 s     |

## Gotchas
- PyInstaller needs `--hidden-import=encodings.idna`
- Windows Firewall prompts on first bind — document in README
- `asyncio.run()` cannot be called twice → use a persistent loop