const cacheBust = performance.now();

(async function () {
  const { markers, frames, fps } = await fetch("./manifest.json").then((resp) => resp.json());
  const frameMillis = 1000 / fps;
  const img = document.getElementById("image");

  let lastActionId = 0;
  let currentFrame = 0;
  let playing = false;

  function jump(direction) {
    if (direction === 1) {
      const idx = markers.find((element) => element > currentFrame);
      if (idx === undefined) {
        seek(frames.length - 1);
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

  function seek(frame) {
    frame = Math.max(0, frame);
    frame = Math.min(frame, frames.length - 1);
    img.src = `${frames[frame]}?cacheBust=${cacheBust}`;
    currentFrame = frame;
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
        seek(nextFrame);

        const isLast = nextFrame === frames.length;
        const isMarker = markers.indexOf(nextFrame) !== -1;
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

  seek(0);
})();
