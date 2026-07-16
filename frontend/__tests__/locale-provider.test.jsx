import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LocaleProvider, useLocale } from "../app/components/LocaleProvider";

function LocaleProbe() {
  const { locale, pick, setLocale } = useLocale();

  return (
    <div>
      <output aria-label="locale">{locale}</output>
      <p>{pick("Salut", "Hello")}</p>
      <button type="button" onClick={() => setLocale("en")}>
        English
      </button>
      <button type="button" onClick={() => setLocale("invalid")}>
        Romanian
      </button>
    </div>
  );
}

describe("LocaleProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.lang = "ro";
  });

  it("restores English from local storage", async () => {
    localStorage.setItem("cealeg_locale", "en");

    render(
      <LocaleProvider>
        <LocaleProbe />
      </LocaleProvider>
    );

    expect(await screen.findByText("Hello")).toBeInTheDocument();
    expect(screen.getByLabelText("locale")).toHaveTextContent("en");
    expect(document.documentElement).toHaveAttribute("lang", "en");
  });

  it("persists language changes and normalizes unsupported values", async () => {
    const user = userEvent.setup();

    render(
      <LocaleProvider>
        <LocaleProbe />
      </LocaleProvider>
    );

    await waitFor(() => expect(screen.getByText("Salut")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "English" }));

    expect(screen.getByText("Hello")).toBeInTheDocument();
    expect(localStorage.getItem("cealeg_locale")).toBe("en");

    await user.click(screen.getByRole("button", { name: "Romanian" }));

    expect(screen.getByText("Salut")).toBeInTheDocument();
    expect(localStorage.getItem("cealeg_locale")).toBe("ro");
    expect(document.documentElement).toHaveAttribute("lang", "ro");
  });

  it("requires a provider", () => {
    expect(() => render(<LocaleProbe />)).toThrow(
      "useLocale must be used inside LocaleProvider"
    );
  });
});
