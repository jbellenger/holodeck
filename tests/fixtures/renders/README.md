Tracked rendered output fixtures.

`demo/` contains the pre-rendered AVIF frame sequence for `demo.blend`.
CI and the GitHub Pages workflow copy those frames into a temporary output
directory and run `holodeck refresh demo.blend ...` to regenerate the manifest
and reinstall the player assets without re-rendering the full demo in CI.
