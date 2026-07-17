export const ANALYTICS_CONSENT_KEY = "cealeg_analytics_consent";
export const ANALYTICS_CONSENT_EVENT = "cealeg:analytics-consent";

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

const SENSITIVE_ROUTE_PREFIXES = [
  "/admin",
  "/alternatives",
  "/barcode-scan",
  "/billing",
  "/cart",
  "/dashboard",
  "/delete-account",
  "/favorites",
  "/forgot-password",
  "/history",
  "/live-assistant",
  "/login",
  "/missions",
  "/onboarding",
  "/preferences",
  "/profile",
  "/register",
  "/reset-password",
  "/result",
  "/scan",
  "/store",
  "/submit-product",
  "/support",
  "/verify-email",
];

const PUBLIC_METADATA_KEYS = new Set([
  "billingcycle",
  "category",
  "checkouttype",
  "currency",
  "length",
  "mode",
  "packid",
  "plan",
  "reason",
  "score",
  "source",
  "store",
  "topic",
  "value",
]);

function normalizeMetadataKey(key) {
  return String(key).replace(/[^a-zA-Z0-9]/g, "").toLowerCase();
}

export function hasAnalyticsConsent() {
  if (typeof window === "undefined") return false;
  return window.localStorage?.getItem(ANALYTICS_CONSENT_KEY) === "accepted";
}

export function isSensitiveAnalyticsPath(pathname) {
  const normalizedPath = String(pathname || "/").split(/[?#]/, 1)[0] || "/";

  return SENSITIVE_ROUTE_PREFIXES.some(
    (prefix) => normalizedPath === prefix || normalizedPath.startsWith(`${prefix}/`)
  );
}

function toPublicAnalyticsMetadata(metadata = {}) {
  return Object.fromEntries(
    Object.entries(metadata || {})
      .filter(([key, value]) => (
        value !== undefined &&
        value !== null &&
        PUBLIC_METADATA_KEYS.has(normalizeMetadataKey(key))
      ))
      .map(([key, value]) => [key, String(value).slice(0, 100)])
  );
}

let posthogInstance = null;

export function setPostHogInstance(instance) {
  posthogInstance = instance;
}

export function trackEvent(name, metadata = {}) {
  if (
    typeof window === "undefined" ||
    !hasAnalyticsConsent() ||
    isSensitiveAnalyticsPath(window.location.pathname)
  ) {
    return;
  }

  const eventName = String(name || "")
    .trim()
    .replace(/[^a-zA-Z0-9_.-]/g, "_")
    .slice(0, 80);

  if (!eventName) return;

  const safeMetadata = toPublicAnalyticsMetadata(metadata);

  if (posthogInstance) {
    posthogInstance.capture(eventName, safeMetadata);
  }

  if (window.gtag) {
    window.gtag("event", eventName, safeMetadata);
  }

  if (window.fbq) {
    const metaEvent = META_STANDARD_EVENTS[eventName];

    if (metaEvent) {
      window.fbq("track", metaEvent, safeMetadata);
    } else {
      window.fbq("trackCustom", eventName, safeMetadata);
    }
  }

  if (window.ttq) {
    window.ttq.track(TIKTOK_STANDARD_EVENTS[eventName] || eventName, safeMetadata);
  }

  fetch("/api/backend/analytics/event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: eventName, metadata: safeMetadata }),
    keepalive: true,
  }).catch(() => {});
}