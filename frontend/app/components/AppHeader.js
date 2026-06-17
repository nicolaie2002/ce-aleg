"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import {
  Barcode,
  Crown,
  LayoutDashboard,
  Radio,
  ScanLine,
  ShoppingBasket,
  ShoppingCart,
  Sparkles,
} from "lucide-react";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { ThemeSwitcher } from "./ThemeSwitcher";
import { useLocale } from "./LocaleProvider";

export function AppHeader({ actionHref = "/barcode-scan", actionLabel }) {
  const { pick } = useLocale();
  const pathname = usePathname();
  const navigation = [
    {
      href: "/dashboard",
      label: pick("Acasa", "Home"),
      desktopLabel: "Dashboard",
      icon: LayoutDashboard,
    },
    {
      href: "/barcode-scan",
      label: pick("Scaneaza", "Scan"),
      desktopLabel: pick("Scanner", "Scanner"),
      icon: Barcode,
    },
    {
      href: "/live-assistant",
      label: "Live",
      desktopLabel: pick("Asistent live", "Live assistant"),
      icon: Radio,
    },
    {
      href: "/cart",
      label: pick("Cos", "Cart"),
      desktopLabel: pick("Cos", "Cart"),
      icon: ShoppingCart,
    },
  ];

  function isActive(href) {
    return pathname === href || (href !== "/dashboard" && pathname.startsWith(`${href}/`));
  }

  useEffect(() => {
    document.body.classList.add("ce-has-mobile-dock");
    return () => document.body.classList.remove("ce-has-mobile-dock");
  }, []);

  return (
    <>
      <header className="ce-header sticky top-0 z-40 border-b border-white/10 shadow-[0_18px_55px_rgba(0,0,0,0.18)] backdrop-blur-xl">
        <div className="ce-shell flex min-h-16 items-center justify-between gap-3 py-3">
          <Link href="/dashboard" className="flex min-w-0 items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-400 text-black shadow-[0_0_24px_rgba(52,211,153,0.22)]">
              <ShoppingBasket size={20} strokeWidth={2.5} />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-base font-black text-white">
                Ce aleg?
              </span>
              <span className="hidden items-center gap-1 text-xs text-cyan-100/75 sm:flex">
                <Sparkles size={12} />
                {pick("cumparaturi mai inteligente", "smarter shopping")}
              </span>
            </span>
          </Link>

          <nav className="hidden items-center gap-1 lg:flex" aria-label={pick("Navigare principala", "Main navigation")}>
            {navigation.map(({ href, desktopLabel, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                aria-current={isActive(href) ? "page" : undefined}
                className={`ce-nav-link inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-bold ${
                  isActive(href)
                    ? "ce-nav-link-active text-white"
                    : "text-gray-300 hover:bg-white/[0.07] hover:text-white"
                }`}
              >
                <Icon size={16} />
                <span>{desktopLabel}</span>
              </Link>
            ))}
          </nav>

          <div className="flex shrink-0 items-center gap-2">
            <LanguageSwitcher compact />
            <ThemeSwitcher />
            <Link
              href="/pricing"
              aria-current={pathname === "/pricing" ? "page" : undefined}
              className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-yellow-300/35 bg-yellow-300/10 px-3 py-2 text-sm font-black text-yellow-200 shadow-[0_0_24px_rgba(250,204,21,0.12)] transition hover:-translate-y-0.5 hover:border-yellow-200/60 hover:bg-yellow-300/20"
            >
              <Crown size={16} />
              <span className="hidden sm:inline">{pick("Planuri", "Plans")}</span>
            </Link>
            {actionHref && (
              <Link
                href={actionHref}
                className="hidden shrink-0 items-center gap-2 rounded-lg bg-white px-4 py-2.5 text-sm font-black text-black transition hover:-translate-y-0.5 hover:bg-cyan-100 xl:inline-flex"
              >
                <ScanLine size={17} />
                {actionLabel || pick("Scaneaza", "Scan")}
              </Link>
            )}
          </div>
        </div>
      </header>

      <nav
        className="ce-mobile-dock fixed inset-x-3 bottom-3 z-40 grid grid-cols-5 border border-white/12 bg-[#0b1118]/94 p-1.5 shadow-2xl backdrop-blur-xl lg:hidden"
        aria-label={pick("Navigare mobila", "Mobile navigation")}
      >
        {navigation.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            aria-current={isActive(href) ? "page" : undefined}
            className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-lg px-1 text-[11px] font-bold ${
              isActive(href)
                ? "bg-cyan-200 text-black"
                : "text-gray-300 hover:bg-white/10 hover:text-white"
            }`}
          >
            <Icon size={18} />
            <span className="max-w-full truncate">{label}</span>
          </Link>
        ))}
        <Link
          href="/pricing"
          aria-current={pathname === "/pricing" ? "page" : undefined}
          className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-lg px-1 text-[11px] font-bold ${
            pathname === "/pricing"
              ? "bg-yellow-300 text-black"
              : "text-yellow-200 hover:bg-yellow-300/10"
          }`}
        >
          <Crown size={18} />
          <span>{pick("Planuri", "Plans")}</span>
        </Link>
      </nav>
    </>
  );
}
