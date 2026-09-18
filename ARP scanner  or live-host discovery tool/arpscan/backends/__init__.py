"""Scanner backends.

A backend is responsible for actually probing the network and returning the
set of live hosts. Backends are thin: target expansion, de-duplication,
vendor enrichment, and sorting all happen in the scanner orchestrator so they
can be tested without touching the network.
"""

from .base import BackendError, ScannerBackend
from .scapy_backend import ScapyBackend
from .system_backend import SystemBackend

__all__ = ["BackendError", "ScannerBackend", "ScapyBackend", "SystemBackend"]