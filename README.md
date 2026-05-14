# Holodeck

Holodeck is a command-line tool that renders Blender animations as slide decks
that can be viewed in a web browser.

Because Holodeck works with pre-rendered frames, it can produce slide decks with
much higher visual fidelity than a tool like Google Slides, while still feeling
real-time during a presentation.

Holodeck renders frames as avif images, which has excellent compression and is
supported in all browsers.

Live demo: [jbellenger.github.io/holodeck](https://jbellenger.github.io/holodeck/)

## Quickstart

### 1. Download Holodeck

Download the latest Holodeck asset for your system from the
[Releases page](https://github.com/jbellenger/holodeck/releases). Choose the
macOS, Linux, or Windows archive for a standalone executable.

Unpack the archive and put the `holodeck` executable somewhere on your `PATH`.
Then check that it runs:

```bash
holodeck --help
```

Blender must also be available on your `PATH` unless you pass a specific Blender
executable with `--blender`.

If none of the standalone executable assets match your system, download the PEX
asset instead. The PEX requires Python 3.11 or newer:

```bash
python path/to/holodeck.pex --help
```

The examples below use `holodeck`. If you use the PEX asset, replace `holodeck`
with `python path/to/holodeck.pex`.

### 2. Configure Your Blend File

Holodeck reads presentation timing from the active Blender scene:

- The scene frame range controls which frames are exported.
- The scene FPS controls playback speed in the browser.
- Timeline markers define slide boundaries and pause points.
- Marker names are ignored; only marker frame numbers matter.

In Blender, add timeline markers with <kbd>M</kbd> on the frames where the
presentation should pause. During playback, pressing space or tapping advances
from the current marker to the next marker.

Markers outside the rendered frame range are ignored. Marker frame numbers are
stored relative to the scene start frame, so a marker on the first rendered frame
becomes marker `0` in the exported manifest.

### 3. Build Your Holodeck

Run `build` with a source `.blend` file and an output directory:

```bash
holodeck build path/to/deck.blend dist/deck --title "My Deck"
```

`build` renders the frames, writes `manifest.json`, and installs the browser
player assets into the output directory. The result is a static site that can be
served locally or uploaded to a static host.

Useful build options:

```bash
holodeck build path/to/deck.blend dist/deck --scene "Scene"
holodeck build path/to/deck.blend dist/deck --res-pct 50
holodeck build path/to/deck.blend dist/deck --render-engine cycles
holodeck build path/to/deck.blend dist/deck --markers-only
```

- `--scene` renders a specific Blender scene instead of the active scene.
- `--res-pct` overrides Blender's render resolution percentage.
- `--render-engine` overrides the Blend file render engine with `eevee`, `cycles`, or `workbench`.
- `--markers-only` renders only marker frames and writes a marker-only manifest.
- `--title` sets the generated player page title.

### 4. Play Your Holodeck Locally

Use `serve` to preview an existing Holodeck output directory:

```bash
holodeck serve dist/deck
```

By default, the server binds to port `8000` and opens the player in your default
browser. You can override either behavior:

```bash
holodeck serve dist/deck --port 9000
holodeck serve dist/deck --no-open
```

Common presenter shortcuts:

- Press space or tap to animate to the next marker. A small white pixel appears
  in the bottom-right corner of the visible frame while animation is running.
- Press the left or right arrow keys to jump between markers.
- Press <kbd>F</kbd> or swipe up to enter fullscreen.

### 5. Refresh Your Holodeck

Use `refresh` when the rendered frame files already exist, but the player bundle
or manifest needs to be regenerated. A common example is moving timeline markers
after rendering; `refresh` can update `manifest.json` without re-rendering every
frame.

```bash
holodeck refresh path/to/deck.blend dist/deck --title "My Deck"
```

`refresh` reads the Blend file metadata, verifies that the expected rendered
frames exist, rewrites `manifest.json`, and reinstalls the browser player assets.
If the actual frame images changed, use `build` or `render-frames` instead.

### 6. Render a Subset of Frames

Use `render-frames` with `--frames` when only a few frame images need to be
re-rendered:

```bash
holodeck render-frames path/to/deck.blend dist/deck --frames "48,72-96"
holodeck render-frames path/to/deck.blend dist/deck --render-engine workbench
holodeck refresh path/to/deck.blend dist/deck --title "My Deck"
```

Frame ranges are inclusive, and comma-separated segments are allowed. For
example, `"4"`, `"4-10"`, and `"1,2,3,20-24"` are all valid frame specs.

`render-frames` updates files under `render/`, but it does not update
`manifest.json`, so run `refresh` afterwards when the manifest should reflect
new Blend metadata or rendered frame fingerprints.

### 7. Deploy Your Holodeck

A built Holodeck output directory is a static site and can be uploaded to any
static site host, such as GitHub Pages, S3, CloudFront, Netlify, or Cloudflare
Pages.

For GitHub Pages, publish the output directory as your Pages artifact or copy it
to the branch or directory configured for Pages. If you publish from a directory
named `docs/`, add a `.nojekyll` file so GitHub Pages serves the bundled assets
without Jekyll processing.

For S3, sync the output directory to a bucket configured for static website
hosting or serve it through CloudFront:

```bash
aws s3 sync dist/deck s3://your-bucket/path/
```

The player uses relative asset paths, so the same output can be served from a
domain root or a subdirectory.


# Tips And Tricks
## workbench rendering
The `--render-engine` option override lets you render with a different engine
without changing the saved setting in the `.blend` file. If you do not pass
`--render-engine`, Holodeck uses the render engine that is already configured in
the file.

Workbench rendering is useful when you want fast feedback on timing, camera
motion, and animation. You can render the whole deck with Workbench first:

```bash
holodeck build path/to/deck.blend dist/deck --render-engine workbench
```

After the timing feels right, you can re-render selected frames or ranges with a
final engine. This is useful when only part of the deck needs more visual polish:

```bash
holodeck render-frames path/to/deck.blend dist/deck --frames "48,72-96" --render-engine cycles
```

You can also omit `--render-engine` during the final pass if the `.blend` file
already has the final engine selected.
