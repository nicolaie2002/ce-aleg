"use client";

import { useEffect, useRef, Suspense } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { usePostHog } from "@posthog/react";
import { setPostHogInstance } from "../utils/analytics";
import {
  ANALYTICS_CONSENT_EVENT,
  hasAnalyticsConsent,
  isSensitiveAnalyticsPath,
} from "../utils/analytics";

const ANALYTICS_READY_EVENT = "cealeg:analytics-ready";

function PageViewTracker() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const posthog = usePostHog();
  const lastTrackedPathRef = useRef("");

  useEffect(() => {
    if (posthog) {
      setPostHogInstance(posthog);
    }
  }, [posthog]);

  useEffect(() => {
    function trackPageView() {
      if (!hasAnalyticsConsent()) return;

      if (isSensitiveAnalyticsPath(pathname)) {
        lastTrackedPathRef.current = "";
        return;
      }

      const fullPath = pathname + (searchParams?.toString() ? `?${searchParams.toString()}` : "");

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
  }, [pathname, searchParams, posthog]);

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
  const posthog = usePostHog();

  useEffect(() => {
    if (posthog) {
      setPostHogInstance(posthog);
    }
  }, [posthog]);

  return <PageViewTrackerWithSuspense />;
}