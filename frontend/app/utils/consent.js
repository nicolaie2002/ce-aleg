export const CONSENT_STORAGE_KEY = "cealeg_consent";
export const CONSENT_SESSION_KEY = "cealeg_consent_session";
export const CONSENT_POLICY_VERSION = "2026-07";
export const CONSENT_CHANGE_EVENT = "cealeg:consent-change";
export const CONSENT_MANAGER_EVENT = "cealeg:open-cookie-manager";

export function createConsentState(overrides = {}) {
  return {
    analytics: false,
    marketing: false,
    functional: false,
    ...overrides,
    necessary: true,
    version: CONSENT_POLICY_VERSION,
    timestamp: typeof overrides.timestamp === "string"
      ? overrides.timestamp
      : new Date().toISOString(),
  };
}

export function normalizeStoredConsent(value) {
  if (!value || typeof value !== "object") return null;
  if (value.version !== CONSENT_POLICY_VERSION) return null;

  const optionalCategories = ["analytics", "marketing", "functional"];
  if (optionalCategories.some((category) => typeof value[category] !== "boolean")) {
    return null;
  }

  return createConsentState({
    analytics: value.analytics,
    marketing: value.marketing,
    functional: value.functional,
    timestamp: typeof value.timestamp === "string" ? value.timestamp : new Date().toISOString(),
  });
}

export function readStoredConsent() {
  if (typeof window === "undefined") return null;

  try {
    return normalizeStoredConsent(
      JSON.parse(window.localStorage.getItem(CONSENT_STORAGE_KEY) || "null")
    );
  } catch {
    return null;
  }
}

export function persistConsent(consent) {
  const normalized = createConsentState(consent);
  window.localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(normalized));
  window.localStorage.setItem(
    "cealeg_analytics_consent",
    normalized.analytics ? "accepted" : "declined"
  );
  return normalized;
}

export function getConsentSessionId() {
  const existing = window.localStorage.getItem(CONSENT_SESSION_KEY);
  if (existing && /^[A-Za-z0-9._:-]{1,128}$/.test(existing)) return existing;

  const generated = globalThis.crypto?.randomUUID?.()
    || `consent-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 14)}`;
  window.localStorage.setItem(CONSENT_SESSION_KEY, generated);
  return generated;
}
