"use client";

import { useEffect, useState } from "react";
import { API_URL } from "../config";
import { useLocale } from "./LocaleProvider";

const cache = new Map();

export function useTranslatedText(text) {
  const { locale } = useLocale();
  const [translatedText, setTranslatedText] = useState(text || "");

  useEffect(() => {
    let isActive = true;
    const sourceText = text || "";

    if (!sourceText || locale === "ro") {
      queueMicrotask(() => isActive && setTranslatedText(sourceText));
      return () => {
        isActive = false;
      };
    }

    const cacheKey = `${locale}:${sourceText}`;
    if (cache.has(cacheKey)) {
      queueMicrotask(() => isActive && setTranslatedText(cache.get(cacheKey)));
      return () => {
        isActive = false;
      };
    }

    fetch(`${API_URL}/translate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: sourceText, target: locale }),
    })
      .then((response) => response.json())
      .then((data) => {
        const result = data.translatedText || sourceText;
        cache.set(cacheKey, result);
        if (isActive) setTranslatedText(result);
      })
      .catch(() => {
        if (isActive) setTranslatedText(sourceText);
      });

    return () => {
      isActive = false;
    };
  }, [locale, text]);

  return translatedText;
}
