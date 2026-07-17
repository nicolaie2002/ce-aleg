import { renderHook, waitFor } from "@testing-library/react";
import {
  clearAuthenticatedSession,
  consumeAuthTokenFromLocation,
  storeAuthenticatedUser,
} from "../app/utils/authStorage";
import {
  ANALYTICS_CONSENT_KEY,
  isSensitiveAnalyticsPath,
  trackEvent,
} from "../app/utils/analytics";

let locale = "en";

jest.mock("../app/components/LocaleProvider", () => ({
  useLocale: () => ({ locale }),
}));

const { useTranslatedText } = require("../app/components/useTranslatedText");

describe("authentication storage boundaries", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    window.history.replaceState({}, "", "/");
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("consumes auth credentials and removes every credential from the URL", () => {
    window.history.replaceState(
      { navigation: true },
      "",
      "/reset-password?token=query-secret&code=oauth-code&keep=yes#access_token=fragment-secret&tab=security"
    );
    const replaceState = jest.spyOn(window.history, "replaceState");

    expect(consumeAuthTokenFromLocation()).toBe("query-secret");
    expect(window.location.pathname).toBe("/reset-password");
    expect(window.location.search).toBe("?keep=yes");
    expect(window.location.hash).toBe("#tab=security");
    expect(replaceState).toHaveBeenCalledWith(
      { navigation: true },
      "",
      "/reset-password?keep=yes#tab=security"
    );
  });

  it("isolates account-scoped storage and synchronizes an existing consent choice", () => {
    localStorage.setItem("cealeg_user", JSON.stringify({ id: "old-user" }));
    localStorage.setItem("cealeg_active_profile:old-user", JSON.stringify({ id: 4 }));
    localStorage.setItem("cealeg_preferences:old-user:primary", "{}");
    localStorage.setItem("cealeg_onboarding_completed", "true");
    localStorage.setItem(ANALYTICS_CONSENT_KEY, "accepted");
    sessionStorage.setItem("cealeg_pending_scan", "123");
    sessionStorage.setItem("unrelated", "keep");

    storeAuthenticatedUser({ id: "new-user", email: "new@example.test" });

    expect(JSON.parse(localStorage.getItem("cealeg_user"))).toEqual({
      id: "new-user",
      email: "new@example.test",
    });
    expect(localStorage.getItem("cealeg_active_profile:old-user")).toBeNull();
    expect(localStorage.getItem("cealeg_preferences:old-user:primary")).toBeNull();
    expect(localStorage.getItem("cealeg_onboarding_completed")).toBeNull();
    expect(sessionStorage.getItem("cealeg_pending_scan")).toBeNull();
    expect(sessionStorage.getItem("unrelated")).toBe("keep");
    expect(fetch).toHaveBeenCalledWith(
      "/api/backend/account/consent",
      expect.objectContaining({
        credentials: "include",
        body: JSON.stringify({ analytics: true }),
      })
    );

    clearAuthenticatedSession();
    expect(localStorage.getItem("cealeg_user")).toBeNull();
  });
});

describe("privacy-aware analytics", () => {
  beforeEach(() => {
    localStorage.clear();
    window.history.replaceState({}, "", "/catalog-romania");
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
    window.gtag = jest.fn();
    window.fbq = jest.fn();
    window.ttq = { track: jest.fn() };
  });

  afterEach(() => {
    delete window.gtag;
    delete window.fbq;
    delete window.ttq;
    jest.restoreAllMocks();
  });

  it("does not emit without consent or from an account-sensitive route", () => {
    trackEvent("product_found", { category: "dairy" });
    localStorage.setItem(ANALYTICS_CONSENT_KEY, "accepted");
    window.history.replaceState({}, "", "/dashboard/private");
    trackEvent("product_found", { category: "dairy" });

    expect(isSensitiveAnalyticsPath("/dashboard/private?token=secret")).toBe(true);
    expect(window.gtag).not.toHaveBeenCalled();
    expect(window.fbq).not.toHaveBeenCalled();
    expect(window.ttq.track).not.toHaveBeenCalled();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("sends only allowlisted metadata to analytics providers and the backend", () => {
    localStorage.setItem(ANALYTICS_CONSENT_KEY, "accepted");

    trackEvent("checkout_started", {
      plan: "family",
      value: 27,
      email: "private@example.test",
      token: "secret",
    });

    const safeMetadata = { plan: "family", value: "27" };
    expect(window.gtag).toHaveBeenCalledWith(
      "event",
      "checkout_started",
      safeMetadata
    );
    expect(window.fbq).toHaveBeenCalledWith(
      "track",
      "InitiateCheckout",
      safeMetadata
    );
    expect(window.ttq.track).toHaveBeenCalledWith(
      "InitiateCheckout",
      safeMetadata
    );
    expect(fetch).toHaveBeenCalledWith(
      "/api/backend/analytics/event",
      expect.objectContaining({
        body: JSON.stringify({
          name: "checkout_started",
          metadata: safeMetadata,
        }),
        keepalive: true,
      })
    );
  });
});

describe("translated text hook", () => {
  beforeEach(() => {
    locale = "en";
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("fetches a translation once and reuses the cached result", async () => {
    fetch.mockResolvedValue({
      json: jest.fn().mockResolvedValue({ translatedText: "Cached translation" }),
    });

    const first = renderHook(() => useTranslatedText("Cache contract source"));
    await waitFor(() => expect(first.result.current).toBe("Cached translation"));
    first.unmount();

    const second = renderHook(() => useTranslatedText("Cache contract source"));
    await waitFor(() => expect(second.result.current).toBe("Cached translation"));

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledWith("/api/backend/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: "Cache contract source", target: "en" }),
    });
  });

  it("keeps Romanian local and falls back to source text after a failed request", async () => {
    locale = "ro";
    const local = renderHook(() => useTranslatedText("Text local"));
    await waitFor(() => expect(local.result.current).toBe("Text local"));
    expect(fetch).not.toHaveBeenCalled();
    local.unmount();

    locale = "en";
    fetch.mockRejectedValue(new Error("offline"));
    const failed = renderHook(() => useTranslatedText("Fallback contract source"));
    await waitFor(() => expect(failed.result.current).toBe("Fallback contract source"));
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
