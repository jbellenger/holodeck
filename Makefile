.PHONY: test test-one setup clean build build-pyinstaller build-pex build-demo serve-demo regen-blend-fixtures sync-player-assets

VENV := holodeck-venv
PYTHON := $(VENV)/bin/python
PYTEST := $(PYTHON) -m pytest
BLENDER ?= blender
DEMO_OUTPUT ?= docs
PORT ?= 8000

# Run unit tests
test:
	$(PYTEST) -v

# Run a specific test (usage: make test-one TEST=test_add_frame)
test-one:
	$(PYTEST) -v -k $(TEST)

# Set up the virtual environment
setup:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install -q -e . pytest

# Remove generated files and caches
clean:
	rm -rf $(VENV)
	rm -rf build
	rm -rf dist
	rm -rf __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Build standalone executables at dist/holodeck and dist/holodeck.pex
build:
	$(MAKE) build-pyinstaller
	$(MAKE) build-pex

build-pyinstaller:
	rm -f dist/holodeck dist/holodeck.exe
	$(MAKE) dist/holodeck

build-pex:
	rm -f dist/holodeck.pex
	$(MAKE) dist/holodeck.pex

sync-player-assets:
	python3 scripts/sync_player_assets.py

dist/holodeck: sync-player-assets
	$(PYTHON) -m pip install -q -e .[build]
	$(PYTHON) scripts/build_executable.py

dist/holodeck.pex: sync-player-assets
	$(PYTHON) -m pip install -q -e .[build]
	$(PYTHON) scripts/build_pex.py

# Regenerate the local demo bundle from demo.blend
build-demo: dist/holodeck
	rm -rf $(DEMO_OUTPUT)
	./dist/holodeck build demo.blend $(DEMO_OUTPUT) --blender $(BLENDER)
	touch $(DEMO_OUTPUT)/.nojekyll

# Start the presentation server for the local demo bundle
serve-demo: dist/holodeck
	./dist/holodeck serve $(DEMO_OUTPUT) --port $(PORT)

# Regenerate Blender test fixture .blend files
regen-blend-fixtures:
	$(BLENDER) -b --factory-startup --python scripts/create_test_blend_fixtures.py
