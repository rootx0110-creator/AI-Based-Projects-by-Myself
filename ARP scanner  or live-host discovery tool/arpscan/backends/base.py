"""Backend interface shared by all scanning strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..models import Host


class BackendError(Exception):
    """Raised when a backend cannot perform the scan (e.g. missing deps)."""


class ScannerBackend(ABC):
    """Interface for a live-host discovery strategy.

    Implementations probe the targets and return every host that answered.
    The returned list need not be sorted or de-duplicated - the scanner
    orchestrator takes care of that.
    """

    name: str = "base"

    @abstractmethod
    def scan(
        self,
        targets: List[str],
        timeout: float = 2.0,
        retries: int = 1,
    ) -> List[Host]:
        """Scan the given IP targets and return the hosts that responded.

        Args:
            targets: IPv4 addresses as strings.
            timeout: Seconds to wait for a response.
            retries: Extra probe attempts per target (scapy backend).

        Raises:
            BackendError: If the backend cannot run in this environment.
        """