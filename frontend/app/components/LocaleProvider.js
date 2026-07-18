"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { NextIntlClientProvider } from "next-intl";
import { createIntlMessages } from "../../messages/intlMessages";

const LocaleContext = createContext(null);

function normalizeLocale(value) {
  return value === "en" ? "en" : "ro";
}

function persistLocale(locale) {
  localStorage.setItem("cealeg_locale", locale);
  document.cookie = `cealeg_locale=${locale}; Path=/; Max-Age=31536000; SameSite=Lax`;
  document.documentElement.lang = locale;
}

async function loadClientMessages(locale) {
  const catalog = locale === "en"
    ? (await import("../../messages/en.json")).default
    : (await import("../../messages/ro.json")).default;

  return createIntlMessages(catalog);
}

export function LocaleProvider({ children, initialLocale = "ro", messages = {} }) {
  const [locale, setLocale] = useState(() => normalizeLocale(initialLocale));
  const [intlMessages, setIntlMessages] = useState(messages);

  useEffect(() => {
    queueMicrotask(() => {
      const savedLocale = localStorage.getItem("cealeg_locale");
      const normalizedLocale = normalizeLocale(savedLocale || initialLocale);
      persistLocale(normalizedLocale);
      setLocale(normalizedLocale);

      if (normalizedLocale !== normalizeLocale(initialLocale)) {
        loadClientMessages(normalizedLocale).then(setIntlMessages).catch(() => null);
      }
    });
  }, [initialLocale]);

  function changeLocale(nextLocale) {
    const normalizedLocale = normalizeLocale(nextLocale);
    persistLocale(normalizedLocale);
    setLocale(normalizedLocale);
    loadClientMessages(normalizedLocale).then(setIntlMessages).catch(() => null);
  }

  const value = useMemo(
    () => ({
      locale,
      setLocale: changeLocale,
      isEnglish: locale === "en",
      pick: (ro, en) => (locale === "en" ? en : ro),
    }),
    [locale]
  );

  return (
    <NextIntlClientProvider locale={locale} messages={intlMessages}>
      <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
    </NextIntlClientProvider>
  );
}

export function useLocale() {
  const context = useContext(LocaleContext);

  if (!context) {
    throw new Error("useLocale must be used inside LocaleProvider");
  }

  return context;
}
