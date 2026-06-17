"use client";

export function CarbonVaporBackground({ variant = "global" }) {
  return (
    <div className={`ce-carbon-vapor ce-carbon-vapor-${variant}`} aria-hidden="true">
      <span className="ce-carbon-vapor-layer ce-carbon-vapor-layer-one" />
      <span className="ce-carbon-vapor-layer ce-carbon-vapor-layer-two" />
      <span className="ce-carbon-vapor-layer ce-carbon-vapor-layer-three" />
    </div>
  );
}
