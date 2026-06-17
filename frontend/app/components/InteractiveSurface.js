"use client";

export function InteractiveSurface({
  as: Component = "div",
  className = "",
  children,
  ...props
}) {
  function updateSurface(event) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const element = event.currentTarget;
    const rect = element.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;
    const tiltX = (50 - y) / 18;
    const tiltY = (x - 50) / 18;

    element.style.setProperty("--surface-x", `${x}%`);
    element.style.setProperty("--surface-y", `${y}%`);
    element.style.setProperty("--surface-tilt-x", `${tiltX}deg`);
    element.style.setProperty("--surface-tilt-y", `${tiltY}deg`);
  }

  function resetSurface(event) {
    const element = event.currentTarget;
    element.style.setProperty("--surface-x", "50%");
    element.style.setProperty("--surface-y", "35%");
    element.style.setProperty("--surface-tilt-x", "0deg");
    element.style.setProperty("--surface-tilt-y", "0deg");
  }

  return (
    <Component
      className={`ce-interactive-surface ${className}`}
      onPointerMove={updateSurface}
      onPointerLeave={resetSurface}
      {...props}
    >
      {children}
    </Component>
  );
}
