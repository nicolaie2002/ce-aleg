"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

const LocaleContext = createContext(null);

export function LocaleProvider({ children }) {
  const [locale, setLocale] = useState("ro");

  useEffect(() => {
    queueMicrotask(() => {
      const savedLocale = localStorage.getItem("cealeg_locale");
      const normalizedLocale = savedLocale === "en" ? "en" : "ro";
      document.documentElement.lang = normalizedLocale;
      setLocale(normalizedLocale);
    });
  }, []);

  function changeLocale(nextLocale) {
    const normalizedLocale = nextLocale === "en" ? "en" : "ro";
    localStorage.setItem("cealeg_locale", normalizedLocale);
    document.documentElement.lang = normalizedLocale;
    setLocale(normalizedLocale);
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

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const context = useContext(LocaleContext);

  if (!context) {
    throw new Error("useLocale must be used inside LocaleProvider");
  }

  return context;
}
