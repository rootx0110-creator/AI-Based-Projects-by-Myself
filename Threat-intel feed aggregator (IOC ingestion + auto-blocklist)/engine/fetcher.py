import requests

import config


def fetch_text(url, timeout=config.FETCH_TIMEOUT):
    """Fetch a feed URL and return decoded text content."""
    headers = {
        "User-Agent": config.DEFAULT_USER_AGENT,
        "Accept": "*/*",
    }
    resp = requests.get(url, headers=headers, timeout=(15, config.FETCH_TIMEOUT), verify=True)
    resp.raise_for_status()
    content = resp.content
    if len(content) > config.MAX_FEED_BYTES:
        raise ValueError(f"Feed larger than {config.MAX_FEED_BYTES} bytes cap")
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")