# Holodeck

Holodeck is a command-line tool that renders Blender animations as slide decks
that can be viewed in a web browser.

Because Holodeck works with pre-rendered frames, it can produce slide decks with
higher visual fidelity than a tool like Google Slides, while still feeling
real-time during a presentation.

Holodeck renders frames as avif images, which has excellent compression and is
supported in all browsers.

Gallery: 
- [the demo in this repository](https://jbellenger.github.io/holodeck/)
- [Brute Force Correctness (GraphQLConf 2026)](https://bfc.bellenger.org/)

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

### 3. Build Your Holodeck

Run `build` with a source `.blend` file and an output directory:

```bash
holodeck build path/to/deck.blend dist --title "My Deck"
```

`build` renders the frames, writes `manifest.json`, and installs the browser
player assets into the output directory. The result is a static site that can be
served locally or uploaded to a static host. By default, Holodeck renders both
animation frames and the first, marker, and last frames at 100% resolution over
the same filenames.

Useful build options:

- `--scene` renders a specific Blender scene instead of the active scene.
- `--animation-res-pct` sets the Blender render resolution percentage for animation frames. The default is 100.
- `--animation-scale-pct` scales animation frames after rendering while preserving full-size originals in `render-source/`. The default is 100.
- `--still-res-pct` sets the resolution percentage for first, marker, and last frames. The default is 100.
- `--animation-renderer` overrides the Blend file renderer for animation frames.
- `--still-renderer` overrides the Blend file renderer for first, marker, and last frames.
- `--stills-only` renders first, marker, and last frames and writes a stills-only manifest.
- `--title` sets the generated player page title.

### 4. Play Your Holodeck Locally

Use `serve` to preview an existing Holodeck output directory:

```bash
holodeck serve dist
```

By default, the server binds to port `8000` and opens the player in your default
browser. You can override either behavior:

```bash
holodeck serve dist --port 9000
holodeck serve dist --no-open
```

Common presenter shortcuts:

- Press space or tap to animate to the next marker. A small white pixel appears
  in the bottom-right corner of the visible frame while animation is running.
- Press the left or right arrow keys to jump between markers.
- Press <kbd>F</kbd> or swipe up to enter fullscreen.

Before animating, the player fetches the full frame segment up to the next
marker and decodes a short runway. This keeps S3 or other static-host latency
out of the animation loop.

### 5. Refresh Your Holodeck

Use `refresh` when the rendered frame files already exist, but the player bundle
or manifest needs to be regenerated. A common example is moving timeline markers
after rendering; `refresh` can update `manifest.json` without re-rendering every
frame.

```bash
holodeck refresh path/to/deck.blend dist --title "My Deck"
```

`refresh` reads the Blend file metadata, verifies that the expected rendered
frames exist, rewrites `manifest.json`, and reinstalls the browser player assets.
If the actual frame images changed, use `build` or `render-frames` instead.

### 6. Deploy Your Holodeck

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
aws s3 sync dist s3://your-bucket/path/ \
  --exclude "*" \
  --include "render/*" \
  --include "render-source/*" \
  --cache-control "public, max-age=31536000, immutable"

aws s3 sync dist s3://your-bucket/path/ \
  --exclude "render/*" \
  --exclude "render-source/*" \
  --cache-control "no-cache"
```

The player uses relative asset paths, so the same output can be served from a
domain root or a subdirectory. Frame URLs include a manifest token, so rendered
frames can be cached aggressively while `manifest.json` and player assets stay
fresh.


# Tips And Tricks
## Render A Subset Of Frames
Use `render-frames` with `--frames` when only a few frame images need to be
re-rendered:

```bash
holodeck render-frames path/to/deck.blend dist --frames "48,72-96"
```

Frame ranges are inclusive, and comma-separated segments are allowed. For
example, `"4"`, `"4-10"`, and `"1,2,3,20-24"` are all valid frame specs.

`render-frames` updates files under `render/`, but it does not update
`manifest.json`. Use it for small visual changes when the timing, markers, and
scene length have not changed.

## Workbench Rendering
Renderer overrides let each Holodeck render pass use a different Blender renderer
without changing the saved setting in the `.blend` file. If you omit a renderer
override, that pass uses the renderer already configured in the file.

Workbench rendering is useful when you want fast feedback on timing, camera
motion, and animation. You can render the whole deck with Workbench first:

```bash
holodeck build path/to/deck.blend dist --animation-renderer workbench
```

After the timing feels right, you can re-render selected frames or ranges with
the renderers you want for each pass. This is useful when only part of the deck
needs more visual polish:

```bash
holodeck render-frames path/to/deck.blend dist --frames "48,72-96" --animation-renderer cycles
```

## Rescale Animation Frames Without Rerendering
Use `--animation-scale-pct` when you want Blender to render animation frames at
full resolution, but ship smaller animation frames in the browser bundle:

```bash
holodeck build path/to/deck.blend dist --animation-scale-pct 50
```

This is particularly useful for:
- long decks
- animation heavy decks
- high fps decks
- eevee-rendered decks

This is similar to `--animation-res-pct` in that they can both reduce the download size of animation frames, but different in some key ways. While `--animation-res-pct` can significantly improve render times, it can produce visible artifacts in eevee-rendered decks when transitioning. `--animation-res-pct` is immune from visible artifacts in eevee, but at the cost of significantly slower render times.

Holodeck stores full-size animation frame sources in `render-source/` using the
same filenames as `render/`. To regenerate playable animation frames from those
preserved sources without opening Blender, run:

```bash
holodeck rescale-frames dist --animation-scale-pct 75
holodeck rescale-frames dist --animation-scale-pct 100
```

The `100` form restores animation frames by copying the preserved source bytes
back into `render/`. Rescaling uses `manifest.json` to leave first, marker, and
last still frames untouched.
