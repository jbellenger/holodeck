.PHONY: test serve setup clean

VENV := deckgen-venv
PYTHON := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest

# Run unit tests
test:
	$(PYTEST) -v

# Run a specific test (usage: make test-one TEST=test_add_frame)
test-one:
	$(PYTEST) -v -k $(TEST)

# Start the presentation server (quiet mode)
serve:
	python3 server.py

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
