State
=====

Current snapshot of the VPN Tunnel Builder application state and the
invariants the system preserves while running.

1. Persisted state
------------------
Stored as JSON at:
  %LOCALAPPDATA%\VPNTunnelBuilder\state.json
(configurable under Settings -> data folder)

Shape:

  {
    "server": {
      "interface_name": "wg0",
      "listen_port": 51820,
      "subnet": "10.0.0.0/24",
      "server_address": "10.0.0.1",
      "endpoint_host": "",           # public IP/hostname peers use to reach server
      "dns": "1.1.1.1",
      "mtu": 1420,
      "private_key": "base64...",    # empty until generated/config set
      "public_key": "base64...",
      "created_at": "ISO-8601",
      "updated_at": "ISO-8601"
    },
    "peers": [
      {
        "id": "uuid",
        "name": "laptop",
        "ip": "10.0.0.2",
        "allowed_ips": "10.0.0.2/32",
        "keepalive": 25,
        "private_key": "base64...",
        "public_key": "base64...",
        "created_at": "ISO-8601",
        "updated_at": "ISO-8601"
      }
    ],
    "exports": [
      {"at": "ISO-8601", "folder": "C:\\...", "peer_count": 3}
    ],
    "settings": {
      "default_dns": "1.1.1.1",
      "default_mtu": 1420,
      "default_keepalive": 25,
      "data_folder": "%LOCALAPPDATA%\\VPNTunnelBuilder",
      "wg_cli_path": ""           # auto-detected or user-provided
    },
    "events": [ {"at": "ISO-8601", "level": "info", "message": "..."} ]
  }

2. Runtime invariants
---------------------
- Server keys: public_key == x25519(scalarbase(server private bytes)).
  Re-computed (never trusted from storage) each time a report/export runs.
- Peer IP assignment: first usable address is the server; peers are
  auto-assigned sequentially from the next free host, never duplicated,
  never beyond the network's broadcast, and never on the server address.
- Client config generation requires: own private key, server public key,
  server endpoint host, and a subnetted AllowedIPs entry.
- Exports are idempotent: re-export over-writes files with identical names;
  relative content stays deterministic (map/list ordering sorted by name).
- The state file is written atomically (temp file + rename) and indented
  deterministically so diffs are meaningful.

3. Event log cap
----------------
Events are kept in RAM for the session and merged into the persisted log on
save; the persisted event log is trimmed to the most recent 200 entries to
keep excitation small and report size bounded.

4. Execution modes
------------------
- GUI (default): full application from main.py.
- selfcheck: `python -m wgbuilder.core.selfcheck` -> verifies the crypto,
  config round-trip and report generation; exit code 0/1. Used by build CI.

5. Last known state (filled at runtime)
---------------------------------------
[populated on first save]