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
  "Favorite": "Favorites",
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
};

const originals = new WeakMap();
const translatedAttributes = ["placeholder", "title", "aria-label"];
const manuallyLocalizedPages = new Set([
  "/",
  "/billing/cancel",
  "/billing/success",
  "/dashboard",
  "/delete-account",
  "/forgot-password",
  "/catalog-romania",
  "/live-assistant",
  "/login",
  "/missions",
  "/onboarding",
  "/preferences",
  "/pricing",
  "/privacy",
  "/register",
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
