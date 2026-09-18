"""
Browser Artifact Extractor - Main Application
Extracts browsing history, cookies, and cache from installed browsers.
"""

import os
import sys
import json
import shutil
import sqlite3
import tempfile
import datetime
import hashlib
import struct
import webbrowser
import threading
import time
import csv
import io
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_file

app = Flask(__name__, template_folder='templates')
app.secret_key = os.urandom(24)

# Global state
app_state = {
    'detected_browsers': {},
    'extraction_results': {},
    'current_status': 'idle',
    'progress': 0,
    'progress_message': '',
}


def get_user_data_dir():
    return Path(os.environ.get('LOCALAPPDATA', ''))


def get_appdata_dir():
    return Path(os.environ.get('APPDATA', ''))


def chrome_timestamp_to_datetime(chrome_ts):
    if not chrome_ts or chrome_ts == 0:
        return None
    try:
        epoch_start = datetime.datetime(1601, 1, 1)
        return epoch_start + datetime.timedelta(microseconds=chrome_ts)
    except Exception:
        return None


def firefox_timestamp_to_datetime(ff_ts):
    if not ff_ts or ff_ts == 0:
        return None
    try:
        return datetime.datetime.fromtimestamp(ff_ts / 1000000)
    except Exception:
        return None


def unix_timestamp_to_datetime(ts):
    if not ts or ts == 0:
        return None
    try:
        return datetime.datetime.fromtimestamp(ts)
    except Exception:
        return None


def format_datetime(dt):
    if dt is None:
        return 'N/A'
    try:
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return str(dt)


class BrowserDetector:
    BROWSERS = {
        'chrome': {
            'name': 'Google Chrome',
            'icon': 'chrome',
            'color': '#4285F4',
            'paths': [
                Path(os.environ.get('LOCALAPPDATA', '')) / 'Google' / 'Chrome' / 'User Data',
            ],
            'history_db': 'History',
            'cookies_db': 'Cookies',
            'cache_path': 'Cache',
        },
        'edge': {
            'name': 'Microsoft Edge',
            'icon': 'edge',
            'color': '#0078D7',
            'paths': [
                Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft' / 'Edge' / 'User Data',
            ],
            'history_db': 'History',
            'cookies_db': 'Cookies',
            'cache_path': 'Cache',
        },
        'brave': {
            'name': 'Brave Browser',
            'icon': 'brave',
            'color': '#FB542B',
            'paths': [
                Path(os.environ.get('LOCALAPPDATA', '')) / 'BraveSoftware' / 'Brave-Browser' / 'User Data',
            ],
            'history_db': 'History',
            'cookies_db': 'Cookies',
            'cache_path': 'Cache',
        },
        'firefox': {
            'name': 'Mozilla Firefox',
            'icon': 'firefox',
            'color': '#FF7139',
            'paths': [
                Path(os.environ.get('APPDATA', '')) / 'Mozilla' / 'Firefox' / 'Profiles',
            ],
            'history_db': 'places.sqlite',
            'cookies_db': 'cookies.sqlite',
            'cache_path': 'cache2',
        },
    }

    @classmethod
    def detect_all(cls):
        detected = {}
        for browser_id, config in cls.BROWSERS.items():
            for base_path in config['paths']:
                if base_path.exists():
                    profiles = cls._find_profiles(browser_id, base_path, config)
                    if profiles:
                        detected[browser_id] = {
                            'name': config['name'],
                            'icon': config['icon'],
                            'color': config['color'],
                            'profiles': profiles,
                            'history_count': 0,
                            'cookies_count': 0,
                            'cache_count': 0,
                        }
                        break
        return detected

    @classmethod
    def _find_profiles(cls, browser_id, base_path, config):
        profiles = []
        if browser_id == 'firefox':
            if base_path.exists():
                for item in base_path.iterdir():
                    if item.is_dir() and item.name.endswith('.default-release'):
                        history_path = item / config['history_db']
                        cookies_path = item / config['cookies_db']
                        if history_path.exists() or cookies_path.exists():
                            profiles.append({
                                'name': item.name,
                                'path': str(item),
                                'history_db': str(history_path) if history_path.exists() else None,
                                'cookies_db': str(cookies_path) if cookies_path.exists() else None,
                                'cache_path': str(item / config['cache_path']) if (item / config['cache_path']).exists() else None,
                            })
                    elif item.is_dir() and '.default' in item.name:
                        history_path = item / config['history_db']
                        cookies_path = item / config['cookies_db']
                        if history_path.exists() or cookies_path.exists():
                            profiles.append({
                                'name': item.name,
                                'path': str(item),
                                'history_db': str(history_path) if history_path.exists() else None,
                                'cookies_db': str(cookies_path) if cookies_path.exists() else None,
                                'cache_path': str(item / config['cache_path']) if (item / config['cache_path']).exists() else None,
                            })
        else:
            default_profile = base_path / 'Default'
            if default_profile.exists():
                history_path = default_profile / config['history_db']
                cookies_path = default_profile / config['cookies_db']
                if not cookies_path.exists():
                    cookies_path = default_profile / 'Network' / config['cookies_db']
                if history_path.exists() or cookies_path.exists():
                    profiles.append({
                        'name': 'Default',
                        'path': str(default_profile),
                        'history_db': str(history_path) if history_path.exists() else None,
                        'cookies_db': str(cookies_path) if cookies_path.exists() else None,
                        'cache_path': str(default_profile / config['cache_path']) if (default_profile / config['cache_path']).exists() else None,
                    })
            for item in base_path.iterdir():
                if item.is_dir() and item.name.startswith('Profile') and item.name != 'Default':
                    history_path = item / config['history_db']
                    cookies_path = item / config['cookies_db']
                    if not cookies_path.exists():
                        cookies_path = item / 'Network' / config['cookies_db']
                    if history_path.exists() or cookies_path.exists():
                        profiles.append({
                            'name': item.name,
                            'path': str(item),
                            'history_db': str(history_path) if history_path.exists() else None,
                            'cookies_db': str(cookies_path) if cookies_path.exists() else None,
                            'cache_path': str(item / config['cache_path']) if (item / config['cache_path']).exists() else None,
                        })
        return profiles


