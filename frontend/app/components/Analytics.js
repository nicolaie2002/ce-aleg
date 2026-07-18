"use client";

import { useEffect, useRef, Suspense } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import {
  ANALYTICS_CONSENT_EVENT,
  ANALYTICS_READY_EVENT,
  getPostHogInstance,
  hasAnalyticsConsent,
  isSensitiveAnalyticsPath,
} from "../utils/analytics";

function PageViewTracker() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const lastTrackedPathRef = useRef("");

  useEffect(() => {
    function trackPageView() {
      if (!hasAnalyticsConsent()) return;

      if (isSensitiveAnalyticsPath(pathname)) {
        lastTrackedPathRef.current = "";
        return;
      }

      const fullPath = pathname + (searchParams?.toString() ? `?${searchParams.toString()}` : "");
      const posthog = getPostHogInstance();

      if (posthog && lastTrackedPathRef.current !== fullPath) {
        posthog.capture("$pageview", {
          $current_url: `${window.location.origin}${fullPath}`,
          $pathname: pathname,
        });
        lastTrackedPathRef.current = fullPath;
      }
    }

    trackPageView();
    window.addEventListener(ANALYTICS_READY_EVENT, trackPageView);
    window.addEventListener(ANALYTICS_CONSENT_EVENT, trackPageView);

    return () => {
      window.removeEventListener(ANALYTICS_READY_EVENT, trackPageView);
      window.removeEventListener(ANALYTICS_CONSENT_EVENT, trackPageView);
    };
  }, [pathname, searchParams]);

  return null;
}

function PageViewTrackerWithSuspense() {
  return (
    <Suspense fallback={null}>
      <PageViewTracker />
    </Suspense>
  );
}

export function Analytics() {
  return <PageViewTrackerWithSuspense />;
}
