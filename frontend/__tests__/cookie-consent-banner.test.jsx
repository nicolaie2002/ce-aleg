import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ANALYTICS_CONSENT_EVENT, ANALYTICS_CONSENT_KEY } from "../app/utils/analytics";
import {
  CONSENT_STORAGE_KEY,
} from "../app/utils/consent";

process.env.NEXT_PUBLIC_GA_ID = "G-TEST";

jest.mock("../app/components/LocaleProvider", () => ({
  useLocale: () => ({ pick: (_romanian, english) => english }),
}));

const { CookieConsentBanner } = require("../app/components/CookieConsentBanner");
const { CookieManager } = require("../app/components/CookieManager");

function findRequest(path) {
  return global.fetch.mock.calls.find(([url]) => url === path);
}

describe("CookieConsentBanner", () => {
  beforeEach(() => {
    localStorage.clear();
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
    window.gtag = jest.fn();
    window.fbq = jest.fn();
    window.ttq = {
      grantConsent: jest.fn(),
      revokeConsent: jest.fn(),
    };
  });

  afterEach(() => {
    delete window.gtag;
    delete window.fbq;
    delete window.ttq;
  });

  it("shows an accessible granular choice and records an anonymous acceptance", async () => {
    const user = userEvent.setup();
    const consentEvent = jest.fn();
    window.addEventListener(ANALYTICS_CONSENT_EVENT, consentEvent);

    render(<CookieConsentBanner />);

    const dialog = await screen.findByRole("dialog", {
      name: "Choose optional cookies",
    });
    expect(dialog).toHaveAccessibleDescription(/activates only with your consent/i);
    expect(screen.getByRole("link", { name: "Privacy" })).toHaveAttribute("href", "/privacy");

    await user.click(screen.getByRole("button", { name: "Accept all" }));

    expect(localStorage.getItem(ANALYTICS_CONSENT_KEY)).toBe("accepted");
    expect(JSON.parse(localStorage.getItem(CONSENT_STORAGE_KEY))).toEqual(
      expect.objectContaining({
        necessary: true,
        analytics: true,
        marketing: true,
        functional: true,
        version: "2026-07",
      })
    );
    expect(await screen.findByRole("status")).toHaveTextContent("Cookie preferences saved.");
    expect(window.gtag).toHaveBeenCalledWith("consent", "update", {
      analytics_storage: "granted",
      ad_storage: "granted",
      ad_user_data: "granted",
      ad_personalization: "granted",
    });
    expect(window.fbq).toHaveBeenCalledWith("grantConsent");
    expect(window.ttq.grantConsent).toHaveBeenCalledTimes(1);
    expect(consentEvent).toHaveBeenCalledTimes(1);

    const logRequest = findRequest("/api/backend/consent/log");
    expect(logRequest).toBeDefined();
    expect(logRequest[1]).toEqual(expect.objectContaining({
      method: "POST",
      credentials: "include",
      keepalive: true,
    }));
    expect(JSON.parse(logRequest[1].body)).toEqual(expect.objectContaining({
      categories: {
        necessary: true,
        analytics: true,
        marketing: true,
        functional: true,
      },
      version: "2026-07",
    }));

    window.removeEventListener(ANALYTICS_CONSENT_EVENT, consentEvent);
  });

  it("records all authenticated preferences and account analytics state", async () => {
    const user = userEvent.setup();
    localStorage.setItem("cealeg_user", JSON.stringify({ id: "42" }));

    render(<CookieConsentBanner />);
    await user.click(await screen.findByRole("button", { name: "Reject optional" }));

    expect(localStorage.getItem(ANALYTICS_CONSENT_KEY)).toBe("declined");
    expect(await screen.findByRole("status")).toHaveTextContent("Optional cookies declined.");
    expect(global.fetch).toHaveBeenCalledTimes(5);
    expect(findRequest("/api/backend/consent/log")).toBeDefined();

    const privacyRequests = global.fetch.mock.calls
      .filter(([url]) => url === "/api/backend/privacy/consent")
      .map(([, options]) => JSON.parse(options.body));
    expect(privacyRequests).toEqual([
      expect.objectContaining({ type: "analytics", granted: false }),
      expect.objectContaining({ type: "marketing", granted: false }),
      expect.objectContaining({ type: "functional", granted: false }),
    ]);
    expect(findRequest("/api/backend/account/consent")[1]).toEqual(
      expect.objectContaining({ body: JSON.stringify({ analytics: false }) })
    );
    expect(window.fbq).toHaveBeenCalledWith("revokeConsent");
  });

  it("logs anonymously when cached account data is corrupt", async () => {
    const user = userEvent.setup();
    localStorage.setItem("cealeg_user", "not-json");

    render(<CookieConsentBanner />);
    await user.click(await screen.findByRole("button", { name: "Accept all" }));

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(findRequest("/api/backend/consent/log")).toBeDefined();
    expect(await screen.findByRole("status")).toBeInTheDocument();
  });

  it("supports custom preferences and can be reopened", async () => {
    const user = userEvent.setup();
    render(
      <>
        <CookieConsentBanner />
        <CookieManager />
      </>
    );

    await user.click(await screen.findByRole("button", { name: "Customize" }));
    const analytics = screen.getByRole("checkbox", { name: /analytics/i });
    const marketing = screen.getByRole("checkbox", { name: /^marketing/i });
    await user.click(analytics);
    expect(marketing).not.toBeChecked();
    await user.click(screen.getByRole("button", { name: "Save choices" }));

    expect(JSON.parse(localStorage.getItem(CONSENT_STORAGE_KEY))).toEqual(
      expect.objectContaining({ analytics: true, marketing: false, functional: false })
    );

    await user.click(screen.getByRole("button", { name: "Manage cookies" }));
    expect(await screen.findByRole("dialog", { name: "Choose optional cookies" })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /analytics/i })).toBeChecked();
  });

  it("migrates and respects an existing legacy preference", async () => {
    localStorage.setItem(ANALYTICS_CONSENT_KEY, "accepted");

    render(<CookieConsentBanner />);

    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem(CONSENT_STORAGE_KEY))).toEqual(
      expect.objectContaining({ analytics: true, marketing: true })
    );
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
