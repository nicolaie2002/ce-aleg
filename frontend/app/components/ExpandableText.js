"use client";

import { useId, useState } from "react";
import { useLocale } from "./LocaleProvider";
import { useTranslatedText } from "./useTranslatedText";

export function ExpandableText({ text, fallback = "", className = "", maxLength = 120 }) {
  const { pick } = useLocale();
  const content = useTranslatedText(text || fallback);
  const contentId = useId();
  const [isExpanded, setIsExpanded] = useState(false);

  if (!content) return null;

  const canExpand = content.length > maxLength;

  return (
    <div>
      <p id={contentId} className={`${className} ${canExpand && !isExpanded ? "line-clamp-2" : ""}`}>
        {content}
      </p>
      {canExpand && (
        <button type="button" onClick={() => setIsExpanded((current) => !current)} aria-controls={contentId} aria-expanded={isExpanded} className="mt-1 inline-flex min-h-11 items-center text-sm font-semibold text-emerald-300 hover:text-emerald-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300/70">
          {isExpanded ? pick("Arată mai puțin", "Show less") : pick("Citește mai mult", "Read more")}
        </button>
      )}
    </div>
  );
}
