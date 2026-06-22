"use client";

import { Suspense, useEffect, useState } from "react";
import Script from "next/script";
import { usePathname, useSearchParams } from "next/navigation";

const GA_ID = process.env.NEXT_PUBLIC_GA_ID || "";
const CONSENT_KEY = "cealeg_analytics_consent";

function hasAnalyticsConsent() {
  if (typeof window === "undefined") {
    return false;
  }

  return localStorage.getItem(CONSENT_KEY) === "accepted";
}

function PageViewTracker() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (!GA_ID || typeof window === "undefined" || !window.gtag) {
      return;
    }

    const query = searchParams.toString();
    window.gtag("config", GA_ID, {
      page_path: query ? `${pathname}?${query}` : pathname,
    });
  }, [pathname, searchParams]);

  return null;
}

export function Analytics() {
  const [hasConsent, setHasConsent] = useState(false);

  useEffect(() => {
    function syncConsent() {
      setHasConsent(hasAnalyticsConsent());
    }

    syncConsent();
    window.addEventListener("storage", syncConsent);
    window.addEventListener("cealeg:analytics-consent", syncConsent);

    return () => {
      window.removeEventListener("storage", syncConsent);
      window.removeEventListener("cealeg:analytics-consent", syncConsent);
    };
  }, []);

  if (!GA_ID || !hasConsent) {
    return null;
  }

  return (
    <>
      <Script
        src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`}
        strategy="afterInteractive"
      />
      <Script id="ga-init" strategy="afterInteractive">
        {`
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          window.gtag = gtag;
          gtag('js', new Date());
          gtag('config', '${GA_ID}', { page_path: window.location.pathname });
        `}
      </Script>
      <Suspense fallback={null}>
        <PageViewTracker />
      </Suspense>
    </>
  );
}
