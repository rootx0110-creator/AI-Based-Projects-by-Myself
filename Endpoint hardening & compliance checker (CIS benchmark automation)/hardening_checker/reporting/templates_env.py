"""Jinja2 templates shared by HTML and PDF renderers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATE_DIR = Path(__file__).parent / "templates"

_severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_status_rank = {"fail": 0, "error": 1, "manual": 2, "skipped": 3,
                "not_applicable": 4, "pass": 5}


def _has_attr(mapping: Any, name: str) -> bool:
    try:
        return name in mapping
    except TypeError:
        return False


def make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    env.filters["sev_rank"] = lambda s: _severity_rank.get(str(s).lower(), 9)
    env.filters["status_rank"] = lambda s: _status_rank.get(str(s).lower(), 9)
    env.globals["has"] = _has_attr
    return env


__all__ = ["make_env", "TEMPLATE_DIR"]
