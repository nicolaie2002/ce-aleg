import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { AutomaticPageTranslation } from "../app/components/AutomaticPageTranslation";
import { LocaleProvider, useLocale } from "../app/components/LocaleProvider";

let mockPathname = "/admin";

jest.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
}));

function TranslationFixture() {
  const { setLocale } = useLocale();
  const [message, setMessage] = useState("Administrare platformă");

  return (
    <>
      <p>{message}</p>
      <button type="button" onClick={() => setMessage("Am găsit 3 produse.")}>Update</button>
      <button type="button" onClick={() => setLocale("ro")}>Romanian</button>
    </>
  );
}

function FlowTranslationFixture() {
  const { setLocale } = useLocale();
  const [status, setStatus] = useState("Scanner pregătit");

  return (
    <>
      <h1>Scanează codul. Confirmă produsul.</h1>
      <h2>Caută alternative potrivite.</h2>
      <input aria-label="Căutare" placeholder="Ex: fără zahăr, mai ieftin, mai multă proteină" />
      <button type="button">Altă aromă</button>
      <p>{status}</p>
      <button type="button" onClick={() => setStatus("Încredere: 92%")}>Dynamic</button>
      <button type="button" onClick={() => setLocale("ro")}>Romanian flow</button>
    </>
  );
}

describe("AutomaticPageTranslation", () => {
  beforeEach(() => {
    mockPathname = "/admin";
    localStorage.clear();
    localStorage.setItem("cealeg_locale", "en");
  });

  it("translates admin copy, reacts to dynamic text and restores Romanian", async () => {
    const user = userEvent.setup();
    render(
      <LocaleProvider>
        <AutomaticPageTranslation />
        <TranslationFixture />
      </LocaleProvider>
    );

    expect(await screen.findByText("Platform administration")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Update" }));
    expect(await screen.findByText("Found 3 products.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Romanian" }));
    await waitFor(() => {
      expect(screen.getByText("Am găsit 3 produse.")).toBeInTheDocument();
    });
  });

  it("translates scanner and contribution copy including dynamic states", async () => {
    mockPathname = "/barcode-scan";
    const user = userEvent.setup();
    render(
      <LocaleProvider>
        <AutomaticPageTranslation />
        <FlowTranslationFixture />
      </LocaleProvider>
    );

    expect(await screen.findByRole("heading", {
      name: "Scan the barcode. Confirm the product.",
    })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Find suitable alternatives." }))
      .toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Different flavor" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("For example: sugar-free, cheaper, more protein"))
      .toBeInTheDocument();
    expect(screen.getByText("Scanner ready")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Dynamic" }));
    expect(await screen.findByText("Confidence: 92%")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Romanian flow" }));
    await waitFor(() => {
      expect(screen.getByText("Încredere: 92%")).toBeInTheDocument();
    });
  });
});
