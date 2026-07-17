import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createElement } from "react";
import { LanguageSwitcher } from "../app/components/LanguageSwitcher";
import { LocaleProvider } from "../app/components/LocaleProvider";
import { ProductImage } from "../app/components/ProductImage";

jest.mock("next/image", () => ({
  __esModule: true,
  default: function MockImage({ fill, unoptimized, ...props }) {
    return createElement("img", props);
  },
}));

describe("LanguageSwitcher", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("cealeg_locale", "en");
    document.documentElement.lang = "ro";
  });

  it("exposes a labelled language group and updates the active choice", async () => {
    const user = userEvent.setup();

    render(
      <LocaleProvider>
        <LanguageSwitcher />
      </LocaleProvider>
    );

    const group = await screen.findByRole("group", { name: "Select language" });
    const englishButton = screen.getByRole("button", { name: "English" });
    const romanianButton = screen.getAllByRole("button")[0];

    expect(group).toHaveAttribute("title", "Change language");
    expect(englishButton).toHaveAttribute("aria-pressed", "true");
    expect(romanianButton).toHaveAttribute("aria-pressed", "false");

    await user.click(romanianButton);

    expect(localStorage.getItem("cealeg_locale")).toBe("ro");
    expect(document.documentElement).toHaveAttribute("lang", "ro");
    expect(romanianButton).toHaveAttribute("aria-pressed", "true");
  });

  it("hides the decorative globe in compact mode", async () => {
    const { container } = render(
      <LocaleProvider>
        <LanguageSwitcher compact />
      </LocaleProvider>
    );

    await screen.findByRole("group", { name: "Select language" });
    expect(container.querySelector("svg")).not.toBeInTheDocument();
  });
});

describe("ProductImage", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("cealeg_locale", "en");
  });

  it("renders the product image with privacy-friendly attributes", async () => {
    render(
      <LocaleProvider>
        <ProductImage src="https://cdn.example/granola.jpg" alt="Granola" />
      </LocaleProvider>
    );

    await waitFor(() => expect(document.documentElement).toHaveAttribute("lang", "en"));
    expect(screen.getByRole("img", { name: "Granola" })).toHaveAttribute(
      "referrerpolicy",
      "no-referrer"
    );
  });

  it("announces a useful fallback when loading fails", async () => {
    const { rerender } = render(
      <LocaleProvider>
        <ProductImage src="/broken.jpg" alt="Granola" fallbackClassName="text-xl" />
      </LocaleProvider>
    );

    const image = screen.getByRole("img", { name: "Granola" });
    fireEvent.error(image);

    expect(await screen.findByText("Granola: image unavailable")).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: "Granola" })).not.toBeInTheDocument();

    rerender(
      <LocaleProvider>
        <ProductImage src="/replacement.jpg" alt="Granola" />
      </LocaleProvider>
    );
    expect(screen.getByRole("img", { name: "Granola" })).toHaveAttribute(
      "src",
      "/replacement.jpg"
    );
  });

  it("provides a generic accessible fallback when no source or alt exists", async () => {
    render(
      <LocaleProvider>
        <ProductImage />
      </LocaleProvider>
    );

    expect(await screen.findByText("Image unavailable")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});
