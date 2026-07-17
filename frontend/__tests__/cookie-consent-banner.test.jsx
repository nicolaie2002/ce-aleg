import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ANALYTICS_CONSENT_EVENT, ANALYTICS_CONSENT_KEY } from "../app/utils/analytics";

process.env.NEXT_PUBLIC_GA_ID = "G-TEST";

jest.mock("../app/components/LocaleProvider", () => ({
  useLocale: () => ({ pick: (_romanian, english) => english }),
}));

const { CookieConsentBanner } = require("../app/components/CookieConsentBanner");

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

  it("shows an accessible choice and accepts analytics without a signed-in account", async () => {
    const user = userEvent.setup();
    const consentEvent = jest.fn();
    window.addEventListener(ANALYTICS_CONSENT_EVENT, consentEvent);

    render(<CookieConsentBanner />);

    const region = await screen.findByRole("region", {
      name: "Help us improve the site",
    });
    expect(region).toHaveAccessibleDescription(/optional cookies only if you accept/i);
    expect(screen.getByRole("link", { name: "Privacy" })).toHaveAttribute("href", "/privacy");

    await user.click(screen.getByRole("button", { name: "Accept analytics" }));

    expect(localStorage.getItem(ANALYTICS_CONSENT_KEY)).toBe("accepted");
    expect(await screen.findByRole("status")).toHaveTextContent("Analytics preference saved.");
    expect(window.gtag).toHaveBeenCalledWith("consent", "update", {
      analytics_storage: "granted",
      ad_storage: "granted",
      ad_user_data: "granted",
      ad_personalization: "granted",
    });
    expect(window.fbq).toHaveBeenCalledWith("grantConsent");
    expect(window.ttq.grantConsent).toHaveBeenCalledTimes(1);
    expect(consentEvent).toHaveBeenCalledTimes(1);
    expect(global.fetch).not.toHaveBeenCalled();

    window.removeEventListener(ANALYTICS_CONSENT_EVENT, consentEvent);
  });

  it("records an authenticated decline through both privacy endpoints", async () => {
    const user = userEvent.setup();
    localStorage.setItem("cealeg_user", JSON.stringify({ id: "42" }));

    render(<CookieConsentBanner />);
    await user.click(await screen.findByRole("button", { name: "Decline" }));

    expect(localStorage.getItem(ANALYTICS_CONSENT_KEY)).toBe("declined");
    expect(await screen.findByRole("status")).toHaveTextContent("Optional analytics declined.");
    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      "/api/backend/privacy/consent",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        keepalive: true,
        body: JSON.stringify({
          type: "analytics",
          granted: false,
          policyVersion: "2026-07",
          source: "web-banner",
        }),
      })
    );
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      "/api/backend/account/consent",
      expect.objectContaining({
        body: JSON.stringify({ analytics: false }),
      })
    );
    expect(window.gtag).toHaveBeenCalledWith(
      "consent",
      "update",
      expect.objectContaining({ analytics_storage: "denied" })
    );
    expect(window.fbq).toHaveBeenCalledWith("revokeConsent");
    expect(window.ttq.revokeConsent).toHaveBeenCalledTimes(1);
  });

  it("does not call account endpoints for corrupt cached account data", async () => {
    const user = userEvent.setup();
    localStorage.setItem("cealeg_user", "not-json");

    render(<CookieConsentBanner />);
    await user.click(await screen.findByRole("button", { name: "Accept analytics" }));

    expect(global.fetch).not.toHaveBeenCalled();
    expect(await screen.findByRole("status")).toBeInTheDocument();
  });

  it("stays hidden when a preference is already stored", async () => {
    localStorage.setItem(ANALYTICS_CONSENT_KEY, "accepted");

    render(<CookieConsentBanner />);

    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
