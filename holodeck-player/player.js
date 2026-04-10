const cacheBust = performance.now();
const preloadConcurrency = 6;

(async function () {
  const { markers, frames, fps } = await fetch("./manifest.json").then((resp) => resp.json());
  const frameMillis = 1000 / fps;
  const img = document.getElementById("image");
  const status = document.getElementById("status");

  let lastActionId = 0;
  let currentFrame = 0;
  let playing = false;
  let ready = false;
  let frameSources = new Array(frames.length).fill(null);

  function showStatus(message) {
    status.textContent = message;
    status.style.display = "block";
  }

  function hideStatus() {
    status.style.display = "none";
  }

  function showPlayer() {
    img.style.display = "block";
    hideStatus();
  }

  function getSegmentEnd(frame) {
    const nextMarker = markers.find((element) => element > frame);
    return nextMarker === undefined ? frames.length - 1 : nextMarker;
  }

  function getSegmentBounds(frame) {
    const clampedFrame = Math.max(0, Math.min(frame, frames.length - 1));
    return {
      start: clampedFrame,
      end: getSegmentEnd(clampedFrame),
    };
  }

  async function preloadFrame(frameIndex) {
    if (frameSources[frameIndex]) {
      return frameSources[frameIndex];
    }

    const frameUrl = `${frames[frameIndex]}?cacheBust=${cacheBust}`;
    const response = await fetch(frameUrl);
    if (!response.ok) {
      throw new Error(`Failed to preload frame ${frameUrl}: ${response.status}`);
    }

    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const preloadImage = new Image();
    preloadImage.src = objectUrl;
    await preloadImage.decode();
    frameSources[frameIndex] = objectUrl;
    return objectUrl;
  }

  async function ensureSegmentLoaded(frame) {
    const { start, end } = getSegmentBounds(frame);
    const pendingFrames = [];

    for (let frameIndex = start; frameIndex <= end; frameIndex += 1) {
      if (!frameSources[frameIndex]) {
        pendingFrames.push(frameIndex);
      }
    }

    if (pendingFrames.length === 0) {
      return { start, end };
    }

    let nextPendingIndex = 0;
    let completed = 0;
    showStatus(`Loading frames ${completed}/${pendingFrames.length}`);

    async function worker() {
      while (nextPendingIndex < pendingFrames.length) {
        const pendingIndex = nextPendingIndex;
        nextPendingIndex += 1;
        const frameIndex = pendingFrames[pendingIndex];
        await preloadFrame(frameIndex);
        completed += 1;
        showStatus(`Loading frames ${completed}/${pendingFrames.length}`);
      }
    }

    const workerCount = Math.min(preloadConcurrency, pendingFrames.length);
    await Promise.all(Array.from({ length: workerCount }, () => worker()));
    return { start, end };
  }

  function releaseFramesOutside(start, end) {
    for (let frameIndex = 0; frameIndex < frameSources.length; frameIndex += 1) {
      const frameSource = frameSources[frameIndex];
      if (!frameSource) {
        continue;
      }
      if (frameIndex >= start && frameIndex <= end) {
        continue;
      }

      URL.revokeObjectURL(frameSource);
      frameSources[frameIndex] = null;
    }
  }

  async function seek(frame) {
    if (frames.length === 0) {
      return;
    }

    const { start, end } = await ensureSegmentLoaded(frame);
    const clampedFrame = Math.max(0, Math.min(frame, frameSources.length - 1));

    img.src = frameSources[clampedFrame];
    currentFrame = clampedFrame;
    releaseFramesOutside(start, end);

    if (ready) {
      hideStatus();
    }
  }

  async function jump(direction) {
    if (!ready) return;

    if (direction === 1) {
      const idx = markers.find((element) => element > currentFrame);
      if (idx === undefined) {
        await seek(frameSources.length - 1);
      } else {
        await seek(idx);
      }
    } else if (direction === -1) {
      const idx = markers.findLast((element) => element < currentFrame);
      if (idx === undefined) {
        await seek(0);
      } else {
        await seek(idx);
      }
    } else {
      throw new Error(`invalid jump direction: ${direction}`);
    }
  }

  async function play(startFrame) {
    await seek(startFrame);

    if (!playing) return;
    let actionId = ++lastActionId;
    const segmentEnd = getSegmentEnd(currentFrame);

    function loop(frame) {
      actionId = ++lastActionId;
      setTimeout(() => {
        if (actionId !== lastActionId) return;
        const nextFrame = frame + 1;

        if (nextFrame > segmentEnd || nextFrame >= frameSources.length) {
          playing = false;
          return;
        }

        img.src = frameSources[nextFrame];
        currentFrame = nextFrame;
        releaseFramesOutside(nextFrame, segmentEnd);

        const isLast = nextFrame === frameSources.length - 1;
        const isMarker = markers.includes(nextFrame);
        if (isLast || isMarker) {
          playing = false;
          return;
        }
        loop(nextFrame);
      }, frameMillis);
    }

    loop(startFrame);
  }

  function runAsync(action) {
    action().catch((error) => {
      playing = false;
      showStatus("Failed to load frames");
      console.error(error);
    });
  }

  addEventListener("keydown", (event) => {
    if (!ready) return;

    switch (event.code) {
      case "ArrowLeft":
        runAsync(() => jump(-1));
        break;
      case "ArrowRight":
        runAsync(() => jump(1));
        break;
      case "Space":
        playing = !playing;
        ++lastActionId;
        if (playing) {
          runAsync(() => play(currentFrame));
        }
        break;
    }
  });

  try {
    if (frames.length === 0) {
      showStatus("No frames found");
      return;
    }

    await seek(0);
    ready = true;
    showPlayer();
  } catch (error) {
    showStatus("Failed to load frames");
    throw error;
  }

  addEventListener("beforeunload", () => {
    frameSources.forEach((frameSource) => {
      if (frameSource) {
        URL.revokeObjectURL(frameSource);
      }
    });
  });
})();
