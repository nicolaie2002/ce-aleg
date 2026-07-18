import { render, screen, waitFor } from "@testing-library/react";
import { createElement } from "react";
import { AppHeader } from "../app/components/AppHeader";
import { LocaleProvider } from "../app/components/LocaleProvider";
import { ThemeProvider } from "../app/components/ThemeProvider";

let pathname = "/dashboard";

jest.mock("next/navigation", () => ({
  usePathname: () => pathname,
}));

jest.mock("next/image", () => ({
  __esModule: true,
  default: function MockImage({ fill, priority, unoptimized, ...props }) {
    return createElement("img", props);
  },
}));

function renderHeader(props = {}) {
  return render(
    <LocaleProvider>
      <ThemeProvider>
        <AppHeader {...props} />
      </ThemeProvider>
    </LocaleProvider>
  );
}

describe("AppHeader", () => {
  beforeEach(() => {
    pathname = "/dashboard";
    localStorage.clear();
    localStorage.setItem("cealeg_locale", "en");
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue([]),
    });
  });

  it("renders accessible desktop and mobile navigation and cleans up its body state", async () => {
    const { unmount } = renderHeader({ actionHref: "/barcode-scan" });

    expect(await screen.findByRole("navigation", { name: "Main navigation" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Mobile navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ce aleg? - Dashboard" })).toHaveAttribute(
      "href",
      "/dashboard"
    );
    expect(screen.getByRole("link", { name: "Help" })).toHaveAttribute("href", "/help");
    expect(screen.getAllByRole("link", { name: "Plans" })).toHaveLength(2);
    expect(document.body).toHaveClass("ce-has-mobile-dock");

    unmount();
    expect(document.body).not.toHaveClass("ce-has-mobile-dock");
  });

  it("loads the active cart count and refreshes it after cart events", async () => {
    localStorage.setItem("cealeg_user", JSON.stringify({ id: 42 }));
    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue([{ quantity: 2 }, { quantity: 1 }]),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue([{ quantity: 4 }]),
      });

    renderHeader();

    expect(await screen.findAllByRole("link", { name: "Cart: 3 items" })).toHaveLength(2);
    window.dispatchEvent(new Event("cealeg:cart-updated"));

    await waitFor(() => {
      expect(screen.getAllByRole("link", { name: "Cart: 4 items" })).toHaveLength(2);
    });
    expect(fetch).toHaveBeenCalledWith("/api/backend/cart/42");
  });
});
