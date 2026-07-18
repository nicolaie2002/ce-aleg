"use client";

import { useEffect, type ReactNode } from "react";
import {
  ANALYTICS_CONSENT_EVENT,
  ANALYTICS_READY_EVENT,
  hasAnalyticsConsent,
  setPostHogInstance,
} from "../app/utils/analytics";

const apiKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const apiHost = process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://eu.i.posthog.com";
let postHogPromise: Promise<typeof import("posthog-js").default> | null = null;

function loadPostHog() {
  if (!postHogPromise) {
    postHogPromise = import("posthog-js").then(({ default: posthog }) => {
      const client = posthog.init(apiKey || "", {
        api_host: apiHost,
        capture_pageview: false,
        persistence: "localStorage",
      });
      setPostHogInstance(client);
      return client;
    });
  }

  return postHogPromise;
}

function identifySignedInUser(posthog: typeof import("posthog-js").default) {
  try {
    const user = JSON.parse(window.localStorage?.getItem("cealeg_user") || "null");
    if (user?.id) {
      posthog.identify(`cealeg-user-${user.id}`, { plan: user.plan || "free" });
    }
  } catch {
    // A malformed local session must not block the application shell.
  }
}

export function PostHogProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    let disposed = false;

    async function synchronizeConsent() {
      if (!apiKey) return;

      if (!hasAnalyticsConsent()) {
        if (postHogPromise) {
          const posthog = await postHogPromise;
          if (!disposed) {
            posthog.reset();
            posthog.opt_out_capturing();
            setPostHogInstance(null);
          }
        }
        return;
      }

      const posthog = await loadPostHog();
      if (disposed || !hasAnalyticsConsent()) return;

      posthog.opt_in_capturing();
      setPostHogInstance(posthog);
      identifySignedInUser(posthog);
      window.dispatchEvent(new Event(ANALYTICS_READY_EVENT));
    }

    void synchronizeConsent();
    window.addEventListener(ANALYTICS_CONSENT_EVENT, synchronizeConsent);

    return () => {
      disposed = true;
      window.removeEventListener(ANALYTICS_CONSENT_EVENT, synchronizeConsent);
    };
  }, []);

  return <>{children}</>;
}
