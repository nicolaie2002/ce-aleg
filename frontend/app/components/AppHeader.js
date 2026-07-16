"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Barcode,
  Crown,
  Database,
  Gift,
  HelpCircle,
  LayoutDashboard,
  Radio,
  ScanLine,
  ShoppingCart,
  Sparkles,
} from "lucide-react";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { ThemeSwitcher } from "./ThemeSwitcher";
import { useLocale } from "./LocaleProvider";
import { API_URL } from "../config";
import { getActiveProfile } from "../utils/profilePreferences";

const NO_PREFETCH_ROUTES = new Set(["/barcode-scan", "/live-assistant", "/cart", "/store"]);

export function AppHeader({ actionHref = "/barcode-scan", actionLabel }) {
  const { pick } = useLocale();
  const pathname = usePathname();
  const [cartCount, setCartCount] = useState(0);
  const desktopNavigation = [
    {
      href: "/dashboard",
      label: pick("Acasă", "Home"),
      desktopLabel: pick("Panou", "Dashboard"),
      icon: LayoutDashboard,
    },
    {
      href: "/barcode-scan",
      label: pick("Scanează", "Scan"),
      desktopLabel: pick("Scanare", "Scanner"),
      icon: Barcode,
    },
    {
      href: "/catalog-romania",
      label: pick("Catalog", "Catalog"),
      desktopLabel: pick("Catalog", "Catalog"),
      icon: Database,
    },
    {
      href: "/missions",
      label: pick("Misiuni", "Missions"),
      desktopLabel: pick("Misiuni", "Missions"),
      icon: Gift,
    },
    {
      href: "/live-assistant",
      label: pick("AI", "AI"),
      desktopLabel: pick("Asistent", "Assistant"),
      icon: Radio,
    },
    {
      href: "/cart",
      label: pick("Coș", "Cart"),
      desktopLabel: pick("Coș", "Cart"),
      icon: ShoppingCart,
    },
  ];
  const mobileNavigation = desktopNavigation.filter(
    ({ href }) => !["/live-assistant", "/catalog-romania"].includes(href)
  );

  function isActive(href) {
    return pathname === href || (href !== "/dashboard" && pathname.startsWith(`${href}/`));
  }

  function getNavigationLabel(label, href) {
    if (href === "/cart" && cartCount > 0) {
      return `${label}: ${cartCount} ${pick("produse", "items")}`;
    }

    return label;
  }

  function shouldPrefetchRoute(href) {
    return !NO_PREFETCH_ROUTES.has(href);
  }

  useEffect(() => {
    document.body.classList.add("ce-has-mobile-dock");
    return () => document.body.classList.remove("ce-has-mobile-dock");
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadCartCount() {
      try {
        const savedUser = window.localStorage.getItem("cealeg_user");

        if (!savedUser) {
          if (isMounted) setCartCount(0);
          return;
        }

        const user = JSON.parse(savedUser);
        const activeProfile = getActiveProfile();
        const profileQuery = activeProfile?.id
          ? `?profile_id=${encodeURIComponent(activeProfile.id)}`
          : "";
        const response = await fetch(`${API_URL}/cart/${user.id}${profileQuery}`);

        if (!response.ok) {
          if (isMounted) setCartCount(0);
          return;
        }

        const items = await response.json();
        const nextCount = Array.isArray(items)
          ? items.reduce((total, item) => total + (item.quantity || 1), 0)
          : 0;

        if (isMounted) setCartCount(nextCount);
      } catch {
        if (isMounted) setCartCount(0);
      }
    }

    function handleCartUpdate() {
      void loadCartCount();
    }

    queueMicrotask(loadCartCount);
    window.addEventListener("cealeg:cart-updated", handleCartUpdate);
    window.addEventListener("cealeg:profile-change", handleCartUpdate);
    window.addEventListener("storage", handleCartUpdate);

    return () => {
      isMounted = false;
      window.removeEventListener("cealeg:cart-updated", handleCartUpdate);
      window.removeEventListener("cealeg:profile-change", handleCartUpdate);
      window.removeEventListener("storage", handleCartUpdate);
    };
  }, []);

  function renderIconWithBadge(Icon, href) {
    const showBadge = href === "/cart" && cartCount > 0;

    return (
      <span className="relative inline-flex">
        <Icon size={18} />
        {showBadge && (
          <span className="absolute -right-2.5 -top-2.5 flex h-5 min-w-5 items-center justify-center rounded-full border border-[#0b1118] bg-yellow-300 px-1 text-[10px] font-black leading-none text-black shadow-[0_0_16px_rgba(250,204,21,0.45)]">
            {cartCount > 99 ? "99+" : cartCount}
          </span>
        )}
      </span>
    );
  }

  return (
    <>
      <header className="ce-header sticky top-0 z-40 border-b border-white/10 shadow-[0_18px_55px_rgba(0,0,0,0.18)] backdrop-blur-xl">
        <div className="ce-shell flex min-h-16 items-center justify-between gap-3 py-3">
          <Link
            href="/dashboard"
            className="flex min-w-0 items-center gap-3"
            aria-label={pick("Ce aleg? - Panou", "Ce aleg? - Dashboard")}
          >
            <span className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-lg shadow-[0_0_24px_rgba(52,211,153,0.22)]">
              <Image
                src="/icon.png"
                alt=""
                width={80}
                height={80}
                className="h-full w-full object-cover"
                priority
              />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-base font-black text-white">
                Ce aleg?
              </span>
              <span className="hidden items-center gap-1 text-xs text-cyan-100/75 sm:flex">
                <Sparkles size={12} />
                {pick("cumpărături mai inteligente", "smarter shopping")}
              </span>
            </span>
          </Link>

          <nav className="hidden items-center gap-1 lg:flex" aria-label={pick("Navigare principală", "Main navigation")}>
            {desktopNavigation.map(({ href, desktopLabel, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                prefetch={shouldPrefetchRoute(href)}
                aria-label={getNavigationLabel(desktopLabel, href)}
                aria-current={isActive(href) ? "page" : undefined}
                className={`ce-nav-link inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-bold ${
                  isActive(href)
                    ? "ce-nav-link-active text-white"
                    : "text-gray-300 hover:bg-white/[0.07] hover:text-white"
                }`}
              >
                {renderIconWithBadge(Icon, href)}
                <span>{desktopLabel}</span>
              </Link>
            ))}
          </nav>

          <div className="flex shrink-0 items-center gap-2">
            <LanguageSwitcher compact />
            <ThemeSwitcher />
            <Link
              href="/help"
              title={pick("Ajutor", "Help")}
              aria-label={pick("Ajutor", "Help")}
              aria-current={pathname === "/help" ? "page" : undefined}
              className={`inline-flex min-h-11 shrink-0 items-center gap-2 rounded-lg border px-3 py-2 text-sm font-black transition ${
                pathname === "/help"
                  ? "border-cyan-200/60 bg-cyan-200 text-black"
                  : "border-white/12 bg-white/[0.04] text-cyan-100 hover:-translate-y-0.5 hover:bg-white/[0.08]"
              }`}
            >
              <HelpCircle size={16} />
              <span className="hidden sm:inline">{pick("Ajutor", "Help")}</span>
            </Link>
            <Link
              href="/pricing"
              aria-label={pick("Planuri", "Plans")}
              aria-current={pathname === "/pricing" ? "page" : undefined}
              className="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-lg border border-yellow-300/35 bg-yellow-300/10 px-3 py-2 text-sm font-black text-yellow-200 shadow-[0_0_24px_rgba(250,204,21,0.12)] transition hover:-translate-y-0.5 hover:border-yellow-200/60 hover:bg-yellow-300/20"
            >
              <Crown size={16} />
              <span className="hidden sm:inline">{pick("Planuri", "Plans")}</span>
            </Link>
            {actionHref && (
              <Link
                href={actionHref}
                prefetch={shouldPrefetchRoute(actionHref)}
                className="hidden shrink-0 items-center gap-2 rounded-lg bg-white px-4 py-2.5 text-sm font-black text-black transition hover:-translate-y-0.5 hover:bg-cyan-100 xl:inline-flex"
              >
                <ScanLine size={17} />
                {actionLabel || pick("Scanează", "Scan")}
              </Link>
            )}
          </div>
        </div>
      </header>

      <nav
        className="ce-mobile-dock fixed inset-x-3 bottom-3 z-40 grid grid-cols-5 border border-white/12 bg-[#0b1118]/94 p-1.5 shadow-2xl backdrop-blur-xl lg:hidden"
        aria-label={pick("Navigare mobilă", "Mobile navigation")}
      >
        {mobileNavigation.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            prefetch={shouldPrefetchRoute(href)}
            aria-label={getNavigationLabel(label, href)}
            aria-current={isActive(href) ? "page" : undefined}
            className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-lg px-1 text-[11px] font-bold ${
              isActive(href)
                ? "bg-cyan-200 text-black"
                : "text-gray-300 hover:bg-white/10 hover:text-white"
            }`}
          >
            {renderIconWithBadge(Icon, href)}
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
