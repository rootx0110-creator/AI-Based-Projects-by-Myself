"""Platform context: gathers environment facts and exposes check primitives.

Each platform provides:
  * platform_info()      -> PlatformInfo
  * check primitives     -> registry / command / service / file / etc.

Primitives are intentionally read-only. Nothing here writes to the system.
"""

from __future__ import annotations

import platform
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone
from typing import Optional

from .exceptions import CheckExecutionError, UnsupportedPlatformError
from .models import PlatformInfo

IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PlatformContext:
    """Abstract base: read-only inspection primitives per OS."""

    name = "unknown"

    # ------------------------------------------------------------------ info
    def platform_info(self) -> PlatformInfo:  # pragma: no cover - overridden
        raise NotImplementedError

    # -------------------------------------------------------------- registry
    def registry_value(self, hive: str, path: str, value: str) -> Optional[object]:
        """Read one registry value. Returns None when absent."""
        raise UnsupportedPlatformError("registry checks are Windows-only")

    def registry_key_exists(self, hive: str, path: str) -> bool:
        raise UnsupportedPlatformError("registry checks are Windows-only")

    # --------------------------------------------------------------- command
    def run_command(
        self, command: list[str], timeout: float = 15.0, shell: bool = False
    ) -> tuple[int, str, str]:
        """Run a read-only command, capturing output. Never mutates state."""
        kwargs: dict[str, object] = {
            "capture_output": True,
            "text": True,
            "timeout": timeout,
            "shell": shell,
            "encoding": "utf-8",
            "errors": "replace",
        }
        # Never let child console windows flash in front of the windowed GUI.
        if IS_WINDOWS:
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            proc = subprocess.run(command, **kwargs)
            return proc.returncode, proc.stdout or "", proc.stderr or ""
        except FileNotFoundError as exc:
            raise CheckExecutionError(f"tool not found: {command[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise CheckExecutionError(
                f"command timed out after {timeout}s: {' '.join(command)}"
            ) from exc

    def run_powershell(self, script: str, timeout: float = 30.0) -> tuple[int, str, str]:
        """Run a read-only PowerShell snippet with a safe profile-less host."""
        ps = "powershell" if IS_WINDOWS else "pwsh"
        return self.run_command(
            [ps, "-NoProfile", "-NonInteractive", "-NoLogo", "-Command", script],
            timeout=timeout,
        )

    # ------------------------------------------------------------------ files
    def file_exists(self, path: str) -> bool:
        raise NotImplementedError

    def read_file_text(self, path: str, max_bytes: int = 1_000_000) -> str:
        raise NotImplementedError

    # --------------------------------------------------------------- services
    def service_status(self, service_name: str) -> Optional[str]:
        """Return service state string or None if the service does not exist."""
        raise NotImplementedError

    def package_installed(self, package: str) -> Optional[bool]:
        """Return True/False, or None when the platform cannot tell."""
        return None

    # ------------------------------------------------------------------ misc
    def local_admins(self) -> list[str]:
        raise NotImplementedError

    def firewall_active(self) -> Optional[bool]:
        return None

    def screen_lock_seconds(self) -> Optional[int]:
        return None


