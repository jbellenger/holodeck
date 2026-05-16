const loadingIndicatorDelayMillis = 32;
const frameCacheWarmConcurrency = 3;
const aggressiveFrameCacheLimit = 5000;
const swipeThresholdPixels = 48;
const decodedFrameBufferAhead = 18;
const decodedFrameBufferBehind = 1;
const decodedFrameConcurrency = 4;
const playbackIndicatorSize = 2;
const advanceHintDurationMillis = 5000;

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
  const advanceHint = document.getElementById("advance-hint");
  const container = document.getElementById("container");
  const loadingBar = document.getElementById("loading-bar");
  const loadingProgress = document.getElementById("loading-progress");
  const playbackIndicator = document.getElementById("playback-indicator");
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
  let canvasSizeDirty = true;
  let canvasCssWidth = 0;
  let canvasCssHeight = 0;
  let canvasPixelRatio = 0;
  let advanceHintDismissed = false;
  let advanceHintShown = false;
  let advanceHintHideAt = 0;
  let advanceHintTimeout = null;
  let screenWakeLock = null;
  let screenWakeLockRequest = null;
  let playbackLoopActive = false;
  let decodedBufferScheduled = false;
  let decodedBufferRequest = null;
  let frameCacheWarmRunning = false;
  let allFramesCacheWarmQueued = false;
  const frameUrls = frames.map((framePath) => buildFrameUrl(framePath, token));
  const warmedFrames = new Array(frameUrls.length).fill(false);
  const warmedFrameBlobs = new Array(frameUrls.length).fill(null);
  const frameWarmPromises = new Array(frameUrls.length).fill(null);
  const decodedFrames = new Map();
  const decodedFramePromises = new Map();
  const frameCacheWarmQueue = [];
  const frameCacheWarmQueued = new Set();

  function announceStatus(messageText) {
    status.textContent = messageText;
  }

  function showMessage(messageText) {
    announceStatus(messageText);
    dismissAdvanceHint();
    hideLoadingProgress();
    message.textContent = messageText;
    message.style.display = "block";
  }

  function hideMessage() {
    message.style.display = "none";
    message.textContent = "";
  }

  function isTouchNavigationDevice() {
    return (
      (window.matchMedia && window.matchMedia("(pointer: coarse)").matches) ||
      navigator.maxTouchPoints > 0
    );
  }

  function getAdvanceHintText() {
    return isTouchNavigationDevice() ? "Tap to advance" : "Press space to advance";
  }

  function scheduleAdvanceHintTimeout() {
    if (advanceHintTimeout !== null) {
      clearTimeout(advanceHintTimeout);
    }

    advanceHintTimeout = setTimeout(
      dismissAdvanceHint,
      Math.max(0, advanceHintHideAt - Date.now())
    );
  }

  function showAdvanceHintWhenVisible() {
    if (advanceHintDismissed || advanceHintShown || !ready || document.hidden) {
      return;
    }

    advanceHint.textContent = getAdvanceHintText();
    advanceHint.hidden = false;
    advanceHintShown = true;
    advanceHintHideAt = Date.now() + advanceHintDurationMillis;
    scheduleAdvanceHintTimeout();
  }

  function dismissAdvanceHint() {
    advanceHintDismissed = true;

    if (advanceHintTimeout !== null) {
      clearTimeout(advanceHintTimeout);
      advanceHintTimeout = null;
    }

    advanceHint.hidden = true;
    advanceHint.textContent = "";
  }

  function handleVisibilityChange() {
    if (advanceHintShown && Date.now() >= advanceHintHideAt) {
      dismissAdvanceHint();
    } else if (advanceHintShown) {
      scheduleAdvanceHintTimeout();
    } else {
      showAdvanceHintWhenVisible();
    }

    if (document.hidden) {
      void releaseScreenWakeLock();
      return;
    }

    void requestScreenWakeLock();
  }

  function showPlaybackIndicator() {
    playbackIndicator.hidden = false;
  }

  function hidePlaybackIndicator() {
    playbackIndicator.hidden = true;
  }

  function updatePlaybackIndicatorPosition(frameX, frameY, frameWidth, frameHeight) {
    const cssScaleX = canvasCssWidth / canvas.width;
    const cssScaleY = canvasCssHeight / canvas.height;
    const frameRight = (frameX + frameWidth) * cssScaleX;
    const frameBottom = (frameY + frameHeight) * cssScaleY;
    const indicatorX = Math.max(0, frameRight - playbackIndicatorSize);
    const indicatorY = Math.max(0, frameBottom - playbackIndicatorSize);

    playbackIndicator.style.transform = `translate3d(${indicatorX}px, ${indicatorY}px, 0)`;
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
    canvasPixelRatio = window.devicePixelRatio || 1;
    canvasCssWidth = Math.max(1, container.clientWidth);
    canvasCssHeight = Math.max(1, container.clientHeight);

    const width = Math.max(1, Math.round(canvasCssWidth * canvasPixelRatio));
    const height = Math.max(1, Math.round(canvasCssHeight * canvasPixelRatio));

    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    canvasSizeDirty = false;
  }

  function ensureCanvasSize() {
    if (canvasSizeDirty || canvasPixelRatio !== (window.devicePixelRatio || 1)) {
      resizeCanvas();
    }
  }

  function fillFrameBackdrop(frameX, frameY, frameWidth, frameHeight) {
    const frameRight = frameX + frameWidth;
    const frameBottom = frameY + frameHeight;
    const coversCanvas =
      frameX <= 0 &&
      frameY <= 0 &&
      frameRight >= canvas.width &&
      frameBottom >= canvas.height;

    if (coversCanvas) {
      return;
    }

    context.fillStyle = "#000";

    if (frameY > 0) {
      context.fillRect(0, 0, canvas.width, frameY);
      context.fillRect(0, frameBottom, canvas.width, canvas.height - frameBottom);
    }

    if (frameX > 0) {
      context.fillRect(0, frameY, frameX, frameHeight);
      context.fillRect(frameRight, frameY, canvas.width - frameRight, frameHeight);
    }
  }

  function drawFrame(source, width, height) {
    ensureCanvasSize();

    const scale = Math.min(canvas.width / width, canvas.height / height);
    const drawWidth = width * scale;
    const drawHeight = height * scale;
    const dx = (canvas.width - drawWidth) / 2;
    const dy = (canvas.height - drawHeight) / 2;

    fillFrameBackdrop(dx, dy, drawWidth, drawHeight);
    context.drawImage(source, dx, dy, drawWidth, drawHeight);
    updatePlaybackIndicatorPosition(dx, dy, drawWidth, drawHeight);
  }

  function showPlayer() {
    canvas.style.display = "block";
    hideMessage();
    hideLoadingProgress();
  }

  function startAction() {
    hidePlaybackIndicator();
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

  function getFrameCacheWarmOrder(frame) {
    const clampedFrame = Math.max(0, Math.min(frame, frameUrls.length - 1));
    const orderedFrames = [];

    for (let frameIndex = clampedFrame; frameIndex < frameUrls.length; frameIndex += 1) {
      orderedFrames.push(frameIndex);
    }

    for (let frameIndex = 0; frameIndex < clampedFrame; frameIndex += 1) {
      orderedFrames.push(frameIndex);
    }

    return orderedFrames;
  }

  function getFrameWindow(frame, frameCount) {
    const startFrame = Math.max(0, Math.min(frame, frameUrls.length - 1));
    const endFrame = Math.min(frameUrls.length - 1, startFrame + frameCount - 1);
    const frameWindow = [];

    for (let frameIndex = startFrame; frameIndex <= endFrame; frameIndex += 1) {
      frameWindow.push(frameIndex);
    }

    return frameWindow;
  }

  async function warmFrame(frameIndex, { retainBlob = true } = {}) {
    if (retainBlob && warmedFrameBlobs[frameIndex]) {
      return warmedFrameBlobs[frameIndex];
    }

    if (frameWarmPromises[frameIndex]) {
      const blob = await frameWarmPromises[frameIndex];
      if (retainBlob) {
        warmedFrameBlobs[frameIndex] = blob;
        return blob;
      }

      return null;
    }

    if (warmedFrames[frameIndex]) {
      return null;
    }

    const warmPromise = (async () => {
      const response = await fetch(frameUrls[frameIndex], { cache: "force-cache" });
      if (!response.ok) {
        throw new Error(`Failed to preload frame ${frameUrls[frameIndex]}: ${response.status}`);
      }

      const blob = await response.blob();
      warmedFrames[frameIndex] = true;
      return blob;
    })();

    frameWarmPromises[frameIndex] = warmPromise.finally(() => {
      frameWarmPromises[frameIndex] = null;
    });

    const blob = await frameWarmPromises[frameIndex];
    if (retainBlob) {
      warmedFrameBlobs[frameIndex] = blob;
      return blob;
    }

    return null;
  }

  function moveQueuedFrameToFront(frameIndex, prioritizedFrames) {
    const existingIndex = frameCacheWarmQueue.indexOf(frameIndex);
    if (existingIndex === -1) {
      return;
    }

    frameCacheWarmQueue.splice(existingIndex, 1);
    prioritizedFrames.push(frameIndex);
  }

  function queueFrameCacheWarm(frameIndexes, { front = false } = {}) {
    const prioritizedFrames = [];

    for (const frameIndex of frameIndexes) {
      if (frameIndex < 0 || frameIndex >= frameUrls.length || warmedFrames[frameIndex]) {
        continue;
      }

      if (frameCacheWarmQueued.has(frameIndex)) {
        if (front) {
          moveQueuedFrameToFront(frameIndex, prioritizedFrames);
        }
        continue;
      }

      frameCacheWarmQueued.add(frameIndex);
      if (front) {
        prioritizedFrames.push(frameIndex);
      } else {
        frameCacheWarmQueue.push(frameIndex);
      }
    }

    if (prioritizedFrames.length > 0) {
      frameCacheWarmQueue.unshift(...prioritizedFrames);
    }

    if (frameCacheWarmQueue.length > 0 && !frameCacheWarmRunning) {
      runBackground(runFrameCacheWarmQueue, { fatal: false });
    }
  }

  async function runFrameCacheWarmQueue() {
    if (frameCacheWarmRunning) {
      return;
    }

    frameCacheWarmRunning = true;

    async function worker() {
      while (frameCacheWarmQueue.length > 0) {
        const frameIndex = frameCacheWarmQueue.shift();
        frameCacheWarmQueued.delete(frameIndex);

        if (warmedFrames[frameIndex]) {
          continue;
        }

        try {
          await warmFrame(frameIndex, { retainBlob: false });
        } catch (error) {
          console.warn(error);
        }
      }
    }

    try {
      const workerCount = Math.min(frameCacheWarmConcurrency, frameCacheWarmQueue.length);
      await Promise.all(Array.from({ length: workerCount }, () => worker()));
    } finally {
      frameCacheWarmRunning = false;
      if (frameCacheWarmQueue.length > 0) {
        runBackground(runFrameCacheWarmQueue, { fatal: false });
      }
    }
  }

  function scheduleFrameCacheWarm(frame) {
    if (frameUrls.length === 0) {
      return;
    }

    queueFrameCacheWarm(getFrameWindow(frame, decodedFrameBufferAhead * 4), { front: true });

    if (allFramesCacheWarmQueued || frameUrls.length > aggressiveFrameCacheLimit) {
      return;
    }

    allFramesCacheWarmQueued = true;
    queueFrameCacheWarm(getFrameCacheWarmOrder(frame));
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
      const decodedFrame = await decodedFramePromises.get(frameIndex);
      assertActionIfProvided(actionId);
      return decodedFrame;
    }

    const decodePromise = (async () => {
      const warmedBlob = await warmFrame(frameIndex);

      let blob = warmedBlob;
      if (!blob) {
        const response = await fetch(frameUrls[frameIndex], { cache: "force-cache" });
        if (!response.ok) {
          throw new Error(`Failed to decode frame ${frameUrls[frameIndex]}: ${response.status}`);
        }

        blob = await response.blob();
        warmedFrames[frameIndex] = true;
      }
      const decodedFrame = await decodeBlob(blob);

      decodedFrames.set(frameIndex, decodedFrame);
      warmedFrameBlobs[frameIndex] = null;
      return decodedFrame;
    })();

    decodedFramePromises.set(
      frameIndex,
      decodePromise.finally(() => {
        decodedFramePromises.delete(frameIndex);
      })
    );

    const decodedFrame = await decodedFramePromises.get(frameIndex);
    assertActionIfProvided(actionId);
    return decodedFrame;
  }

  async function fillDecodedBuffer(frame, { actionId = null } = {}) {
    assertActionIfProvided(actionId);

    const segmentEnd = getSegmentEnd(frame);
    const bufferEnd = Math.min(segmentEnd, frame + decodedFrameBufferAhead);
    const pendingFrames = [];

    for (let frameIndex = frame; frameIndex <= bufferEnd; frameIndex += 1) {
      if (!decodedFrames.has(frameIndex)) {
        pendingFrames.push(frameIndex);
      }
    }

    if (pendingFrames.length === 0) {
      pruneDecodedFrames(Math.max(frame, currentFrame));
      return;
    }

    let nextPendingIndex = 0;

    async function worker() {
      while (nextPendingIndex < pendingFrames.length) {
        assertActionIfProvided(actionId);
        const pendingIndex = nextPendingIndex;
        nextPendingIndex += 1;
        const frameIndex = pendingFrames[pendingIndex];
        await getDecodedFrame(frameIndex, { actionId });
        assertActionIfProvided(actionId);
        pruneDecodedFrames(Math.max(frame, currentFrame));
      }
    }

    const workerCount = Math.min(decodedFrameConcurrency, pendingFrames.length);
    await Promise.all(Array.from({ length: workerCount }, () => worker()));
    assertActionIfProvided(actionId);
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

  function scheduleDecodedBuffer(frame, { actionId = null } = {}) {
    decodedBufferRequest = { frame, actionId };

    if (decodedBufferScheduled) {
      return;
    }

    decodedBufferScheduled = true;
    runBackground(async () => {
      try {
        while (decodedBufferRequest) {
          const request = decodedBufferRequest;
          decodedBufferRequest = null;
          await fillDecodedBuffer(request.frame, { actionId: request.actionId });
        }
      } finally {
        decodedBufferScheduled = false;
        if (decodedBufferRequest) {
          const request = decodedBufferRequest;
          decodedBufferRequest = null;
          scheduleDecodedBuffer(request.frame, { actionId: request.actionId });
        }
      }
    });
  }

  function queueCurrentFrameRedraw() {
    canvasSizeDirty = true;

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
      scheduleFrameCacheWarm(clampedFrame);
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

  function advancePlayback() {
    if (playing) {
      if (playbackLoopActive) {
        return;
      }

      playing = false;
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

  function canRequestScreenWakeLock() {
    return (
      "wakeLock" in navigator &&
      navigator.wakeLock &&
      typeof navigator.wakeLock.request === "function"
    );
  }

  function shouldKeepScreenAwake() {
    return document.fullscreenElement && !document.hidden;
  }

  async function requestScreenWakeLock() {
    if (
      !canRequestScreenWakeLock() ||
      !shouldKeepScreenAwake() ||
      screenWakeLock ||
      screenWakeLockRequest
    ) {
      return;
    }

    try {
      screenWakeLockRequest = navigator.wakeLock.request("screen");
      const wakeLock = await screenWakeLockRequest;
      wakeLock.addEventListener("release", () => {
        if (screenWakeLock === wakeLock) {
          screenWakeLock = null;
        }
      });

      if (!shouldKeepScreenAwake()) {
        await wakeLock.release();
        return;
      }

      screenWakeLock = wakeLock;
    } catch (error) {
      console.error(error);
    } finally {
      screenWakeLockRequest = null;
    }
  }

  async function releaseScreenWakeLock() {
    if (!screenWakeLock) {
      return;
    }

    const wakeLock = screenWakeLock;
    screenWakeLock = null;

    try {
      await wakeLock.release();
    } catch (error) {
      console.error(error);
    }
  }

  async function enableFullscreen({ preferLandscape = false } = {}) {
    if (!container.requestFullscreen || document.fullscreenElement) {
      return;
    }

    try {
      await container.requestFullscreen();
      void requestScreenWakeLock();
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

  function handleFullscreenChange() {
    queueCurrentFrameRedraw();

    if (document.fullscreenElement) {
      void requestScreenWakeLock();
    } else {
      void releaseScreenWakeLock();
    }
  }

  function handleTouchAction(clientX) {
    if (!ready || (playing && playbackLoopActive)) {
      return;
    }

    if (playing) {
      playing = false;
    }

    const bounds = container.getBoundingClientRect();
    const touchX = clientX - bounds.left;

    if (touchX < bounds.width / 2) {
      playing = false;
      startAction();
      jump(-1);
      return;
    }

    advancePlayback();
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
    // Start once a short decoded runway is ready; warm the rest in the background.
    showLoadingProgress();
    await fillDecodedBuffer(clampedFrame, { actionId });
    hideLoadingProgress();
    scheduleFrameCacheWarm(clampedFrame);

    const segmentEnd = getSegmentEnd(clampedFrame);
    if (clampedFrame >= segmentEnd || clampedFrame === frameUrls.length - 1) {
      playing = false;
      return;
    }

    let lastPlaybackTimestamp = performance.now();
    let playbackUnderrun = false;

    function loop(timestamp) {
      try {
        if (!playing || !isActionActive(actionId)) {
          playbackLoopActive = false;
          hidePlaybackIndicator();
          return;
        }

        const elapsedFrames = Math.floor((timestamp - lastPlaybackTimestamp) / frameMillis);
        const targetFrame = Math.min(currentFrame + elapsedFrames, segmentEnd, frameUrls.length - 1);

        if (targetFrame > currentFrame) {
          const decodedFrameIndex = getBestDecodedFrame(currentFrame + 1, targetFrame);
          if (decodedFrameIndex !== null) {
            const advancedFrames = decodedFrameIndex - currentFrame;
            const decodedFrame = decodedFrames.get(decodedFrameIndex);
            drawFrame(decodedFrame.source, decodedFrame.width, decodedFrame.height);
            currentFrame = decodedFrameIndex;
            currentFrameWidth = decodedFrame.width;
            currentFrameHeight = decodedFrame.height;
            lastPlaybackTimestamp += advancedFrames * frameMillis;
            if (playbackUnderrun) {
              playbackUnderrun = false;
              hideLoadingProgress();
            }
            pruneDecodedFrames(decodedFrameIndex);
            scheduleDecodedBuffer(decodedFrameIndex, { actionId });
            scheduleFrameCacheWarm(decodedFrameIndex);
          } else {
            if (!playbackUnderrun) {
              playbackUnderrun = true;
              showLoadingProgress();
            }
            scheduleDecodedBuffer(currentFrame, { actionId });
            scheduleFrameCacheWarm(currentFrame);
            lastPlaybackTimestamp = timestamp;
          }
        }

        const isLast = currentFrame === frameUrls.length - 1;
        const isMarker = currentFrame !== clampedFrame && markerSet.has(currentFrame);
        if (currentFrame >= segmentEnd || isLast || isMarker) {
          playing = false;
          playbackLoopActive = false;
          hidePlaybackIndicator();
          scheduleFrameCacheWarm(currentFrame);
          return;
        }

        requestAnimationFrame(loop);
      } catch (error) {
        playbackLoopActive = false;
        hidePlaybackIndicator();
        handleAsyncError(error, { hideProgressOnCancel: true });
      }
    }

    showPlaybackIndicator();
    playbackLoopActive = true;
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
    hidePlaybackIndicator();
    hideLoadingProgress();
    showMessage("Failed to load frames");
    console.error(error);
  }

  function runAsync(action) {
    action().catch((error) => {
      handleAsyncError(error, { hideProgressOnCancel: true });
    });
  }

  function runBackground(action, { fatal = true } = {}) {
    action().catch((error) => {
      if (fatal) {
        handleAsyncError(error);
      } else {
        console.warn(error);
      }
    });
  }

  addEventListener("keydown", dismissAdvanceHint, { capture: true });
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

        advancePlayback();
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
  document.addEventListener("fullscreenchange", handleFullscreenChange);
  document.addEventListener("visibilitychange", handleVisibilityChange);

  container.addEventListener("touchstart", dismissAdvanceHint, { passive: true, capture: true });
  container.addEventListener("touchmove", dismissAdvanceHint, { passive: true, capture: true });
  container.addEventListener("touchend", dismissAdvanceHint, { passive: true, capture: true });
  container.addEventListener("touchcancel", dismissAdvanceHint, { passive: true, capture: true });

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
    await renderFrame(0, { actionId: initialActionId });
    ready = true;
    showPlayer();
    showAdvanceHintWhenVisible();
    scheduleDecodedBuffer(0, { actionId: initialActionId });
    scheduleFrameCacheWarm(0);
  } catch (error) {
    hideLoadingProgress();
    showMessage("Failed to load frames");
    throw error;
  }
})();
