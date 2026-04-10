"""Build the standalone Holodeck executable with PyInstaller."""

from __future__ import annotations

import os
import subprocess
import shutil
import sys
from pathlib import Path


def get_pyinstaller_executable() -> Path:
    """Return the PyInstaller console script next to the active interpreter."""
    scripts_dir = Path(sys.executable).parent
    candidates = ["pyinstaller"]
    if os.name == "nt":
        candidates.insert(0, "pyinstaller.exe")

    for candidate in candidates:
        executable = scripts_dir / candidate
        if executable.is_file():
            return executable

    raise FileNotFoundError(
        f"PyInstaller executable not found next to {sys.executable}. "
        "Install the build dependencies first."
    )


def format_add_data(source: Path, destination: str) -> str:
    """Format a PyInstaller --add-data argument for the current platform."""
    return f"{source}{os.pathsep}{destination}"


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    dist_dir = repo_root / "dist"
    build_dir = repo_root / "build" / "pyinstaller"
    entrypoint = repo_root / "scripts" / "run_holodeck.py"
    pyinstaller = get_pyinstaller_executable()

    shutil.rmtree(build_dir, ignore_errors=True)
    (dist_dir / "holodeck").unlink(missing_ok=True)
    (dist_dir / "holodeck.exe").unlink(missing_ok=True)

    subprocess.run(
        [
            str(pyinstaller),
            "--noconfirm",
            "--clean",
            "--onefile",
            "--name",
            "holodeck",
            "--distpath",
            str(dist_dir),
            "--workpath",
            str(build_dir / "work"),
            "--specpath",
            str(build_dir / "spec"),
            "--paths",
            str(repo_root),
            "--add-data",
            format_add_data(repo_root / "holodeck" / "resources", "holodeck/resources"),
            "--add-data",
            format_add_data(
                repo_root / "holodeck" / "blender_scripts",
                "holodeck/blender_scripts",
            ),
            str(entrypoint),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
