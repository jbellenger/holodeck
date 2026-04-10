.PHONY: test serve setup clean build build-addon build-player export-headless build-demo

VENV := holodeck-venv
PYTHON := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest
VERSION := 1.0.0
BLENDER ?= blender
BLEND_FILE ?= demo.blend
HOLODECK_OUTPUT ?= dist/holodeck-export
DEMO_OUTPUT ?= docs

# Run unit tests
test:
	$(PYTEST) -v

# Run a specific test (usage: make test-one TEST=test_add_frame)
test-one:
	$(PYTEST) -v -k $(TEST)

# Start the presentation server (quiet mode)
serve:
	python3 holodeck-player/server.py

# Set up the virtual environment
setup:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q pytest

# Remove generated files and caches
clean:
	rm -rf $(VENV)
	rm -rf __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Build the Blender addon zip
build-addon:
	mkdir -p dist
	cd holodeck && zip -r ../dist/holodeck-$(VERSION).zip . -x "*__pycache__*" "*.pyc"

# Build the player webapp zip
build-player:
	mkdir -p dist
	cd holodeck/resources && zip -r ../../dist/holodeck-player-$(VERSION).zip .

# Build both artifacts
build: build-addon build-player

# Render a .blend file into a static Holodeck export bundle
export-headless:
	mkdir -p dist
	$(BLENDER) -b $(BLEND_FILE) --python scripts/export_holodeck.py -- --output $(HOLODECK_OUTPUT)

# Refresh the tracked GitHub Pages demo bundle from demo.blend
build-demo:
	rm -rf $(DEMO_OUTPUT)
	mkdir -p $(DEMO_OUTPUT)
	$(BLENDER) -b demo.blend --python scripts/export_holodeck.py -- --output $(DEMO_OUTPUT)
	touch $(DEMO_OUTPUT)/.nojekyll
