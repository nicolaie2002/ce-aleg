const CONSENT_KEY = "cealeg_analytics_consent";

export function trackEvent(name, metadata = {}) {
  if (typeof window === "undefined") return;

  const eventName = String(name || "").trim();

  if (!eventName) return;

  const safeMetadata = Object.fromEntries(
    Object.entries(metadata || {})
      .filter(([, value]) => value !== undefined && value !== null)
      .map(([key, value]) => [key, String(value).slice(0, 250)])
  );

  if (window.localStorage?.getItem(CONSENT_KEY) === "accepted" && window.gtag) {
    window.gtag("event", eventName, safeMetadata);
  }

  fetch("/api/backend/analytics/event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: eventName, metadata: safeMetadata }),
    keepalive: true,
  }).catch(() => {});
}
