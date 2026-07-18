"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { useLocale } from "./LocaleProvider";
import adminTranslations from "../../messages/admin-en.json";
import flowTranslations from "../../messages/flow-en.json";

const translations = {
  ...adminTranslations,
  ...flowTranslations,
  "Dashboard": "Dashboard",
  "Scanează": "Scan",
  "Scanează produs": "Scan product",
  "Scanează alt produs": "Scan another product",
  "Scanează din nou": "Scan again",
  "Scanează codul": "Scan barcode",
  "Înapoi la dashboard": "Back to dashboard",
  "Înapoi la rezultat": "Back to result",
  "Înapoi la scanare": "Back to scanner",
  "Scanează codul de bare.": "Scan the barcode.",
  "Caută produsul": "Find product",
  "Se caută...": "Searching...",
  "Cod de bare detectat/manual": "Detected/manual barcode",
  "Adaugă în coș": "Add to cart",
  "Adaugă la favorite": "Add to favorites",
  "Vezi coșul": "View cart",
  "Caută alternative potrivite": "Find suitable alternatives",
  "Alternative potrivite": "Suitable alternatives",
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
  "Pornește camera": "Start camera",
  "Pornește lanterna": "Turn flashlight on",
  "Oprește lanterna": "Turn flashlight off",
  "Introdu codul manual": "Enter barcode manually",
  "Caută după nume": "Search by name",
  "Pentru o scanare reușită": "For a successful scan",
  "Produs nou în România?": "New product in Romania?",
  "Ajută-ne să îl adăugăm.": "Help us add it.",
  "Sursa online nu răspunde": "The online source is not responding",
  "Cod citit de scanner": "Code read by scanner",
  "Da, codul e corect": "Yes, the code is correct",
  "Nu, rescanez": "No, scan again",
  "Corectez manual": "Fix manually",
  "Trimite produsul la verificare": "Submit product for review",
  "Vezi analiza produsului": "View product analysis",
  "Se adaugă...": "Adding...",
  "Se salvează...": "Saving...",
  "Salvează în baza locală": "Save to local catalog",
  "Verifică prețul în magazin": "Check the price in store",
  "Categorie necunoscută": "Unknown category",
  "Produs negăsit în catalog": "Product not found in catalog",
  "Produs venit din scanare": "Product from scan",
  "Cod de bare confirmat în scanner": "Barcode confirmed in scanner",
  "Verifică încă o dată codul de bare": "Check the barcode once more",
  "Flow rapid pe telefon": "Fast mobile flow",
  "Poze, OCR, trimitere.": "Photos, OCR, submit.",
  "Cod verificat": "Verified code",
  "Cod opțional": "Optional code",
  "Față produs": "Product front",
  "Tabel nutrițional": "Nutrition table",
  "Poză față produs": "Product front photo",
  "Poză tabel nutrițional": "Nutrition label photo",
  "Extrage automat din poze": "Extract automatically from photos",
  "Se extrag datele...": "Extracting data...",
  "Trimite la verificare": "Submit for review",
  "Propunerile tale": "Your submissions",
  "Nu ai trimis încă produse": "You have not submitted products yet",
  "Vezi misiunile": "View missions",
  "Contribuie produs": "Contribute product",
  "Adaugă un produs nou": "Add a new product",
  "Nume produs *": "Product name *",
  "Cod de bare": "Barcode",
  "Magazin *": "Store *",
  "Categorie": "Category",
  "Cantitate / gramaj": "Quantity / size",
  "Preț estimativ": "Estimated price",
  "Proteină": "Protein",
  "Zahăr": "Sugar",
  "Grăsimi": "Fat",
  "Ingrediente / observații": "Ingredients / notes",
  "Catalog România": "Romania catalog",
  "Scanează un produs": "Scan a product",
  "Adaugă produs lipsă": "Add missing product",
  "Vezi ghidul": "View guide",
  "Vezi pagina magazinului": "View store page",
  "Vezi pagina produsului": "View product page",
  "Ghid alternative": "Alternative guide",
  "Trimite produs": "Submit product",
  "Catalogul creste gratis": "The catalog grows for free",
  "Lactate": "Dairy",
  "Mezeluri": "Deli meats",
  "Dulciuri": "Sweets",
  "Băuturi": "Drinks",
  "Panificație": "Bakery",
  "Produse bio": "Organic products",
  "Cafea": "Coffee",
  "Alternative la iaurturi dulci": "Alternatives to sweet yogurts",
  "Alternative la dulciuri foarte zaharoase": "Alternatives to very sugary sweets",
  "Alternative la băuturi cu zahăr": "Alternatives to sugary drinks",
  "Alternative la snacks-uri sărate sau dulci": "Alternatives to salty or sweet snacks",
};