# --------------------------------------------------------------------------- #
# Windows
# --------------------------------------------------------------------------- #
class WindowsContext(PlatformContext):
    name = "windows"

    # Friendly hive names -> winreg constants
    _HIVES = {
        "HKLM": "HKEY_LOCAL_MACHINE",
        "HKCU": "HKEY_CURRENT_USER",
        "HKCR": "HKEY_CLASSES_ROOT",
        "HKU": "HKEY_USERS",
        "HKCC": "HKEY_CURRENT_CONFIG",
    }

    def platform_info(self) -> PlatformInfo:
        info = PlatformInfo(system="Windows")
        info.os_name = platform.system()
        try:
            win = platform.win32_ver()
            info.os_version = win[0] or win[1]
            info.build = win[1]
        except Exception:  # noqa: BLE001 - info only, never fatal
            info.os_version = platform.release()
        info.arch = platform.machine() or platform.architecture()[0]
        info.hostname = socket.gethostname()
        info.ip_addresses = self._local_ips()
        info.is_admin = self._is_admin()
        info.domain_joined = self._domain_joined()
        try:
            cap = self.registry_value("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "DisplayVersion")
            if cap:
                info.extra["display_version"] = str(cap)
            ubr = self.registry_value("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "UBR")
            if ubr is not None:
                info.extra["patch_level"] = str(ubr)
        except Exception:  # noqa: BLE001
            pass
        return info

    # -------------------------------------------------------------- registry
    def registry_value(self, hive: str, path: str, value: str) -> Optional[object]:
        if hive not in self._HIVES:
            raise CheckExecutionError(f"unsupported hive: {hive}")
        try:
            import winreg  # noqa: PLC0415 - Windows only
        except ImportError as exc:  # pragma: no cover
            raise UnsupportedPlatformError("winreg unavailable") from exc

        hive_const = getattr(winreg, self._HIVES[hive])
        flag = winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        try:
            with winreg.OpenKey(hive_const, path, 0, flag) as key:
                data, _type = winreg.QueryValueEx(key, value)
                return data
        except FileNotFoundError:
            return None
        except PermissionError as exc:
            raise CheckExecutionError(f"access denied: {hive}\\{path}\\{value}") from exc

    def registry_key_exists(self, hive: str, path: str) -> bool:
        try:
            import winreg  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover
            raise UnsupportedPlatformError("winreg unavailable") from exc
        try:
            hive_const = getattr(winreg, self._HIVES.get(hive, "HKEY_LOCAL_MACHINE"))
            with winreg.OpenKey(hive_const, path, 0,
                                winreg.KEY_READ | winreg.KEY_WOW64_64KEY):
                return True
        except FileNotFoundError:
            return False

    # ------------------------------------------------------------------ files
    def file_exists(self, path: str) -> bool:
        import os  # noqa: PLC0415

        return os.path.exists(path)

    def read_file_text(self, path: str, max_bytes: int = 1_000_000) -> str:
        import os  # noqa: PLC0415

        if not os.path.isfile(path):
            raise CheckExecutionError(f"file not found: {path}")
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(max_bytes)

    # --------------------------------------------------------------- services
    def service_status(self, service_name: str) -> Optional[str]:
        code, out, _err = self.run_powershell(
            f"(Get-Service -Name '{service_name}' -ErrorAction SilentlyContinue)"
            ".Status.ToString()",
            timeout=20,
        )
        text = (out or "").strip()
        if code != 0 or not text:
            return None
        return text

    def local_admins(self) -> list[str]:
        code, out, _err = self.run_powershell(
            "Get-LocalGroupMember -Group 'Administrators' "
            "| Select-Object -ExpandProperty Name", timeout=20,
        )
        if code != 0:
            return []
        return [ln.strip() for ln in out.splitlines() if ln.strip()]

    def firewall_active(self) -> Optional[bool]:
        code, out, _err = self.run_powershell(
            "(Get-NetFirewallProfile | Where-Object Enabled -eq $false).Count", timeout=25
        )
        if code != 0:
            return None
        try:
            return int(out.strip() or "0") == 0
        except ValueError:
            return None

    def screen_lock_seconds(self) -> Optional[int]:
        v = self.registry_value(
            "HKCU", r"Control Panel\Desktop", "ScreenSaveTimeOut"
        )
        if v is None:
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------- internals
    @staticmethod
    def _is_admin() -> bool:
        try:
            import ctypes  # noqa: PLC0415

            return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            return False

    def _domain_joined(self) -> bool:
        code, out, _err = self.run_powershell(
            "(Get-CimInstance Win32_ComputerSystem).PartOfDomain", timeout=20
        )
        return code == 0 and out.strip().lower() == "true"

    @staticmethod
    def _local_ips() -> list[str]:
        ips: list[str] = []
        try:
            for _family, _kind, _proto, _canon, sockaddr in socket.getaddrinfo(
                socket.gethostname(), None, family=socket.AF_INET
            ):
                ip = sockaddr[0]
                if ip not in ips and not ip.startswith("169.254."):
                    ips.append(ip)
        except OSError:
            pass
        if not ips:
            try:
                probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                probe.connect(("10.255.255.255", 1))
                ips.append(probe.getsockname()[0])
                probe.close()
            except OSError:
                pass
        return ips


# --------------------------------------------------------------------------- #
# Linux / macOS (optional support)
# --------------------------------------------------------------------------- #
class UnixContext(PlatformContext):
    name = "unix"

    def platform_info(self) -> PlatformInfo:
        info = PlatformInfo(system=platform.system())
        info.os_name = "Linux" if IS_LINUX else "macOS"
        info.os_version = platform.release()
        info.arch = platform.machine()
        info.hostname = socket.gethostname()
        info.ip_addresses = WindowsContext._local_ips()
        info.is_admin = _unix_is_root()
        info.extra["kernel"] = platform.release()
        if IS_LINUX:
            pretty = _first_file_line("/etc/os-release", "PRETTY_NAME=")
            if pretty:
                info.os_name = pretty
        elif IS_MACOS:
            code, out, _ = self.run_command(["sw_vers", "-productVersion"])
            if code == 0:
                info.os_version = out.strip()
                info.os_name = f"macOS {out.strip()}"
        return info

    def file_exists(self, path: str) -> bool:
        import os  # noqa: PLC0415

        return os.path.exists(path)

    def read_file_text(self, path: str, max_bytes: int = 1_000_000) -> str:
        import os  # noqa: PLC0415

        if not os.path.isfile(path):
            raise CheckExecutionError(f"file not found: {path}")
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(max_bytes)

    def service_status(self, service_name: str) -> Optional[str]:
        code, out, _err = self.run_command(
            ["systemctl", "is-active", service_name], timeout=10
        )
        text = out.strip()
        if code == 0 and text:
            return text
        if text in {"inactive", "failed", "activating"}:
            return text
        return None

    def firewall_active(self) -> Optional[bool]:
        code, out, _err = self.run_command(["systemctl", "is-active", "ufw"], timeout=10)
        if code == 0:
            return out.strip() == "active"
        code, out, _err = self.run_command(["ufw", "status"], timeout=10)
        if code == 0:
            return "Status: active" in out
        return None

    def screen_lock_seconds(self) -> Optional[int]:
        return None


def _unix_is_root() -> bool:
    import os  # noqa: PLC0415

    return hasattr(os, "geteuid") and os.geteuid() == 0


def _first_file_line(path: str, prefix: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith(prefix):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return ""


def make_context() -> PlatformContext:
    """Factory: pick the right platform context for the running OS."""
    if IS_WINDOWS:
        return WindowsContext()
    if IS_LINUX or IS_MACOS:
        return UnixContext()
    raise UnsupportedPlatformError(f"unsupported platform: {sys.platform}")


__all__ = [
    "PlatformContext",
    "WindowsContext",
    "UnixContext",
    "make_context",
    "utc_now_iso",
    "IS_WINDOWS",
    "IS_LINUX",
    "IS_MACOS",
    "re",
]
