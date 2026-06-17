"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

const ThemeContext = createContext({
  theme: "dark",
  setTheme: () => {},
  toggleTheme: () => {},
});

function getStoredTheme() {
  if (typeof window === "undefined") return "dark";

  const storedTheme = window.localStorage.getItem("cealeg_theme");
  return storedTheme === "light" ? "light" : "dark";
}

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState("dark");

  useEffect(() => {
    queueMicrotask(() => {
      const storedTheme = getStoredTheme();
      setThemeState(storedTheme);
      document.documentElement.dataset.theme = storedTheme;
    });
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const setTheme = useCallback((nextTheme) => {
    const safeTheme = nextTheme === "light" ? "light" : "dark";
    setThemeState(safeTheme);
    document.documentElement.dataset.theme = safeTheme;
    window.localStorage.setItem("cealeg_theme", safeTheme);
  }, []);

  const value = useMemo(
    () => ({
      theme,
      setTheme,
      toggleTheme: () => setTheme(theme === "dark" ? "light" : "dark"),
    }),
    [setTheme, theme]
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
