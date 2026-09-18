"""Reporting subsystem: HTML and PDF report generation."""

from .html_report import render_html
from .pdf_report import render_pdf

__all__ = ["render_html", "render_pdf"]
