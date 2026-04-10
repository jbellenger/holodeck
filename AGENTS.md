# Repository Guidelines

## Project Structure & Module Organization
This repository has two main parts:

- `holodeck/`: Blender add-on code. Keep pure, testable logic in `holodeck/core/` and Blender-specific adapters in `holodeck/handlers/`.
- `holodeck/resources/`: Browser player assets, including `index.html`, `styles.css`, and `player.js`.
- `tests/`: Pytest coverage for the add-on and local server behavior.
- `demo/`: Canonical demo source files, including `demo.blend` and tracked rendered frames.

Preserve the existing separation of concerns: logic belongs in `core/`, Blender hooks and UI belong in `handlers/`.

## Build, Test, and Development Commands
- `make setup`: Create `holodeck-venv/` and install pytest.
- `make test`: Run the full test suite with verbose output.
- `make test-one TEST=test_add_frame`: Run a focused test by name pattern.
- `make serve`: Start the presentation server locally on port `8000`.
- `make build`: Produce both distributable zip files in `dist/`.
- `make clean`: Remove the virtualenv and Python cache files.

For quick player checks, run `make serve` and open `http://localhost:8000`.

## Coding Style & Naming Conventions
Use 4-space indentation in Python and follow existing straightforward, standard-library-first patterns. Prefer:

- `snake_case` for functions, methods, variables, and module names
- `PascalCase` for classes such as `ManifestGenerator`
- thin Blender handlers that delegate to testable core logic

No formatter or linter is configured in this repo today, so match the surrounding file style and keep changes small and readable.

## Testing Guidelines
Tests use `pytest` with discovery defined in `pytest.ini`:

- files: `tests/test_*.py`
- classes: `Test*`
- functions: `test_*`

Add or update tests whenever behavior changes in `holodeck/core/`, render handlers, or the local server. Prefer unit tests for manifest generation and lightweight integration tests for server endpoints.

## Commit & Pull Request Guidelines
Git history is minimal and currently only shows `init`, so there is no strong historical convention yet. Use short, imperative commit subjects such as `Add manifest marker validation`.

For pull requests, include:

- a brief summary of the user-visible or developer-visible change
- test coverage notes (`make test`, targeted test names, or manual browser checks)
- screenshots or short recordings for player UI changes
- linked issues or context when the change is not self-explanatory
