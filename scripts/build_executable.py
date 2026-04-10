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


def get_add_data_entries(repo_root: Path) -> list[tuple[Path, str]]:
    """Return filesystem paths that must be available to the frozen runtime."""
    return [
        (repo_root / "holodeck", "holodeck"),
    ]


def build_pyinstaller_command(repo_root: Path, pyinstaller: Path, dist_dir: Path, build_dir: Path) -> list[str]:
    """Construct the PyInstaller command for the Holodeck CLI executable."""
    entrypoint = repo_root / "scripts" / "run_holodeck.py"
    command = [
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
    ]

    for source, destination in get_add_data_entries(repo_root):
        command.extend(["--add-data", format_add_data(source, destination)])

    command.append(str(entrypoint))
    return command


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    dist_dir = repo_root / "dist"
    build_dir = repo_root / "build" / "pyinstaller"
    pyinstaller = get_pyinstaller_executable()

    shutil.rmtree(build_dir, ignore_errors=True)
    (dist_dir / "holodeck").unlink(missing_ok=True)
    (dist_dir / "holodeck.exe").unlink(missing_ok=True)

    subprocess.run(
        build_pyinstaller_command(repo_root, pyinstaller, dist_dir, build_dir),
        check=True,
    )


if __name__ == "__main__":
    main()
