import posthog from "posthog-js";

export function initPostHog() {
  if (typeof window === "undefined") return;

  const apiKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  const apiHost = process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://eu.i.posthog.com";

  if (!apiKey) {
    console.warn("PostHog API key not configured");
    return;
  }

  posthog.init(apiKey, {
    api_host: apiHost,
    capture_pageview: false,
    persistence: "localStorage",
    loaded: (posthog) => {
      if (typeof window !== "undefined") {
        const userData = window.localStorage?.getItem("cealeg_user");
        if (userData) {
          try {
            const user = JSON.parse(userData);
            if (user?.email) {
              posthog.identify(user.email, {
                email: user.email,
                name: user.name,
                created_at: user.created_at,
              });
            }
          } catch (e) {
            console.warn("Failed to parse cealeg_user from localStorage", e);
          }
        }
      }
    },
  });

  return posthog;
}