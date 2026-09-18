"""Pytest bootstrap: make src/ importable as the import root."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
