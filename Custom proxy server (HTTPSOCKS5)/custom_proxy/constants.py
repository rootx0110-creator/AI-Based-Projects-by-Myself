"""Static constants for Custom Proxy Server."""

APP_NAME = "Custom Proxy Server"
APP_ID = "CustomProxyServer"
APP_VERSION = "1.0.0"
SERVER_BANNER = f"CustomProxy/{APP_VERSION}"

# Network defaults (ADR constants)
DEFAULT_HTTP_PORT = 8080
DEFAULT_SOCKS_PORT = 1080
BUFFER_SIZE = 65536
CONNECT_TIMEOUT = 10.0            # seconds to establish upstream connections
IDLE_TIMEOUT = 75.0               # keep-alive idle timeout for client requests
HEADER_LIMIT = 64 * 1024          # max bytes for a request head
MAX_BODY_BYTES = 256 * 1024 * 1024

# Housekeeping
MAX_LOG_LINES = 2000
CONN_HISTORY_MAX = 200
STATS_INTERVAL = 1.0              # seconds between stats samples
HISTORY_SECONDS = 90              # sparkline window

BUFFER_SIZES = (16384, 32768, 65536, 131072, 262144)
BIND_MODES = ("localhost", "lan")

# Headers that must not be forwarded end-to-end (RFC 7230 hop-by-hop + proxy
# bookkeeping headers we regenerate ourselves).
HOP_BY_HOP_HEADERS = {
    "connection",
    "proxy-connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


class ErrorCode:
    """Stable error codes (E1xxx network, E2xxx auth, E3xxx config)."""

    CONNECT_REFUSED = "E1001"    # upstream refused / unreachable
    UPSTREAM_TIMEOUT = "E1002"   # upstream connect timed out
    DNS_FAILURE = "E1003"        # hostname could not be resolved
    BAD_REQUEST = "E1004"        # malformed request or target
    RELAY_ERROR = "E1005"        # connection dropped mid-transfer
    CLIENT_GONE = "E1006"        # client disconnected early
    UPSTREAM_AUTH = "E2001"      # upstream proxy rejected our credentials
    CLIENT_AUTH = "E2002"        # client failed proxy authentication
    UPSTREAM_POLICY = "E2003"    # upstream proxy refused target (policy)
    CONFIG_INVALID = "E3001"     # invalid settings supplied by user
    BIND_FAILED = "E3002"        # port in use or no permission
    CONFIG_IO = "E3003"          # config file unreadable / corrupt


ERROR_HINTS = {
    ErrorCode.CONNECT_REFUSED: "the target host refused the connection or is unreachable",
    ErrorCode.UPSTREAM_TIMEOUT: "connecting to the target timed out",
    ErrorCode.DNS_FAILURE: "the hostname could not be resolved",
    ErrorCode.BAD_REQUEST: "the request was malformed",
    ErrorCode.RELAY_ERROR: "the connection dropped while relaying data",
    ErrorCode.CLIENT_GONE: "the client disconnected before the request finished",
    ErrorCode.UPSTREAM_AUTH: "the upstream proxy rejected our credentials",
    ErrorCode.CLIENT_AUTH: "the client did not present valid proxy credentials",
    ErrorCode.UPSTREAM_POLICY: "the upstream proxy refused the target",
    ErrorCode.CONFIG_INVALID: "settings are invalid — open Settings and correct them",
    ErrorCode.BIND_FAILED: "the port is already in use or requires permission",
    ErrorCode.CONFIG_IO: "the settings file could not be read — defaults were loaded",
}
