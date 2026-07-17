"use client";

import { PostHogProvider as PHProvider } from "@posthog/react";
import { useEffect } from "react";

const apiKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const apiHost = process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://eu.i.posthog.com";

export function PostHogProvider({ children }) {
  if (!apiKey) {
    return <>{children}</>;
  }

  return (
    <PHProvider
      apiKey={apiKey}
      options={{
        api_host: apiHost,
        capture_pageview: false,
        persistence: "localStorage",
        loaded: (posthog) => {
          if (typeof window !== "undefined") {
            const userStr = window.localStorage?.getItem("cealeg_user");
            if (userStr) {
              try {
                const user = JSON.parse(userStr);
                if (user?.email) {
                  posthog.identify(user.email, {
                    email: user.email,
                    name: user.name,
                    created_at: user.created_at,
                  });
                }
              } catch {
                // ignore parse errors
              }
            }
          }
        },
      }}
    >
      {children}
    </PHProvider>
  );
}