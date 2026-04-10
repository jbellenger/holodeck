"""Runtime helpers for locating packaged Holodeck assets."""

from __future__ import annotations

import atexit
from contextlib import ExitStack
from importlib import resources
import sys
from pathlib import Path

_PACKAGE_ROOT_STACK = ExitStack()
_RESOURCE_PACKAGE_ROOT: Path | None = None

atexit.register(_PACKAGE_ROOT_STACK.close)


def _get_source_package_root() -> Path:
    """Return the package root when Holodeck is available on the filesystem."""
    return Path(__file__).resolve().parents[1]


def _get_resource_package_root() -> Path:
    """Return the package root extracted from importlib.resources when needed."""
    global _RESOURCE_PACKAGE_ROOT

    if _RESOURCE_PACKAGE_ROOT is None:
        package_root = resources.files("holodeck")
        _RESOURCE_PACKAGE_ROOT = Path(
            _PACKAGE_ROOT_STACK.enter_context(resources.as_file(package_root))
        )

    return _RESOURCE_PACKAGE_ROOT


def get_package_root() -> Path:
    """Return the root directory for packaged Holodeck assets."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / "holodeck"

    package_root = _get_source_package_root()
    if package_root.exists():
        return package_root

    return _get_resource_package_root()


def get_package_path(*parts: str) -> Path:
    """Return the filesystem path to a packaged Holodeck file or directory."""
    return get_package_root().joinpath(*parts)
