"use client";

import { useEffect, useRef } from "react";

function createNoiseTexture(size = 96) {
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");
  canvas.width = size;
  canvas.height = size;

  if (!context) return null;

  const image = context.createImageData(size, size);

  for (let index = 0; index < image.data.length; index += 4) {
    const value = 18 + Math.random() * 42;
    image.data[index] = value;
    image.data[index + 1] = value;
    image.data[index + 2] = value;
    image.data[index + 3] = 22 + Math.random() * 34;
  }

  context.putImageData(image, 0, 0);
  return canvas;
}

function makeWisps(count, seedOffset) {
  const wisps = [];
  let seed = 92821 + seedOffset;

  function random() {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  }

  for (let index = 0; index < count; index += 1) {
    wisps.push({
      x: random(),
      y: random(),
      length: 0.36 + random() * 0.56,
      amplitude: 0.015 + random() * 0.055,
      width: 0.75 + random() * 2.8,
      blur: 0.4 + random() * 2.2,
      rotation: -0.45 + random() * 0.9,
      phase: random() * Math.PI * 2,
      speed: 0.00012 + random() * 0.00022,
      alpha: 0.06 + random() * 0.16,
      tone: random(),
    });
  }

  return wisps;
}

export function CarbonVaporBackground({ variant = "global" }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;

    const context = canvas.getContext("2d", { alpha: true });
    if (!context) return undefined;

    const container = canvas.parentElement || document.body;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const noise = createNoiseTexture(112);
    const wisps = makeWisps(variant === "hero" ? 30 : 34, variant === "hero" ? 17 : 41);
    const pointer = {
      x: 0.5,
      y: 0.5,
      targetX: 0.5,
      targetY: 0.5,
    };
    let width = 0;
    let height = 0;
    let animationFrame = 0;
    let running = true;

    function resize() {
      const rect = container.getBoundingClientRect();
      const nextWidth = Math.max(1, Math.floor(rect.width || window.innerWidth));
      const nextHeight = Math.max(1, Math.floor(rect.height || window.innerHeight));
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 1.75);

      width = nextWidth;
      height = nextHeight;
      canvas.width = Math.floor(nextWidth * pixelRatio);
      canvas.height = Math.floor(nextHeight * pixelRatio);
      canvas.style.width = `${nextWidth}px`;
      canvas.style.height = `${nextHeight}px`;
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    }

    function drawBackground(isLight) {
      context.clearRect(0, 0, width, height);

      const base = context.createLinearGradient(0, 0, width, height);

      if (isLight) {
        base.addColorStop(0, "rgba(236, 247, 250, 0.34)");
        base.addColorStop(0.55, "rgba(245, 247, 241, 0.22)");
        base.addColorStop(1, "rgba(213, 232, 238, 0.26)");
      } else {
        base.addColorStop(0, variant === "hero" ? "rgba(2, 3, 5, 0.98)" : "rgba(3, 5, 8, 0.94)");
        base.addColorStop(0.52, variant === "hero" ? "rgba(13, 14, 16, 0.98)" : "rgba(8, 10, 13, 0.78)");
        base.addColorStop(1, variant === "hero" ? "rgba(1, 2, 4, 0.99)" : "rgba(1, 2, 5, 0.9)");
      }

      context.fillStyle = base;
      context.fillRect(0, 0, width, height);

      if (noise) {
        const pattern = context.createPattern(noise, "repeat");
        if (pattern) {
          context.globalCompositeOperation = isLight ? "multiply" : "overlay";
          context.globalAlpha = isLight ? 0.08 : variant === "hero" ? 0.24 : 0.16;
          context.fillStyle = pattern;
          context.fillRect(0, 0, width, height);
        }
      }

      context.globalAlpha = 1;
      context.globalCompositeOperation = "source-over";
    }

    function drawCarbonFolds(time, isLight) {
      if (isLight) return;

      const foldCount = variant === "hero" ? 9 : 7;
      context.save();
      context.globalCompositeOperation = "screen";

      for (let index = 0; index < foldCount; index += 1) {
        const phase = time * 0.00008 + index * 0.86;
        const startX = width * (-0.15 + index * 0.16);
        const startY = height * (0.1 + (index % 4) * 0.22);
        const endX = startX + width * (0.54 + (index % 3) * 0.18);
        const endY = startY + height * (0.08 + Math.sin(phase) * 0.18);
        const controlX = startX + width * (0.2 + Math.sin(phase * 0.7) * 0.06);
        const controlY = startY - height * (0.18 + Math.cos(phase) * 0.08);
        const gradient = context.createLinearGradient(startX, startY, endX, endY);

        gradient.addColorStop(0, "rgba(255,255,255,0)");
        gradient.addColorStop(0.44, `rgba(255,255,255,${variant === "hero" ? 0.035 : 0.026})`);
        gradient.addColorStop(1, "rgba(255,255,255,0)");

        context.beginPath();
        context.moveTo(startX, startY);
        context.quadraticCurveTo(controlX, controlY, endX, endY);
        context.filter = "blur(3.5px)";
        context.lineWidth = 1.1 + (index % 3) * 0.8;
        context.strokeStyle = gradient;
        context.stroke();
      }

      context.restore();
      context.filter = "none";
    }

    function drawWisp(wisp, time, isLight) {
      const parallaxStrength = variant === "hero" ? 34 : 18;
      const centerX = wisp.x * width + (pointer.x - 0.5) * parallaxStrength * (wisp.tone - 0.5);
      const centerY = wisp.y * height + (pointer.y - 0.5) * parallaxStrength * 0.55 * (wisp.tone - 0.5);
      const length = wisp.length * width;
      const amplitude = wisp.amplitude * height;
      const drift = time * wisp.speed + wisp.phase;
      const pulse = 0.55 + Math.sin(drift * 1.3) * 0.18;
      const alpha = wisp.alpha * pulse * (isLight ? 0.55 : variant === "hero" ? 1.18 : 1);
      const segments = 54;

      context.save();
      context.translate(centerX, centerY);
      context.rotate(wisp.rotation + Math.sin(drift * 0.65) * 0.18);
      context.beginPath();

      for (let index = 0; index <= segments; index += 1) {
        const progress = index / segments;
        const x = (progress - 0.5) * length;
        const y =
          Math.sin(progress * Math.PI * 2.1 + drift) * amplitude +
          Math.sin(progress * Math.PI * 5.4 - drift * 0.8) * amplitude * 0.34;

        if (index === 0) {
          context.moveTo(x, y);
        } else {
          context.lineTo(x, y);
        }
      }

      const gradient = context.createLinearGradient(-length / 2, 0, length / 2, 0);
      const tone = isLight
        ? Math.floor(34 + wisp.tone * 32)
        : Math.floor(150 + wisp.tone * 78);
      gradient.addColorStop(0, `rgba(${tone}, ${tone}, ${tone}, 0)`);
      gradient.addColorStop(0.5, `rgba(${tone}, ${tone}, ${tone}, ${alpha})`);
      gradient.addColorStop(1, `rgba(${tone}, ${tone}, ${tone}, 0)`);

      context.globalCompositeOperation = isLight ? "multiply" : "screen";
      context.filter = `blur(${wisp.blur}px)`;
      context.lineWidth = Math.max(0.7, wisp.width * (height / 780));
      context.strokeStyle = gradient;
      context.stroke();
      context.restore();
    }

    function drawMetalHighlights(time, isLight) {
      const count = variant === "hero" ? 12 : 8;
      context.save();
      context.globalCompositeOperation = isLight ? "multiply" : "screen";

      for (let index = 0; index < count; index += 1) {
        const phase = time * (0.00005 + index * 0.000006) + index * 1.9;
        const x = ((Math.sin(phase) * 0.5 + 0.5) * 1.18 - 0.09) * width;
        const y = ((Math.cos(phase * 0.72) * 0.5 + 0.5) * 1.12 - 0.06) * height;
        const lineLength = width * (0.12 + (index % 3) * 0.05);
        const alpha = isLight ? 0.025 : variant === "hero" ? 0.12 : 0.08;
        const gradient = context.createLinearGradient(x - lineLength, y, x + lineLength, y);

        gradient.addColorStop(0, "rgba(255,255,255,0)");
        gradient.addColorStop(0.5, isLight ? `rgba(35,42,48,${alpha})` : `rgba(255,255,255,${alpha})`);
        gradient.addColorStop(1, "rgba(255,255,255,0)");

        context.save();
        context.translate(x, y);
        context.rotate(-0.18 + index * 0.08);
        context.filter = "blur(1.6px)";
        context.lineWidth = 1;
        context.strokeStyle = gradient;
        context.beginPath();
        context.moveTo(-lineLength / 2, 0);
        context.lineTo(lineLength / 2, 0);
        context.stroke();
        context.restore();
      }

      context.restore();
    }

    function renderFrame(time = 0, shouldContinue = false) {
      if (!running) return;

      const isLight = document.documentElement.dataset.theme === "light";
      pointer.x += (pointer.targetX - pointer.x) * 0.05;
      pointer.y += (pointer.targetY - pointer.y) * 0.05;
      drawBackground(isLight);
      drawCarbonFolds(time, isLight);

      context.globalAlpha = variant === "hero" ? 0.96 : 1;
      wisps.forEach((wisp) => drawWisp(wisp, time, isLight));
      context.globalAlpha = 1;
      drawMetalHighlights(time, isLight);
      context.filter = "none";
      context.globalCompositeOperation = "source-over";

      if (shouldContinue && !reducedMotion.matches) {
        animationFrame = window.requestAnimationFrame((nextTime) => {
          renderFrame(nextTime, true);
        });
      }
    }

    resize();

    function handlePointerMove(event) {
      const rect = container.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      pointer.targetX = (event.clientX - rect.left) / rect.width;
      pointer.targetY = (event.clientY - rect.top) / rect.height;
    }

    container.addEventListener("pointermove", handlePointerMove, { passive: true });

    const resizeObserver = new ResizeObserver(() => {
      resize();
      renderFrame(performance.now(), false);
    });
    resizeObserver.observe(container);

    renderFrame(0, !reducedMotion.matches);

    const themeObserver = new MutationObserver(() => {
      renderFrame(performance.now(), false);
    });
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    return () => {
      running = false;
      window.cancelAnimationFrame(animationFrame);
      container.removeEventListener("pointermove", handlePointerMove);
      resizeObserver.disconnect();
      themeObserver.disconnect();
    };
  }, [variant]);

  return (
    <div
      className={`ce-carbon-vapor ce-carbon-vapor-${variant}`}
      aria-hidden="true"
    >
      <canvas ref={canvasRef} className="ce-carbon-vapor-canvas" />
    </div>
  );
}
