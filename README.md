# Holodeck

Holodeck is a small Blender presentation workflow made of two parts:

- a Blender add-on in `holodeck/` that generates presentation data from an animation
- a browser player in `holodeck-player/` that plays rendered frames using `manifest.json`

The repo also includes tests, a sample Blender file (`demo.blend`), and build helpers for packaging both parts.

## Project Layout

- `holodeck/`: Blender add-on source
- `holodeck/core/`: pure logic such as manifest and server helpers
- `holodeck/handlers/`: Blender-specific handlers and UI
- `holodeck/resources/`: packaged player assets used by the add-on
- `holodeck-player/`: standalone browser player and local server
- `tests/`: pytest coverage for core logic and server behavior
- `demo.blend`: example source file for local development

## Quick Start

1. Create the virtual environment and install test dependencies:

```bash
make setup
```

2. Run the test suite:

```bash
make test
```

3. Start the local player server:

```bash
make serve
```

4. Open `http://localhost:8000` in your browser.

## Common Commands

- `make setup`: create `holodeck-venv/` and install pytest
- `make test`: run the full test suite
- `make test-one TEST=test_add_frame`: run a focused test
- `make serve`: start the local server on port `8000`
- `make build`: create addon and player zip files in `dist/`
- `make clean`: remove the virtualenv and Python cache files

## Typical Workflow

1. Open `demo.blend` or your own Blender file.
2. Use the Holodeck add-on to render frames and generate a `manifest.json`.
3. Serve the player locally with `make serve`.
4. Open the player in a browser and present from the generated frames.

For player-specific details, see `holodeck-player/README.md`.
