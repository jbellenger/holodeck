"""PyInstaller entrypoint for the Holodeck executable."""

from holodeck.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
