"""Runtime helpers for locating packaged Holodeck assets."""

from __future__ import annotations

import sys
from pathlib import Path


def get_package_root() -> Path:
    """Return the root directory for packaged Holodeck assets."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / "holodeck"
    return Path(__file__).resolve().parents[1]


def get_package_path(*parts: str) -> Path:
    """Return the filesystem path to a packaged Holodeck file or directory."""
    return get_package_root().joinpath(*parts)
