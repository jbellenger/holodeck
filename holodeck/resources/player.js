const preloadConcurrency = 6;
const loadingIndicatorDelayMillis = 32;
const optimisticPreloadSegmentCount = 2;
const swipeThresholdPixels = 48;
const decodedFrameBufferAhead = 6;
const decodedFrameBufferBehind = 1;

class CancelledActionError extends Error {
  constructor() {
    super("Player action was cancelled");
    this.name = "CancelledActionError";
  }
}

(async function () {
  const { markers, frames, fps, token } = await fetch("./manifest.json").then((resp) => resp.json());
  const frameMillis = 1000 / fps;
  const canvas = document.getElementById("canvas");
  const context = canvas.getContext("2d", { alpha: false, desynchronized: true });
  const status = document.getElementById("status");
  const message = document.getElementById("message");
  const container = document.getElementById("container");
  const loadingBar = document.getElementById("loading-bar");
  const loadingProgress = document.getElementById("loading-progress");
  const markerSet = new Set(markers);

  if (!context) {
    throw new Error("Unable to acquire 2D canvas context.");
  }

  let lastActionId = 0;
  let currentFrame = 0;
  let currentFrameWidth = 0;
  let currentFrameHeight = 0;
  let playing = false;
  let ready = false;
  let loadingIndicatorTimeout = null;
  let pendingLoadingState = null;
  let touchStartPoint = null;
  let resizeQueued = false;
  const frameUrls = frames.map((framePath) => buildFrameUrl(framePath, token));
  const warmedFrames = new Array(frameUrls.length).fill(false);
  const frameWarmPromises = new Array(frameUrls.length).fill(null);
  const decodedFrames = new Map();
  const decodedFramePromises = new Map();

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

  function resizeCanvas() {
    const pixelRatio = window.devicePixelRatio || 1;
    const width = Math.max(1, Math.round(container.clientWidth * pixelRatio));
    const height = Math.max(1, Math.round(container.clientHeight * pixelRatio));

    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
  }

  function drawFrame(source, width, height) {
    resizeCanvas();
    context.fillStyle = "#000";
    context.fillRect(0, 0, canvas.width, canvas.height);

    const scale = Math.min(canvas.width / width, canvas.height / height);
    const drawWidth = width * scale;
    const drawHeight = height * scale;
    const dx = (canvas.width - drawWidth) / 2;
    const dy = (canvas.height - drawHeight) / 2;

    context.drawImage(source, dx, dy, drawWidth, drawHeight);
  }

  function showPlayer() {
    canvas.style.display = "block";
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

  function getPreloadSegmentStarts(frame, segmentCountAhead = optimisticPreloadSegmentCount) {
    if (frameUrls.length === 0) {
      return [];
    }

    const starts = [Math.max(0, Math.min(frame, frameUrls.length - 1))];

    while (starts.length <= segmentCountAhead) {
      const nextStart = getSegmentEnd(starts[starts.length - 1]);
      if (nextStart <= starts[starts.length - 1]) {
        break;
      }

      starts.push(nextStart);
      if (nextStart === frameUrls.length - 1) {
        break;
      }
    }

    return starts;
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

  function releaseDecodedFrame(frameIndex) {
    const entry = decodedFrames.get(frameIndex);
    if (!entry) {
      return;
    }

    entry.release();
    decodedFrames.delete(frameIndex);
  }

  function pruneDecodedFrames(referenceFrame) {
    const keepStart = Math.max(0, referenceFrame - decodedFrameBufferBehind);
    const keepEnd = Math.min(frameUrls.length - 1, referenceFrame + decodedFrameBufferAhead);

    for (const frameIndex of decodedFrames.keys()) {
      if (frameIndex < keepStart || frameIndex > keepEnd) {
        releaseDecodedFrame(frameIndex);
      }
    }
  }

  async function decodeBlob(blob) {
    if (typeof createImageBitmap === "function") {
      const bitmap = await createImageBitmap(blob);
      return {
        source: bitmap,
        width: bitmap.width,
        height: bitmap.height,
        release() {
          bitmap.close();
        },
      };
    }

    const objectUrl = URL.createObjectURL(blob);
    const image = new Image();
    image.decoding = "async";
    image.src = objectUrl;

    try {
      await image.decode();
      return {
        source: image,
        width: image.naturalWidth,
        height: image.naturalHeight,
        release() {
          URL.revokeObjectURL(objectUrl);
        },
      };
    } catch (error) {
      URL.revokeObjectURL(objectUrl);
      throw error;
    }
  }

  async function getDecodedFrame(frameIndex, { actionId = null } = {}) {
    assertActionIfProvided(actionId);

    const cachedFrame = decodedFrames.get(frameIndex);
    if (cachedFrame) {
      return cachedFrame;
    }

    if (decodedFramePromises.has(frameIndex)) {
      return decodedFramePromises.get(frameIndex);
    }

    const decodePromise = (async () => {
      await warmFrame(frameIndex);
      assertActionIfProvided(actionId);

      const response = await fetch(frameUrls[frameIndex], { cache: "force-cache" });
      if (!response.ok) {
        throw new Error(`Failed to decode frame ${frameUrls[frameIndex]}: ${response.status}`);
      }

      const blob = await response.blob();
      assertActionIfProvided(actionId);
      const decodedFrame = await decodeBlob(blob);

      try {
        assertActionIfProvided(actionId);
      } catch (error) {
        decodedFrame.release();
        throw error;
      }

      decodedFrames.set(frameIndex, decodedFrame);
      return decodedFrame;
    })();

    decodedFramePromises.set(
      frameIndex,
      decodePromise.finally(() => {
        decodedFramePromises.delete(frameIndex);
      })
    );

    return decodedFramePromises.get(frameIndex);
  }

  async function fillDecodedBuffer(frame, { actionId = null } = {}) {
    assertActionIfProvided(actionId);

    const segmentEnd = getSegmentEnd(frame);
    const bufferEnd = Math.min(segmentEnd, frame + decodedFrameBufferAhead);

    for (let frameIndex = frame; frameIndex <= bufferEnd; frameIndex += 1) {
      await getDecodedFrame(frameIndex, { actionId });
      assertActionIfProvided(actionId);
      pruneDecodedFrames(frameIndex);
    }
  }

  function getBestDecodedFrame(startFrame, targetFrame) {
    for (let frameIndex = targetFrame; frameIndex >= startFrame; frameIndex -= 1) {
      if (decodedFrames.has(frameIndex)) {
        return frameIndex;
      }
    }

    return null;
  }

  async function renderFrame(frame, { actionId = null } = {}) {
    if (frameUrls.length === 0) {
      return null;
    }

    const clampedFrame = Math.max(0, Math.min(frame, frameUrls.length - 1));
    const decodedFrame = await getDecodedFrame(clampedFrame, { actionId });
    assertActionIfProvided(actionId);

    drawFrame(decodedFrame.source, decodedFrame.width, decodedFrame.height);
    currentFrame = clampedFrame;
    currentFrameWidth = decodedFrame.width;
    currentFrameHeight = decodedFrame.height;
    pruneDecodedFrames(clampedFrame);

    if (ready) {
      hideLoadingProgress();
    }

    return clampedFrame;
  }

  async function warmOptimisticSegments(frame, { excludeFrame = null } = {}) {
    const segmentStarts = getPreloadSegmentStarts(frame);

    for (let index = 0; index < segmentStarts.length; index += 1) {
      await warmSegment(segmentStarts[index], {
        excludeFrame: index === 0 ? excludeFrame : null,
      });
    }
  }

  function scheduleOptimisticPreload(frame, { excludeFrame = null } = {}) {
    runBackground(() => warmOptimisticSegments(frame, { excludeFrame }));
  }

  function scheduleDecodedBuffer(frame, { actionId = null } = {}) {
    runBackground(() => fillDecodedBuffer(frame, { actionId }));
  }

  function queueCurrentFrameRedraw() {
    if (!ready || resizeQueued) {
      return;
    }

    resizeQueued = true;
    requestAnimationFrame(() => {
      resizeQueued = false;
      const decodedFrame = decodedFrames.get(currentFrame);
      if (!decodedFrame) {
        return;
      }

      drawFrame(decodedFrame.source, decodedFrame.width, decodedFrame.height);
    });
  }

  function seek(frame) {
    const actionId = lastActionId;
    runAsync(async () => {
      const clampedFrame = await renderFrame(frame, { actionId });
      if (clampedFrame === null) {
        return;
      }

      scheduleDecodedBuffer(clampedFrame, { actionId });
      scheduleOptimisticPreload(clampedFrame, { excludeFrame: clampedFrame });
    });
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

  async function tryLockLandscapeOrientation() {
    if (!screen.orientation || !screen.orientation.lock) {
      return;
    }

    try {
      await screen.orientation.lock("landscape");
    } catch (error) {
      console.error(error);
    }
  }

  function unlockOrientationIfSupported() {
    if (!screen.orientation || !screen.orientation.unlock) {
      return;
    }

    screen.orientation.unlock();
  }

  function isWideImage() {
    return currentFrameWidth > currentFrameHeight;
  }

  async function enableFullscreen({ preferLandscape = false } = {}) {
    if (!container.requestFullscreen || document.fullscreenElement) {
      return;
    }

    try {
      await container.requestFullscreen();
      if (preferLandscape && isWideImage()) {
        await tryLockLandscapeOrientation();
      }
    } catch (error) {
      console.error(error);
    }
  }

  async function disableFullscreen() {
    if (!document.fullscreenElement || !document.exitFullscreen) {
      return;
    }

    unlockOrientationIfSupported();
    try {
      await document.exitFullscreen();
    } catch (error) {
      console.error(error);
    }
  }

  function toggleFullscreen() {
    if (document.fullscreenElement) {
      void disableFullscreen();
      return;
    }

    void enableFullscreen();
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

  function handleTouchGesture(endPoint) {
    if (!touchStartPoint || !ready) {
      return;
    }

    const deltaX = endPoint.clientX - touchStartPoint.clientX;
    const deltaY = endPoint.clientY - touchStartPoint.clientY;
    const isVerticalSwipe = Math.abs(deltaY) >= swipeThresholdPixels && Math.abs(deltaY) > Math.abs(deltaX);

    if (isVerticalSwipe) {
      if (deltaY < 0) {
        void enableFullscreen({ preferLandscape: true });
      } else {
        void disableFullscreen();
      }
      return;
    }

    handleTouchAction(endPoint.clientX);
  }

  async function play(startFrame, actionId) {
    const clampedFrame = await renderFrame(startFrame, { actionId });
    if (clampedFrame === null) {
      return;
    }

    if (!playing) {
      return;
    }

    assertActionActive(actionId);
    await warmSegment(clampedFrame, {
      actionId,
      showProgress: true,
      excludeFrame: clampedFrame,
    });
    await fillDecodedBuffer(clampedFrame, { actionId });
    hideLoadingProgress();
    scheduleOptimisticPreload(clampedFrame, { excludeFrame: clampedFrame });

    const segmentEnd = getSegmentEnd(clampedFrame);
    const startTimestamp = performance.now();

    function loop(timestamp) {
      if (!playing || !isActionActive(actionId)) {
        return;
      }

      const elapsedFrames = Math.floor((timestamp - startTimestamp) / frameMillis);
      const targetFrame = Math.min(clampedFrame + elapsedFrames, segmentEnd, frameUrls.length - 1);

      if (targetFrame > currentFrame) {
        const decodedFrameIndex = getBestDecodedFrame(currentFrame + 1, targetFrame);
        if (decodedFrameIndex !== null) {
          const decodedFrame = decodedFrames.get(decodedFrameIndex);
          drawFrame(decodedFrame.source, decodedFrame.width, decodedFrame.height);
          currentFrame = decodedFrameIndex;
          currentFrameWidth = decodedFrame.width;
          currentFrameHeight = decodedFrame.height;
          pruneDecodedFrames(decodedFrameIndex);
          scheduleDecodedBuffer(decodedFrameIndex, { actionId });
        }
      }

      const isLast = currentFrame === frameUrls.length - 1;
      const isMarker = currentFrame !== clampedFrame && markerSet.has(currentFrame);
      if (currentFrame >= segmentEnd || isLast || isMarker) {
        playing = false;
        scheduleOptimisticPreload(currentFrame, { excludeFrame: currentFrame });
        return;
      }

      requestAnimationFrame(loop);
    }

    requestAnimationFrame(loop);
  }

  function handleAsyncError(error, { hideProgressOnCancel = false } = {}) {
    if (error instanceof CancelledActionError) {
      if (hideProgressOnCancel) {
        hideLoadingProgress();
      }
      return;
    }

    playing = false;
    hideLoadingProgress();
    showMessage("Failed to load frames");
    console.error(error);
  }

  function runAsync(action) {
    action().catch((error) => {
      handleAsyncError(error, { hideProgressOnCancel: true });
    });
  }

  function runBackground(action) {
    action().catch((error) => {
      handleAsyncError(error);
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

  addEventListener("resize", queueCurrentFrameRedraw);
  document.addEventListener("fullscreenchange", queueCurrentFrameRedraw);

  container.addEventListener("touchstart", (event) => {
    if (event.touches.length !== 1) {
      touchStartPoint = null;
      return;
    }

    touchStartPoint = {
      clientX: event.touches[0].clientX,
      clientY: event.touches[0].clientY,
    };
  }, { passive: true });

  container.addEventListener("touchcancel", () => {
    touchStartPoint = null;
  });

  container.addEventListener("touchend", (event) => {
    if (event.changedTouches.length !== 1) {
      touchStartPoint = null;
      return;
    }

    event.preventDefault();
    handleTouchGesture(event.changedTouches[0]);
    touchStartPoint = null;
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
    await renderFrame(0, { actionId: initialActionId });
    ready = true;
    showPlayer();
    scheduleDecodedBuffer(0, { actionId: initialActionId });
    scheduleOptimisticPreload(0, { excludeFrame: 0 });
  } catch (error) {
    hideLoadingProgress();
    showMessage("Failed to load frames");
    throw error;
  }
})();
