"""Sync canonical browser player assets into generated copies."""

from __future__ import annotations

import shutil
from pathlib import Path

ASSET_NAMES = ("index.html", "player.js", "styles.css")
CANONICAL_PLAYER_DIRNAME = "holodeck-player"
GENERATED_PLAYER_DIRS = (
    Path("holodeck/resources"),
)


def copy_player_assets(source_dir: Path, destination_dir: Path) -> None:
    """Copy the canonical player assets into a destination directory."""
    destination_dir.mkdir(parents=True, exist_ok=True)

    for asset_name in ASSET_NAMES:
        source_asset = source_dir / asset_name
        if not source_asset.is_file():
            raise FileNotFoundError(f"Missing canonical player asset: {source_asset}")
        shutil.copy2(source_asset, destination_dir / asset_name)


def sync_player_assets(repo_root: Path) -> list[Path]:
    """Sync canonical player assets into generated package directories."""
    source_dir = repo_root / CANONICAL_PLAYER_DIRNAME
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Canonical player directory not found: {source_dir}")

    destination_dirs: list[Path] = []
    for relative_dir in GENERATED_PLAYER_DIRS:
        destination_dir = repo_root / relative_dir
        copy_player_assets(source_dir, destination_dir)
        destination_dirs.append(destination_dir)

    return destination_dirs


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    destination_dirs = sync_player_assets(repo_root)
    for destination_dir in destination_dirs:
        print(f"Synchronized player assets to {destination_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
