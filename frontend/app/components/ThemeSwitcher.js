"use client";

import { Moon, Sun } from "lucide-react";
import { useLocale } from "./LocaleProvider";
import { useTheme } from "./ThemeProvider";

export function ThemeSwitcher() {
  const { pick } = useLocale();
  const { theme, toggleTheme } = useTheme();
  const label =
    theme === "dark"
      ? pick("Activează tema luminoasă", "Switch to light theme")
      : pick("Activează tema întunecată", "Switch to dark theme");

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-white/15 bg-black/25 text-gray-200 shadow-[0_0_18px_rgba(45,212,191,0.1)] hover:-translate-y-0.5 hover:border-cyan-300/50 hover:bg-cyan-300/10 hover:text-cyan-100 focus:outline-none focus:ring-2 focus:ring-cyan-200"
      aria-label={label}
      title={label}
      suppressHydrationWarning
    >
      <Sun className="ce-theme-icon ce-theme-icon-sun" size={17} />
      <Moon className="ce-theme-icon ce-theme-icon-moon" size={17} />
    </button>
  );
}
