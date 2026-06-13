"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { useLocale } from "./LocaleProvider";

const translations = {
  "Dashboard": "Dashboard",
  "Scanează": "Scan",
  "Scanează produs": "Scan product",
  "Scanează alt produs": "Scan another product",
  "Scanează din nou": "Scan again",
  "Scanează codul": "Scan barcode",
  "← Înapoi la dashboard": "← Back to dashboard",
  "← Înapoi la rezultat": "← Back to result",
  "← Înapoi la scanare": "← Back to scanner",
  "Scanează codul de bare.": "Scan the barcode.",
  "Caută produsul": "Find product",
  "Se caută...": "Searching...",
  "Cod de bare detectat/manual": "Detected/manual barcode",
  "Adaugă în coș": "Add to cart",
  "Adaugă la favorite ⭐": "Add to favorites ⭐",
  "Vezi coșul": "View cart",
  "Caută alternative potrivite": "Find suitable alternatives",
  "Alternative potrivite": "Suitable alternatives",
  "Favorite ⭐": "Favorites ⭐",
  "Coș inteligent": "Smart cart",
  "Coșul este gol": "Your cart is empty",
  "Adaugă magazin nou": "Add new store",
  "Adaugă magazin": "Add store",
  "Istoric": "History",
  "Favorite": "Favorites",
  "Șterge": "Remove",
  "Închide": "Close",
  "Adaugă prețul din magazin": "Add store price",
  "Preț necunoscut": "Unknown price",
  "preț necunoscut": "unknown price",
  "Verdict rapid": "Quick verdict",
  "Citește mai mult": "Read more",
  "Arată mai puțin": "Show less",
  "Produs posibil": "Possible product",
  "Salvează în catalog": "Save to catalog",
  "Produs găsit în Open Food Facts.": "Product found in Open Food Facts.",
  "Pentru scanare mai rapidă": "For faster scanning",
  "Oprește camera": "Stop camera",
  "Repornește scannerul": "Restart scanner",
  "Caută codul introdus": "Find entered barcode",
};

const originals = new WeakMap();
const translatedAttributes = ["placeholder"];
const manuallyLocalizedPages = new Set([
  "/",
  "/dashboard",
  "/live-assistant",
  "/login",
  "/pricing",
  "/privacy",
  "/register",
  "/store",
  "/terms",
]);

function translateValue(value, locale) {
  const leading = value.match(/^\s*/)?.[0] || "";
  const trailing = value.match(/\s*$/)?.[0] || "";
  const normalized = value.trim();
  return `${leading}${locale === "en" ? translations[normalized] || normalized : normalized}${trailing}`;
}

function translateTree(root, locale) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();

  while (node) {
    if (!originals.has(node)) originals.set(node, node.nodeValue);
    const original = originals.get(node);
    const translated = translateValue(original, locale);
    if (node.nodeValue !== translated) node.nodeValue = translated;
    node = walker.nextNode();
  }

  root.querySelectorAll?.("[placeholder], [title], [aria-label]").forEach((element) => {
    translatedAttributes.forEach((attribute) => {
      if (!element.hasAttribute(attribute)) return;
      const key = `data-cealeg-${attribute}`;
      if (!element.hasAttribute(key)) element.setAttribute(key, element.getAttribute(attribute));
      element.setAttribute(attribute, translateValue(element.getAttribute(key), locale));
    });
  });
}

export function AutomaticPageTranslation() {
  const { locale } = useLocale();
  const pathname = usePathname();

  useEffect(() => {
    if (manuallyLocalizedPages.has(pathname)) return undefined;

    translateTree(document.body, locale);
    const observer = new MutationObserver((entries) => {
      entries.forEach((entry) => {
        entry.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) translateTree(node, locale);
          if (node.nodeType === Node.TEXT_NODE && node.parentElement) translateTree(node.parentElement, locale);
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [locale, pathname]);

  return null;
}