import ctypes
from ctypes import wintypes

GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x1
FILE_SHARE_WRITE = 0x2
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80


def _win_read_file(path_str):
    """Read a file on Windows using CreateFile with sharing flags."""
    handle = ctypes.windll.kernel32.CreateFileW(
        path_str, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
        None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None
    )
    if handle in (ctypes.c_void_p(-1).value, 0xFFFFFFFFFFFFFFFF, -1):
        return None
    try:
        size_hi = wintypes.DWORD(0)
        size_lo = ctypes.windll.kernel32.GetFileSize(handle, ctypes.byref(size_hi))
        size = (size_hi.value << 32) | size_lo
        if size == 0:
            return None
        buf = ctypes.create_string_buffer(int(size))
        bytes_read = wintypes.DWORD(0)
        ok = ctypes.windll.kernel32.ReadFile(handle, buf, size, ctypes.byref(bytes_read), None)
        if not ok:
            return None
        return buf.raw[:bytes_read.value]
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def copy_db_if_locked(src_path, suffix='_copy'):
    if not src_path or not Path(src_path).exists():
        return None
    src_path_str = str(src_path)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix + '.db')
    tmp.close()
    try:
        shutil.copy2(src_path_str, tmp.name)
        return tmp.name
    except Exception:
        pass
    try:
        src = sqlite3.connect(f'file:{src_path_str}?immutable=1', uri=True)
        dst = sqlite3.connect(tmp.name)
        try:
            with dst:
                src.backup(dst)
            return tmp.name
        finally:
            src.close()
            dst.close()
    except Exception:
        pass
    try:
        with open(src_path_str, 'rb') as fsrc:
            with open(tmp.name, 'wb') as fdst:
                while True:
                    chunk = fsrc.read(65536)
                    if not chunk:
                        break
                    fdst.write(chunk)
            return tmp.name
    except Exception:
        pass
    if os.name == 'nt':
        try:
            data = _win_read_file(src_path_str)
            if data:
                with open(tmp.name, 'wb') as fdst:
                    fdst.write(data)
                return tmp.name
        except Exception:
            pass
    try:
        os.unlink(tmp.name)
    except Exception:
        pass
    return None


