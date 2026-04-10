[Live Demo](https://jbellenger.github.io/holodeck/)

# Holodeck

Holodeck is a small Blender presentation workflow made of two parts:

- a Blender add-on in `holodeck/` that generates presentation data from an animation
- a browser player in `holodeck/resources/` that plays rendered frames using `manifest.json`

The repo also includes tests, a sample Blender file (`demo.blend`), and build helpers for packaging both parts.

## Project Layout

- `holodeck/`: Blender add-on source
- `holodeck/core/`: pure logic such as manifest and server helpers
- `holodeck/handlers/`: Blender-specific handlers and UI
- `holodeck/resources/`: canonical packaged player assets used by the add-on and headless export
- `holodeck-player/`: local dev server and standalone player copy
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
- `make export-headless BLEND_FILE=demo.blend HOLODECK_OUTPUT=dist/demo-holodeck`: render a static export bundle with Blender in background mode
- `make build-demo`: refresh the tracked `docs/` bundle used by GitHub Pages
- `make clean`: remove the virtualenv and Python cache files

## Typical Workflow

1. Open `demo.blend` or your own Blender file.
2. Set the render output to a `render/` directory relative to the blend file.
3. Use the Holodeck add-on to render frames and generate `manifest.json` plus root-level player assets.
4. Start the built-in server from the Holodeck panel and open the reported URL.

## Headless Export

The background export workflow renders a self-contained static bundle with this layout:

```text
build/holodeck/
  index.html
  manifest.json
  player.js
  styles.css
  render/
```

You can produce that bundle directly with Blender:

```bash
make export-headless BLEND_FILE=demo.blend HOLODECK_OUTPUT=dist/demo-holodeck
```

For another project, invoke the same script from its `Makefile`:

```make
BLENDER ?= blender
HOLODECK_REPO ?= /path/to/holodeck
BLEND_FILE := blend/presentation.blend
HOLODECK_OUTPUT := build/holodeck

build-holodeck:
	rm -rf $(HOLODECK_OUTPUT)
	$(BLENDER) -b $(BLEND_FILE) \
	  --python $(HOLODECK_REPO)/scripts/export_holodeck.py \
	  -- --output $(HOLODECK_OUTPUT)
```

The repo’s own public demo is the committed `docs/` bundle. Refresh it with:

```bash
make build-demo
```

For player-specific details, see `holodeck-player/README.md`.
