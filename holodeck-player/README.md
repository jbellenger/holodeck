# Holodeck Player

This directory contains a standalone copy of the browser player assets.

The canonical workflow is now CLI-driven:

```bash
holodeck build presentation.blend dist/presentation
holodeck serve dist/presentation
```

Holodeck copies the packaged player assets into each output directory automatically, so you usually do not need to work in this directory directly.
