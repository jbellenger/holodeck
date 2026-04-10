# Holodeck

Holodeck is a CLI tool and webapp that renders Blender animations as slide decks that can be viewed in a web-browser.

Because the Holodeck webapp displays pre-rendered frames, the resulting slide deck presentation allows slide decks that are higher fidelity than what can be achieved with a tool like google slides, in a way that appears to be realtime (but isn't).

Live demo: [jbellenger.github.io/holodeck](https://jbellenger.github.io/holodeck/)

Holodeck uses Blender frame markers (default blender key-binding: <kbd>M</kbd>) as pause points. Pressing space in the holodeck webapp will animate (using the frame rate configured in blender) until the next pause point.

To turn a `.blend` file into something you can upload to a static host, run:

```bash
holodeck build demo.blend dist/demo
```

That creates `dist/demo`, which you can upload to GitHub Pages, S3, or any other static host. To preview the same directory locally, run:

```bash
holodeck serve dist/demo
```

That command opens the local player URL in your default browser. Use `--no-open` to skip that behavior.

## Configuring a Blend File

Holodeck reads the active scene's frame range, fps, and timeline markers from Blender.

- `frame_start` and `frame_end` define the rendered frame span.
- Timeline markers define presentation boundaries. Put a marker on the frame where a section should begin.
- In the browser player, left and right navigation jumps between marker frames, and playback stops when it reaches the next marker or the end of the animation.
- Marker names are ignored. Only their frame numbers matter.
- Marker frame numbers are interpreted relative to the scene's start frame, so a marker on the first rendered frame becomes marker `0` in the exported manifest.
- Markers outside the rendered frame range are ignored.

## Project Layout

- `holodeck/`: Python package and CLI entrypoint
- `holodeck/core/`: testable logic for Blender invocation, manifest generation, and serving
- `holodeck-player/`: canonical browser player source files
- `holodeck/resources/`: packaged copies of `holodeck-player/` for distributable builds
- `docs/`: generated local demo output for previewing `demo.blend`
- `tests/`: pytest coverage for core logic and CLI behavior
- `tests/fixtures/blends/`: Blender fixtures for render override integration tests
- `demo.blend`: sample Blender source file

## Quick Start

1. Create the virtual environment and install dependencies:

```bash
make setup
```

2. Build the standalone `holodeck` executable:

```bash
make build
```

That produces both `dist/holodeck` (PyInstaller) and `dist/holodeck.pex` (PEX).

3. Build an export from a `.blend` file:

```bash
./dist/holodeck build demo.blend dist/demo
```

4. Serve it locally:

```bash
./dist/holodeck serve dist/demo
```

## CLI Commands

```bash
holodeck build demo.blend dist/demo
holodeck serve dist/demo --port 8000
holodeck serve dist/demo --no-open
```

- `build`: render a `.blend` file into a static directory you can upload to a site
- `serve`: preview an existing Holodeck directory locally

## Standalone Executables

You can build both standalone executables:

```bash
make build
```

That produces:

- `dist/holodeck`: a PyInstaller single-file binary
- `dist/holodeck.pex`: a PEX executable built from the same CLI entrypoint

You can also build them individually:

```bash
make build-pyinstaller
make build-pex
```

- The file is movable on the same machine.
- The executable bundles Python, the player assets, and the Blender helper scripts.
- It is distributable to other machines of the same OS and CPU architecture with Blender available on `PATH`.
- It is not a cross-platform binary. Build it separately on macOS, Linux, and Windows if you need all three.

## Common Commands

- `make setup`: create `holodeck-venv/` and install the package plus pytest
- `make test`: run the full test suite
- `make test-one TEST=test_add_frame`: run a focused test
- `make build`: produce both `dist/holodeck` and `dist/holodeck.pex`
- `make build-pyinstaller`: produce the standalone `dist/holodeck` binary with PyInstaller
- `make build-pex`: produce the standalone `dist/holodeck.pex` executable with PEX
- `make sync-player-assets`: refresh the packaged `holodeck/resources/` player files from `holodeck-player/`
- `make build-demo`: regenerate the local `docs/` demo bundle from `demo.blend`
- `make regen-blend-fixtures`: rebuild the tracked Blender test fixtures
- `make serve-demo`: serve `docs/` on port `8000` using `dist/holodeck`
- `make clean`: remove the virtualenv and Python cache files

`holodeck-player/` is the canonical source for the browser player. Local source-tree exports read from it directly, `make build` refreshes the packaged copy used for distributable binaries, and GitHub Pages deploys a freshly generated site artifact from CI instead of serving checked-in `docs/` files.
