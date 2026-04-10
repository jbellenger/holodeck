const preloadConcurrency = 6;
const loadingIndicatorDelayMillis = 32;

class CancelledActionError extends Error {
  constructor() {
    super("Player action was cancelled");
    this.name = "CancelledActionError";
  }
}

(async function () {
  const { markers, frames, fps, token } = await fetch("./manifest.json").then((resp) => resp.json());
  const frameMillis = 1000 / fps;
  const img = document.getElementById("image");
  const status = document.getElementById("status");
  const message = document.getElementById("message");
  const container = document.getElementById("container");
  const loadingBar = document.getElementById("loading-bar");
  const loadingProgress = document.getElementById("loading-progress");

  let lastActionId = 0;
  let currentFrame = 0;
  let playing = false;
  let ready = false;
  let loadingIndicatorTimeout = null;
  let pendingLoadingState = null;
  const frameUrls = frames.map((framePath) => buildFrameUrl(framePath, token));
  const warmedFrames = new Array(frameUrls.length).fill(false);
  const frameWarmPromises = new Array(frameUrls.length).fill(null);

  function announceStatus(messageText) {
    status.textContent = messageText;
  }

  function showMessage(messageText) {
    announceStatus(messageText);
    hideLoadingProgress();
    message.textContent = messageText;
    message.style.display = "block";
  }

  function hideMessage() {
    message.style.display = "none";
    message.textContent = "";
  }

  function renderLoadingProgress(completed = null, total = null) {
    announceStatus(
      completed !== null && total !== null
        ? `Loading frames ${completed}/${total}`
        : "Loading frames…"
    );
    hideMessage();
    loadingBar.style.display = "block";

    if (completed !== null && total !== null && total > 0) {
      loadingBar.classList.remove("is-indeterminate");
      loadingProgress.style.width = `${(completed / total) * 100}%`;
      loadingProgress.style.transform = "translateX(0)";
      return;
    }

    loadingBar.classList.add("is-indeterminate");
    loadingProgress.style.width = "15%";
    loadingProgress.style.transform = "translateX(-100%)";
  }

  function showLoadingProgress(completed = null, total = null) {
    pendingLoadingState = { completed, total };

    if (loadingBar.style.display === "block") {
      renderLoadingProgress(completed, total);
      return;
    }

    if (loadingIndicatorTimeout !== null) {
      return;
    }

    loadingIndicatorTimeout = setTimeout(() => {
      loadingIndicatorTimeout = null;
      if (!pendingLoadingState) {
        return;
      }

      renderLoadingProgress(pendingLoadingState.completed, pendingLoadingState.total);
    }, loadingIndicatorDelayMillis);
  }

  function hideLoadingProgress() {
    pendingLoadingState = null;

    if (loadingIndicatorTimeout !== null) {
      clearTimeout(loadingIndicatorTimeout);
      loadingIndicatorTimeout = null;
    }

    loadingBar.style.display = "none";
    loadingBar.classList.remove("is-indeterminate");
    loadingProgress.style.width = "15%";
    loadingProgress.style.transform = "translateX(-100%)";
  }

  function showPlayer() {
    img.style.display = "block";
    hideMessage();
    hideLoadingProgress();
  }

  function startAction() {
    lastActionId += 1;
    return lastActionId;
  }

  function isActionActive(actionId) {
    return actionId === lastActionId;
  }

  function assertActionActive(actionId) {
    if (!isActionActive(actionId)) {
      throw new CancelledActionError();
    }
  }

  function assertActionIfProvided(actionId) {
    if (actionId !== null && actionId !== undefined) {
      assertActionActive(actionId);
    }
  }

  function buildFrameUrl(framePath, manifestToken) {
    if (!manifestToken) {
      return framePath;
    }

    const frameUrl = new URL(framePath, window.location.href);
    frameUrl.searchParams.set("v", manifestToken);
    return frameUrl.toString();
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

  async function warmFrame(frameIndex) {
    if (warmedFrames[frameIndex]) {
      return;
    }

    if (frameWarmPromises[frameIndex]) {
      return frameWarmPromises[frameIndex];
    }

    const warmPromise = (async () => {
      const response = await fetch(frameUrls[frameIndex], { cache: "force-cache" });
      if (!response.ok) {
        throw new Error(`Failed to preload frame ${frameUrls[frameIndex]}: ${response.status}`);
      }

      await response.blob();
      warmedFrames[frameIndex] = true;
    })();

    frameWarmPromises[frameIndex] = warmPromise.finally(() => {
      frameWarmPromises[frameIndex] = null;
    });

    return frameWarmPromises[frameIndex];
  }

  async function warmSegment(frame, { actionId = null, showProgress = false, excludeFrame = null } = {}) {
    assertActionIfProvided(actionId);

    const { start, end } = getSegmentBounds(frame);
    const pendingFrames = [];

    for (let frameIndex = start; frameIndex <= end; frameIndex += 1) {
      if (frameIndex === excludeFrame) {
        continue;
      }

      if (!warmedFrames[frameIndex]) {
        pendingFrames.push(frameIndex);
      }
    }

    if (pendingFrames.length === 0) {
      return { start, end };
    }

    let nextPendingIndex = 0;
    let completed = 0;
    if (showProgress) {
      showLoadingProgress(completed, pendingFrames.length);
    }

    async function worker() {
      while (nextPendingIndex < pendingFrames.length) {
        assertActionIfProvided(actionId);
        const pendingIndex = nextPendingIndex;
        nextPendingIndex += 1;
        const frameIndex = pendingFrames[pendingIndex];
        await warmFrame(frameIndex);
        assertActionIfProvided(actionId);
        completed += 1;
        if (showProgress) {
          showLoadingProgress(completed, pendingFrames.length);
        }
      }
    }

    const workerCount = Math.min(preloadConcurrency, pendingFrames.length);
    await Promise.all(Array.from({ length: workerCount }, () => worker()));
    assertActionIfProvided(actionId);
    return { start, end };
  }

  function displayFrame(frame) {
    if (frameUrls.length === 0) {
      return null;
    }

    const clampedFrame = Math.max(0, Math.min(frame, frameUrls.length - 1));
    img.src = frameUrls[clampedFrame];
    currentFrame = clampedFrame;

    if (ready) {
      hideLoadingProgress();
    }

    return clampedFrame;
  }

  async function waitForDisplayedFrame(frame) {
    const clampedFrame = displayFrame(frame);
    if (clampedFrame === null) {
      return;
    }

    await img.decode();
  }

  function seek(frame) {
    const clampedFrame = displayFrame(frame);
    if (clampedFrame === null) {
      return;
    }

    runAsync(() => warmSegment(clampedFrame, { excludeFrame: clampedFrame }));
  }

  function jump(direction) {
    if (!ready) return;

    if (direction === 1) {
      const idx = markers.find((element) => element > currentFrame);
      if (idx === undefined) {
        seek(frameUrls.length - 1);
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

  function togglePlayback() {
    if (playing) {
      playing = false;
      startAction();
      return;
    }

    playing = true;
    runAsync(() => play(currentFrame, startAction()));
  }

  function toggleFullscreen() {
    if (document.fullscreenElement && document.exitFullscreen) {
      document.exitFullscreen().catch((error) => {
        console.error(error);
      });
      return;
    }

    if (!container.requestFullscreen) {
      return;
    }

    container.requestFullscreen().catch((error) => {
      console.error(error);
    });
  }

  function handleTouchAction(clientX) {
    if (!ready) {
      return;
    }

    const bounds = container.getBoundingClientRect();
    const touchX = clientX - bounds.left;

    if (touchX < bounds.width / 2) {
      playing = false;
      startAction();
      jump(-1);
      return;
    }

    togglePlayback();
  }

  async function play(startFrame, actionId) {
    const clampedFrame = displayFrame(startFrame);
    if (clampedFrame === null) {
      return;
    }

    if (!playing) return;
    assertActionActive(actionId);
    await warmSegment(clampedFrame, {
      actionId,
      showProgress: true,
      excludeFrame: clampedFrame,
    });
    hideLoadingProgress();

    const segmentEnd = getSegmentEnd(currentFrame);

    function loop(frame) {
      setTimeout(() => {
        if (!playing || !isActionActive(actionId)) {
          return;
        }

        const nextFrame = frame + 1;
        if (nextFrame > segmentEnd || nextFrame >= frameUrls.length) {
          playing = false;
          return;
        }

        img.src = frameUrls[nextFrame];
        currentFrame = nextFrame;

        const isLast = nextFrame === frameUrls.length - 1;
        const isMarker = markers.includes(nextFrame);
        if (isLast || isMarker) {
          playing = false;
          return;
        }

        loop(nextFrame);
      }, frameMillis);
    }

    loop(currentFrame);
  }

  function runAsync(action) {
    action().catch((error) => {
      if (error instanceof CancelledActionError) {
        hideLoadingProgress();
        return;
      }

      playing = false;
      hideLoadingProgress();
      showMessage("Failed to load frames");
      console.error(error);
    });
  }

  addEventListener("keydown", (event) => {
    if (!ready) return;

    switch (event.code) {
      case "ArrowLeft":
        playing = false;
        startAction();
        jump(-1);
        break;
      case "ArrowRight":
        playing = false;
        startAction();
        jump(1);
        break;
      case "ArrowDown":
      case "Enter":
      case "Space":
        event.preventDefault();
        if (event.repeat) {
          break;
        }

        togglePlayback();
        break;
      case "KeyF":
        event.preventDefault();
        if (event.repeat) {
          break;
        }

        toggleFullscreen();
        break;
    }
  });

  container.addEventListener("touchend", (event) => {
    if (event.changedTouches.length !== 1) {
      return;
    }

    event.preventDefault();
    handleTouchAction(event.changedTouches[0].clientX);
  }, { passive: false });

  try {
    if (frames.length === 0) {
      showMessage("No frames found");
      return;
    }

    const initialActionId = startAction();
    showLoadingProgress();
    await warmFrame(0);
    assertActionActive(initialActionId);
    await waitForDisplayedFrame(0);
    ready = true;
    showPlayer();
    runAsync(() => warmSegment(0, { excludeFrame: 0 }));
  } catch (error) {
    hideLoadingProgress();
    showMessage("Failed to load frames");
    throw error;
  }
})();
