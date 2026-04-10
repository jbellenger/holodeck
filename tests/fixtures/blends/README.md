# Blender Fixture Files

These `.blend` files exercise Holodeck's render output override behavior.

- `open_exr_output.blend`: saved with `OPEN_EXR` output and a non-Holodeck render path.
- `named_png_output.blend`: saved with `PNG` output to a file-like path instead of a render directory.

Holodeck should ignore both saved output configurations and render AVIF frames into the output directory passed on the command line.

Regenerate the fixtures with:

```bash
blender -b --factory-startup --python scripts/create_test_blend_fixtures.py
```