def count_db_rows(db_path, table_name='urls'):
    tmp_path = copy_db_if_locked(db_path, '_count')
    if not tmp_path:
        return 0
    try:
        conn = sqlite3.connect(f'file:{tmp_path}?mode=ro', uri=True)
        cur = conn.cursor()
        try:
            cur.execute(f'SELECT COUNT(*) FROM {table_name}')
            return cur.fetchone()[0]
        except Exception:
            return 0
        finally:
            conn.close()
    except Exception:
        return 0
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def extract_history(db_path, browser_id):
    entries = []
    tmp_path = copy_db_if_locked(db_path, '_history')
    if not tmp_path:
        return entries
    try:
        conn = sqlite3.connect(f'file:{tmp_path}?mode=ro', uri=True)
        conn.row_factory = sqlite3.Row
        conn.text_factory = lambda b: b.decode('utf-8', errors='replace')
        cursor = conn.cursor()

        if browser_id == 'firefox':
            cursor.execute('''
                SELECT p.url, p.title, p.visit_count, p.last_visit_date, p.frecency
                FROM moz_places p
                WHERE p.visit_count > 0
                ORDER BY p.last_visit_date DESC
                LIMIT 50000
            ''')
        else:
            cursor.execute('''
                SELECT urls.url, urls.title, urls.visit_count,
                       urls.last_visit_time, urls.typed_count,
                       urls.hidden
                FROM urls
                ORDER BY urls.last_visit_time DESC
                LIMIT 50000
            ''')

        for row in cursor.fetchall():
            if browser_id == 'firefox':
                dt = firefox_timestamp_to_datetime(row['last_visit_date'])
                entries.append({
                    'url': row['url'] or '',
                    'title': row['title'] or '',
                    'visit_count': row['visit_count'] or 0,
                    'last_visit': format_datetime(dt),
                    'timestamp': row['last_visit_date'] or 0,
                    'typed_count': 0,
                })
            else:
                dt = chrome_timestamp_to_datetime(row['last_visit_time'])
                entries.append({
                    'url': row['url'] or '',
                    'title': row['title'] or '',
                    'visit_count': row['visit_count'] or 0,
                    'last_visit': format_datetime(dt),
                    'timestamp': row['last_visit_time'] or 0,
                    'typed_count': row['typed_count'] or 0,
                })

        conn.close()
    except Exception as e:
        print(f"Error extracting history from {browser_id}: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
    return entries


def extract_cookies(db_path, browser_id):
    entries = []
    tmp_path = copy_db_if_locked(db_path, '_cookies')
    if not tmp_path:
        return entries
    try:
        conn = sqlite3.connect(f'file:{tmp_path}?mode=ro', uri=True)
        conn.row_factory = sqlite3.Row
        conn.text_factory = lambda b: b.decode('utf-8', errors='replace')
        cursor = conn.cursor()

        if browser_id == 'firefox':
            cursor.execute('''
                SELECT host, name, value, path, expiry, isSecure, isHttpOnly
                FROM moz_cookies
                ORDER BY host
                LIMIT 50000
            ''')
        else:
            cursor.execute('''
                SELECT host_key, name, value, path, expires_utc,
                       is_secure, is_httponly, encrypted_value
                FROM cookies
                ORDER BY host_key
                LIMIT 50000
            ''')

        for row in cursor.fetchall():
            if browser_id == 'firefox':
                dt = unix_timestamp_to_datetime(row['expiry'])
                entries.append({
                    'domain': row['host'] or '',
                    'name': row['name'] or '',
                    'value': row['value'] or '',
                    'path': row['path'] or '/',
                    'expiry': format_datetime(dt),
                    'secure': bool(row['isSecure']),
                    'http_only': bool(row['isHttpOnly']),
                })
            else:
                dt = chrome_timestamp_to_datetime(row['expires_utc'])
                value = row['value'] or ''
                if not value and row['encrypted_value']:
                    value = '<encrypted>'
                entries.append({
                    'domain': row['host_key'] or '',
                    'name': row['name'] or '',
                    'value': value,
                    'path': row['path'] or '/',
                    'expiry': format_datetime(dt),
                    'secure': bool(row['is_secure']),
                    'http_only': bool(row['is_httponly']),
                })

        conn.close()
    except Exception as e:
        print(f"Error extracting cookies from {browser_id}: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
    return entries


def extract_cache(cache_path, browser_id):
    entries = []
    if not cache_path or not Path(cache_path).exists():
        return entries
    try:
        cache_path = Path(cache_path)
        index_file = cache_path / 'index'
        if index_file.exists():
            try:
                with open(index_file, 'rb') as f:
                    data = f.read(1024 * 1024)
                    url_count = data.count(b'\x00')
                    entries.append({
                        'type': 'Cache Index',
                        'info': f'Index file present ({len(data)} bytes)',
                        'file_count': url_count,
                        'total_size': len(data),
                    })
            except Exception:
                pass

        file_count = 0
        total_size = 0
        mime_types = {}
        for root, dirs, files in os.walk(cache_path):
            for fname in files:
                fpath = Path(root) / fname
                try:
                    size = fpath.stat().st_size
                    total_size += size
                    file_count += 1
                    ext = fpath.suffix.lower()
                    mime_types[ext] = mime_types.get(ext, 0) + 1
                except Exception:
                    continue
                if file_count >= 10000:
                    break
            if file_count >= 10000:
                break

        if file_count > 0:
            entries.append({
                'type': 'Cache Files',
                'info': f'{file_count} cached files found',
                'file_count': file_count,
                'total_size': total_size,
                'mime_types': dict(sorted(mime_types.items(), key=lambda x: -x[1])[:20]),
            })

        for ext, count in sorted(mime_types.items(), key=lambda x: -x[1])[:10]:
            entries.append({
                'type': f'File Type: {ext or "no extension"}',
                'info': f'{count} files',
                'file_count': count,
                'total_size': 0,
            })

    except Exception as e:
        print(f"Error extracting cache from {browser_id}: {e}")
    return entries


# ---- Flask Routes ----

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/detect', methods=['POST'])
def detect_browsers():
    try:
        detected = BrowserDetector.detect_all()

        for browser_id, info in detected.items():
            hist_total = 0
            cook_total = 0
            for profile in info['profiles']:
                if profile.get('history_db'):
                    table = 'moz_places' if browser_id == 'firefox' else 'urls'
                    hist_total += count_db_rows(profile['history_db'], table)
                if profile.get('cookies_db'):
                    table = 'moz_cookies' if browser_id == 'firefox' else 'cookies'
                    cook_total += count_db_rows(profile['cookies_db'], table)
            info['history_count'] = hist_total
            info['cookies_count'] = cook_total

        app_state['detected_browsers'] = detected
        return jsonify({'status': 'ok', 'browsers': detected})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/extract', methods=['POST'])
def extract_artifacts():
    data = request.get_json() or {}
    selected = data.get('browsers', [])
    results = {}
    app_state['current_status'] = 'extracting'
    app_state['progress'] = 0

    detected = app_state.get('detected_browsers', {})
    total = len(selected)
    for idx, browser_id in enumerate(selected):
        if browser_id not in detected:
            continue
        browser_info = detected[browser_id]
        app_state['progress_message'] = f"Extracting from {browser_info['name']}..."
        app_state['progress'] = int((idx / total) * 100)

        browser_results = {
            'name': browser_info['name'],
            'history': [],
            'cookies': [],
            'cache': [],
        }

        for profile in browser_info['profiles']:
            if profile.get('history_db'):
                browser_results['history'].extend(
                    extract_history(profile['history_db'], browser_id)
                )
            if profile.get('cookies_db'):
                browser_results['cookies'].extend(
                    extract_cookies(profile['cookies_db'], browser_id)
                )
            if profile.get('cache_path'):
                browser_results['cache'].extend(
                    extract_cache(profile['cache_path'], browser_id)
                )

        results[browser_id] = browser_results

    app_state['extraction_results'] = results
    app_state['current_status'] = 'complete'
    app_state['progress'] = 100
    app_state['progress_message'] = 'Extraction complete!'

    return jsonify({'status': 'ok', 'results': results})


@app.route('/api/results')
def get_results():
    return jsonify({
        'status': app_state['current_status'],
        'results': app_state['extraction_results'],
    })


@app.route('/api/export/html', methods=['POST'])
def export_html():
    results = app_state.get('extraction_results', {})
    if not results:
        return jsonify({'status': 'error', 'message': 'No results to export'}), 400

    html = generate_html_report(results)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8')
    tmp.write(html)
    tmp.close()
    return send_file(tmp.name, as_attachment=True, download_name='browser_artifacts_report.html',
                     mimetype='text/html')


@app.route('/api/export/json', methods=['POST'])
def export_json():
    results = app_state.get('extraction_results', {})
    if not results:
        return jsonify({'status': 'error', 'message': 'No results to export'}), 400

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w', encoding='utf-8')
    json.dump(results, tmp, indent=2, default=str)
    tmp.close()
    return send_file(tmp.name, as_attachment=True, download_name='browser_artifacts_report.json',
                     mimetype='application/json')


@app.route('/api/export/csv', methods=['POST'])
def export_csv():
    data = request.get_json() or {}
    artifact_type = data.get('type', 'history')
    results = app_state.get('extraction_results', {})
    if not results:
        return jsonify({'status': 'error', 'message': 'No results to export'}), 400

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w', newline='', encoding='utf-8')
    writer = csv.writer(tmp)

    if artifact_type == 'history':
        writer.writerow(['Browser', 'URL', 'Title', 'Visit Count', 'Last Visit', 'Typed Count'])
        for bid, bdata in results.items():
            for entry in bdata.get('history', []):
                writer.writerow([bdata['name'], entry['url'], entry['title'],
                                 entry['visit_count'], entry['last_visit'], entry['typed_count']])
    elif artifact_type == 'cookies':
        writer.writerow(['Browser', 'Domain', 'Name', 'Value', 'Path', 'Expiry', 'Secure', 'HttpOnly'])
        for bid, bdata in results.items():
            for entry in bdata.get('cookies', []):
                writer.writerow([bdata['name'], entry['domain'], entry['name'], entry['value'],
                                 entry['path'], entry['expiry'], entry['secure'], entry['http_only']])
    elif artifact_type == 'cache':
        writer.writerow(['Browser', 'Type', 'Info', 'File Count', 'Total Size'])
        for bid, bdata in results.items():
            for entry in bdata.get('cache', []):
                writer.writerow([bdata['name'], entry['type'], entry['info'],
                                 entry['file_count'], entry['total_size']])

    tmp.close()
    return send_file(tmp.name, as_attachment=True,
                     download_name=f'browser_{artifact_type}_report.csv',
                     mimetype='text/csv')


def generate_html_report(results):
    total_history = sum(len(b.get('history', [])) for b in results.values())
    total_cookies = sum(len(b.get('cookies', [])) for b in results.values())
    total_cache = sum(len(b.get('cache', [])) for b in results.values())

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Browser Artifact Extractor - Report</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f0f1a; color: #e0e0e0; padding: 40px; }}
.header {{ text-align: center; margin-bottom: 40px; }}
.header h1 {{ font-size: 2.2em; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.header p {{ color: #888; margin-top: 10px; font-size: 1.1em; }}
.summary {{ display: flex; justify-content: center; gap: 30px; margin: 30px 0; }}
.summary-card {{ background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 16px; padding: 25px 40px; text-align: center; border: 1px solid #333; }}
.summary-card h3 {{ font-size: 2.5em; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.summary-card p {{ color: #aaa; margin-top: 5px; }}
.browser-section {{ margin: 30px 0; background: #1a1a2e; border-radius: 16px; padding: 30px; border: 1px solid #333; }}
.browser-section h2 {{ color: #667eea; margin-bottom: 20px; font-size: 1.5em; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
th {{ background: #16213e; color: #667eea; padding: 12px 15px; text-align: left; font-weight: 600; border-bottom: 2px solid #333; }}
td {{ padding: 10px 15px; border-bottom: 1px solid #222; color: #ccc; font-size: 0.9em; }}
tr:hover td {{ background: #1e1e3a; }}
.url-cell {{ max-width: 400px; word-break: break-all; color: #7ec8e3; }}
.section-title {{ color: #e0e0e0; font-size: 1.2em; margin: 20px 0 10px; padding-bottom: 8px; border-bottom: 1px solid #333; }}
.footer {{ text-align: center; margin-top: 40px; color: #555; font-size: 0.9em; }}
</style>
</head>
<body>
<div class="header">
<h1>Browser Artifact Extractor</h1>
<p>Report generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</div>
<div class="summary">
<div class="summary-card"><h3>{total_history}</h3><p>History Entries</p></div>
<div class="summary-card"><h3>{total_cookies}</h3><p>Cookies</p></div>
<div class="summary-card"><h3>{total_cache}</h3><p>Cache Entries</p></div>
</div>
"""
    for bid, bdata in results.items():
        html += f'<div class="browser-section"><h2>{bdata["name"]}</h2>'

        if bdata.get('history'):
            html += '<div class="section-title">Browsing History</div>'
            html += '<table><tr><th>URL</th><th>Title</th><th>Visits</th><th>Last Visit</th></tr>'
            for h in bdata['history'][:500]:
                html += f'<tr><td class="url-cell">{h["url"]}</td><td>{h["title"]}</td><td>{h["visit_count"]}</td><td>{h["last_visit"]}</td></tr>'
            html += '</table>'

        if bdata.get('cookies'):
            html += '<div class="section-title">Cookies</div>'
            html += '<table><tr><th>Domain</th><th>Name</th><th>Value</th><th>Expiry</th><th>Secure</th></tr>'
            for c in bdata['cookies'][:500]:
                val = c['value'][:50] + '...' if len(c['value']) > 50 else c['value']
                html += f'<tr><td>{c["domain"]}</td><td>{c["name"]}</td><td>{val}</td><td>{c["expiry"]}</td><td>{"Yes" if c["secure"] else "No"}</td></tr>'
            html += '</table>'

        if bdata.get('cache'):
            html += '<div class="section-title">Cache</div>'
            html += '<table><tr><th>Type</th><th>Info</th><th>Files</th></tr>'
            for c in bdata['cache']:
                html += f'<tr><td>{c["type"]}</td><td>{c["info"]}</td><td>{c["file_count"]}</td></tr>'
            html += '</table>'

        html += '</div>'

    html += f"""
<div class="footer">
<p>Browser Artifact Extractor v1.0 | Report contains {total_history + total_cookies + total_cache} total artifacts</p>
</div>
</body></html>"""
    return html


def open_browser():
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')


if __name__ == '__main__':
    threading.Thread(target=open_browser, daemon=True).start()
    print("=" * 60)
    print("  Browser Artifact Extractor v1.0")
    print("  Starting server at http://127.0.0.1:5000")
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    app.run(host='127.0.0.1', port=5000, debug=False)
