"""Build the standalone Holodeck executable with PEX."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    dist_dir = repo_root / "dist"
    output_path = dist_dir / "holodeck.pex"

    dist_dir.mkdir(parents=True, exist_ok=True)
    output_path.unlink(missing_ok=True)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pex",
            ".",
            "-c",
            "holodeck",
            "-o",
            str(output_path),
        ],
        cwd=repo_root,
        check=True,
    )


if __name__ == "__main__":
    main()
