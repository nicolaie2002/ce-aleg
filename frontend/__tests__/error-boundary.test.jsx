import * as Sentry from "@sentry/nextjs";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ErrorPage from "../app/error";
import { LocaleProvider } from "../app/components/LocaleProvider";

jest.mock("@sentry/nextjs", () => ({
  captureException: jest.fn(),
}));

jest.mock("../app/components/AppHeader", () => ({
  AppHeader: () => <header>Ce aleg?</header>,
}));

describe("route error boundary", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.lang = "ro";
  });

  it("reports the error and retries in Romanian", async () => {
    const user = userEvent.setup();
    const reset = jest.fn();
    const error = new Error("test failure");

    render(
      <LocaleProvider>
        <ErrorPage error={error} reset={reset} />
      </LocaleProvider>
    );

    expect(
      await screen.findByRole("heading", {
        name: "Reîncarcă pagina sau revino în panoul de control.",
      })
    ).toBeInTheDocument();
    expect(screen.getByText(/Datele tale sunt în siguranță/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Panou de control" })).toHaveAttribute(
      "href",
      "/dashboard"
    );

    await waitFor(() => expect(Sentry.captureException).toHaveBeenCalledWith(error));
    await user.click(screen.getByRole("button", { name: "Încearcă din nou" }));

    expect(reset).toHaveBeenCalledTimes(1);
  });

  it("uses English when that is the saved language", async () => {
    localStorage.setItem("cealeg_locale", "en");

    render(
      <LocaleProvider>
        <ErrorPage error={new Error("test failure")} reset={jest.fn()} />
      </LocaleProvider>
    );

    expect(
      await screen.findByRole("heading", {
        name: "Reload the page or return to your dashboard.",
      })
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(document.documentElement).toHaveAttribute("lang", "en");
  });
});
