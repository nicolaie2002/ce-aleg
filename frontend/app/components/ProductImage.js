"use client";

import Image from "next/image";
import { useState } from "react";
import { Package } from "lucide-react";

export function ProductImage({
  src,
  alt,
  containerClassName,
  imageClassName = "object-contain p-2",
  fallbackClassName = "text-3xl",
}) {
  const [failedSrc, setFailedSrc] = useState("");
  const hasImage = src && failedSrc !== src;
  return (
    <div
      className={`relative flex shrink-0 items-center justify-center overflow-hidden bg-white ${containerClassName}`}
    >
      {hasImage ? (
        <Image
          src={src}
          alt={alt}
          fill
          sizes="220px"
          unoptimized
          referrerPolicy="no-referrer"
          className={imageClassName}
          onError={() => setFailedSrc(src)}
        />
      ) : (
        <Package
          className={`${fallbackClassName} text-gray-400`}
          aria-label="Imagine indisponibilă"
        />
      )}
    </div>
  );
}