const originals = new WeakMap();
const renderedValues = new WeakMap();
const translatedAttributes = ["placeholder", "title", "aria-label"];
/** @type {Array<[RegExp, (...matches: string[]) => string]>} */
const translationPatterns = [
  [/^Am găsit ([\d.,]+) produse\.$/, (count) => `Found ${count} products.`],
  [/^Am găsit ([\d.,]+) produse pentru raportare\.$/, (count) => `Found ${count} products for this report.`],
  [/^([\d.,]+) din ([\d.,]+) conturi afișate$/, (visible, total) => `${visible} of ${total} accounts shown`],
  [/^([\d.,]+)% din catalog$/, (count) => `${count}% of the catalog`],
  [/^([\d.,]+) produse în plus$/, (count) => `${count} duplicate products`],
  [/^([\d.,]+) fără ingrediente$/, (count) => `${count} without ingredients`],
  [/^([\d.,]+) propuneri de verificat$/, (count) => `${count} submissions to review`],
  [/^([\d.,]+) neîncadrate$/, (count) => `${count} uncategorized`],
  [/^([\d.,]+) produse$/, (count) => `${count} products`],
  [/^([\d.,]+) rapoarte$/, (count) => `${count} reports`],
  [/^([\d.,]+) erori checkout$/, (count) => `${count} checkout errors`],
  [/^([\d.,]+) coduri negăsite, ([\d.,]+) analize fără rezultat$/, (barcodes, analyses) => `${barcodes} missing barcodes, ${analyses} analyses without results`],
  [/^([\d.,]+) schimbări din ([\d.,]+) verificate$/, (changed, checked) => `${changed} changes from ${checked} checked`],
  [/^Caut produs raportat: (.+)$/, (query) => `Searching for reported product: ${query}`],
  [/^Magazin: (.+) · Cerință: (.+)$/, (store, requirement) => `Store: ${store} · Request: ${requirement}`],
  [/^Pentru: (.+)$/, (product) => `For: ${product}`],
  [/^Ai folosit ([\d.,]+)\/([\d.,]+) scanări gratuite luna aceasta\.$/, (used, limit) => `You used ${used}/${limit} free scans this month.`],
  [/^Încredere: ([\d.,]+)%$/, (confidence) => `Confidence: ${confidence}%`],
  [/^Camera ([\d.,]+)$/, (index) => `Camera ${index}`],
  [/^Trimite la verificare - până la ([\d.,]+) CeCoins după aprobare$/, (coins) => `Submit for review - up to ${coins} CeCoins after approval`],
  [/^Poză optimizată: (.+) -> (.+)\.$/, (before, after) => `Photo optimized: ${before} -> ${after}.`],
];
const manuallyLocalizedPages = new Set([
  "/",
  "/billing/cancel",
  "/billing/success",
  "/cart",
  "/dashboard",
  "/delete-account",
  "/forgot-password",
  "/favorites",
  "/help",
  "/history",
  "/catalog-romania",
  "/live-assistant",
  "/login",
  "/missions",
  "/onboarding",
  "/preferences",
  "/pricing",
  "/privacy",
  "/register",
  "/result",
  "/reset-password",
  "/store",
  "/support",
  "/terms",
  "/verify-email",
]);

function translateValue(value, locale) {
  const leading = value.match(/^\s*/)?.[0] || "";
  const trailing = value.match(/\s*$/)?.[0] || "";
  const normalized = value.trim();
  let translated = normalized;

  if (locale === "en") {
    translated = translations[normalized] || normalized;
    if (translated === normalized) {
      for (const [pattern, replacer] of translationPatterns) {
        const match = normalized.match(pattern);
        if (match) {
          translated = replacer(...match.slice(1));
          break;
        }
      }
    }
  }

  return `${leading}${translated}${trailing}`;
}

function translateTextNode(node, locale) {
  const currentValue = node.nodeValue || "";
  if (!originals.has(node) || currentValue !== renderedValues.get(node)) {
    originals.set(node, currentValue);
  }

  const translated = translateValue(originals.get(node), locale);
  renderedValues.set(node, translated);
  if (currentValue !== translated) node.nodeValue = translated;
}

function translateTree(root, locale) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();

  while (node) {
    translateTextNode(node, locale);
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
    if (
      manuallyLocalizedPages.has(pathname) ||
      pathname.startsWith("/catalog-romania")
    ) return undefined;

    translateTree(document.body, locale);
    const observer = new MutationObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.type === "characterData") {
          translateTextNode(entry.target, locale);
          return;
        }
        entry.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) translateTree(node, locale);
          if (node.nodeType === Node.TEXT_NODE && node.parentElement) translateTree(node.parentElement, locale);
        });
      });
    });
    observer.observe(document.body, { characterData: true, childList: true, subtree: true });
    return () => observer.disconnect();
  }, [locale, pathname]);

  return null;
}
