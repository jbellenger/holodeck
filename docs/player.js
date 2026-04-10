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
  let frameSources = [];

  function setStatus(message) {
    status.textContent = message;
  }

  function showPlayer() {
    status.style.display = "none";
    img.style.display = "block";
  }

  async function preloadFrame(frameUrl) {
    const response = await fetch(frameUrl);
    if (!response.ok) {
      throw new Error(`Failed to preload frame ${frameUrl}: ${response.status}`);
    }

    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const preloadImage = new Image();
    preloadImage.src = objectUrl;
    await preloadImage.decode();
    return objectUrl;
  }

  async function preloadFrames() {
    const sources = new Array(frames.length);
    let nextIndex = 0;
    let completed = 0;

    setStatus(`Loading frames 0/${frames.length}`);

    async function worker() {
      while (nextIndex < frames.length) {
        const frameIndex = nextIndex;
        nextIndex += 1;
        const frameUrl = `${frames[frameIndex]}?cacheBust=${cacheBust}`;
        sources[frameIndex] = await preloadFrame(frameUrl);
        completed += 1;
        setStatus(`Loading frames ${completed}/${frames.length}`);
      }
    }

    const workerCount = Math.min(preloadConcurrency, frames.length);
    await Promise.all(Array.from({ length: workerCount }, () => worker()));
    return sources;
  }

  function seek(frame) {
    frame = Math.max(0, frame);
    frame = Math.min(frame, frameSources.length - 1);
    img.src = frameSources[frame];
    currentFrame = frame;
  }

  function jump(direction) {
    if (!ready) return;

    if (direction === 1) {
      const idx = markers.find((element) => element > currentFrame);
      if (idx === undefined) {
        seek(frameSources.length - 1);
      } else {
        seek(idx);
      }
    } else if (direction === -1) {
      const idx = markers.findLast((element) => element < currentFrame);
      if (idx === undefined) {
        seek(0);
      } else {
        seek(idx);
      }
    } else {
      throw new Error(`invalid jump direction: ${direction}`);
    }
  }

  function play(startFrame) {
    seek(startFrame);

    if (!playing) return;
    let actionId = ++lastActionId;
    function loop(frame) {
      actionId = ++lastActionId;
      setTimeout(() => {
        if (actionId !== lastActionId) return;
        const nextFrame = frame + 1;

        if (nextFrame >= frameSources.length) {
          playing = false;
          return;
        }

        seek(nextFrame);

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

  addEventListener("keydown", (event) => {
    if (!ready) return;

    switch (event.code) {
      case "ArrowLeft":
        jump(-1);
        break;
      case "ArrowRight":
        jump(1);
        break;
      case "Space":
        playing = !playing;
        ++lastActionId;
        play(currentFrame);
        break;
    }
  });

  try {
    frameSources = await preloadFrames();
    ready = true;
    seek(0);
    showPlayer();
  } catch (error) {
    setStatus("Failed to load frames");
    throw error;
  }

  addEventListener("beforeunload", () => {
    frameSources.forEach((frameSource) => URL.revokeObjectURL(frameSource));
  });
})();
