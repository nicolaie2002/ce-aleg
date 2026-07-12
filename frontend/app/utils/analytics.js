const CONSENT_KEY = "cealeg_analytics_consent";

const META_STANDARD_EVENTS = {
  barcode_lookup: "Search",
  product_found: "ViewContent",
  checkout_started: "InitiateCheckout",
  pricing_checkout: "InitiateCheckout",
  cecoins_checkout: "InitiateCheckout",
  subscription_started: "Subscribe",
  register_started: "CompleteRegistration",
};

const TIKTOK_STANDARD_EVENTS = {
  barcode_lookup: "Search",
  product_found: "ViewContent",
  checkout_started: "InitiateCheckout",
  pricing_checkout: "InitiateCheckout",
  cecoins_checkout: "InitiateCheckout",
  subscription_started: "Subscribe",
  register_started: "CompleteRegistration",
};

const PRIVATE_ANALYTICS_KEYS = new Set([
  "barcode",
  "email",
  "sessionid",
  "session_id",
  "userid",
  "user_id",
]);

function hasAnalyticsConsent() {
  return window.localStorage?.getItem(CONSENT_KEY) === "accepted";
}

function toAnalyticsMetadata(metadata = {}) {
  return Object.fromEntries(
    Object.entries(metadata || {})
      .filter(([, value]) => value !== undefined && value !== null)
      .map(([key, value]) => [key, String(value).slice(0, 250)])
  );
}

function toPublicPixelMetadata(metadata = {}) {
  return Object.fromEntries(
    Object.entries(metadata).filter(
      ([key]) => !PRIVATE_ANALYTICS_KEYS.has(String(key).replace(/[^a-zA-Z0-9_]/g, "").toLowerCase())
    )
  );
}

export function trackEvent(name, metadata = {}) {
  if (typeof window === "undefined") return;

  const eventName = String(name || "").trim();

  if (!eventName) return;

  const safeMetadata = toAnalyticsMetadata(metadata);
  const pixelMetadata = toPublicPixelMetadata(safeMetadata);
  const hasConsent = hasAnalyticsConsent();

  if (hasConsent && window.gtag) {
    window.gtag("event", eventName, safeMetadata);
  }

  if (hasConsent && window.fbq) {
    const metaEvent = META_STANDARD_EVENTS[eventName];

    if (metaEvent) {
      window.fbq("track", metaEvent, pixelMetadata);
    } else {
      window.fbq("trackCustom", eventName, pixelMetadata);
    }
  }

  if (hasConsent && window.ttq) {
    window.ttq.track(TIKTOK_STANDARD_EVENTS[eventName] || eventName, pixelMetadata);
  }

  fetch("/api/backend/analytics/event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: eventName, metadata: safeMetadata }),
    keepalive: true,
  }).catch(() => {});
}
