"""Exception hierarchy for the hardening checker."""


class HardeningError(Exception):
    """Base class for all application errors."""


class UnsupportedPlatformError(HardeningError):
    """Raised when scanning is requested on an unsupported platform."""


class RuleLoadError(HardeningError):
    """Raised when a rule module or rule definition is invalid."""


class CheckExecutionError(HardeningError):
    """Raised when a check cannot be executed at all (missing tool, bad spec)."""


class ReportError(HardeningError):
    """Raised when HTML/PDF report generation fails."""


class PrivilegeWarning(HardeningError):
    """Not fatal: raised contextually when privileges are insufficient."""
