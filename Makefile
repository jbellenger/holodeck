.PHONY: test serve setup clean build build-addon build-player

VENV := holodeck-venv
PYTHON := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest
VERSION := 1.0.0

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
	cd holodeck-player && zip -r ../dist/holodeck-player-$(VERSION).zip .

# Build both artifacts
build: build-addon build-player
