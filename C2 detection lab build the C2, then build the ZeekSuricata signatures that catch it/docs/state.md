# C2 Detection Lab — Current State

> Written for lab operators and maintainers. Updated on first release (v1.0.0).

## 1. What is implemented

- [x] Loopback C2 listener (`c2lab/server.py`) — GET/POST, tasking blob response.
- [x] Beacon agent simulator (`c2lab/client.py`) — interval + jitter scheduling,
      RTT measurement, profile-driven fingerprints.
- [x] Five C2 fingerprint profiles (`c2lab/presets.py`).
- [x] Suricata `.rules` generator — UA + URI + method signatures with
      deterministic SIDs (`c2lab/signatures.py`).
- [x] Zeek `signatures` generator + `beacon_detect.zeek` skeleton script.
- [x] Detection analyzer (`c2lab/detect.py`) — signature replay + behavioural
      cadence model (CV, UA stability, URI concentration).
- [x] HTML report renderer (`c2lab/report.py`) — **full** and **summary**
      flavours, self-contained inline CSS, plus JSON event export.
- [x] Tkinter GUI (`c2lab/app.py`) — standard menu bar, toolbar, tabbed
      notebook, live beacon monitor, status bar, docs viewer.
- [x] Embedded documentation with **File ▸ Export ▸ Documentation**.
- [x] One-file `.exe` build script (`build_exe.ps1`) + generated icon.

## 2. Known limitations (lab honesty)

| Limitation                                    | Reason / mitigation                                  |
|-----------------------------------------------|------------------------------------------------------|
| HTTP only, no HTTPS/TLS decoder               | Keep the lab dependency-light; rules document where TLS would require JA3/JA4 tooling. |
| Suricata/Zeek rules are *content* based       | Behavioural layer compensates; rules are teaching artifacts, validate before prod. |
| RTT data approximate                          | Loopback timings are not representative of WAN RTT.   |
| Single listener instance at a time            | One lab at a time keeps state obvious.               |
| Python 3.14 + Tk 9 build                      | Verified locally; PyInstaller one-file.              |

## 3. Test notes

Smoke-tested flows:

- Start lab → beacons flow → live table populates → detection returns
  CRITICAL/HIGH findings → full + summary HTML saved and opened in browser.
- Signature export writes `.rules`, `.sig`, `.zeek` and the docs rebuild from
  `c2lab/docs.py` verbatim.

## 4. What is next (backlog)

- [ ] JA3/JA4 fingerprint presets for TLS beacons inside the generated rules.
- [ ] PCAP capture mode (write the beacon traffic to a pcap file for off-box
      Zeek/Suricata replay).
- [ ] Rule lint pass (suricata -T / zeek -s) surfaced in the UI.
- [ ] MITRE ATT&CK annotation per profile (T1071.001 Application Layer Protocol).
- [ ] Multi-host victim simulation (multiple beacon clients, distinct IPs).
- [ ] IOC export (domains/IPs/UA hashes) alongside the HTML report.

## 5. Status rubric

- **Detector quality** — deterministic and self-consistent inside the lab;
  representative, not production-grade.
- **Operational hygiene** — loopback only; documented; ethical-lab scope.
