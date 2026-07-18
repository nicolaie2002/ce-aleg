import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FamilyProfiles } from "@/app/components/FamilyProfiles";
import { LocaleProvider } from "@/app/components/LocaleProvider";

jest.mock("@/app/config", () => ({ API_URL: "/api/backend" }));

function jsonResponse(payload, { ok = true, status = 200 } = {}) {
  return {
    ok,
    status,
    headers: { get: jest.fn(() => "application/json") },
    json: jest.fn().mockResolvedValue(payload),
  };
}

function renderProfiles() {
  return render(
    <LocaleProvider>
      <FamilyProfiles />
    </LocaleProvider>
  );
}

describe("FamilyProfiles", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem(
      "cealeg_user",
      JSON.stringify({ id: 42, email: "family@example.com" })
    );
    global.fetch = jest.fn();
  });

  it("shows the Family upgrade state for a free account", async () => {
    global.fetch.mockResolvedValue(
      jsonResponse({ enabled: false, plan: "free", profiles: [] })
    );

    renderProfiles();

    expect(await screen.findByRole("link", { name: "Vezi Family" })).toHaveAttribute(
      "href",
      "/pricing"
    );
    expect(screen.getByText("free")).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledWith("/api/backend/family/profiles");
  });

  it("selects, deletes and creates profiles for a Family account", async () => {
    const user = userEvent.setup();
    const primary = {
      id: 1,
      name: "Ana Popescu",
      color: "teal",
      isPrimary: true,
    };
    const child = {
      id: 2,
      name: "Copil",
      color: "violet",
      isPrimary: false,
    };
    const created = {
      id: 3,
      name: "Mara",
      color: "teal",
      isPrimary: false,
    };
    global.fetch
      .mockResolvedValueOnce(
        jsonResponse({ enabled: true, plan: "family", profiles: [primary, child] })
      )
      .mockResolvedValueOnce(jsonResponse({ ok: true }))
      .mockResolvedValueOnce(jsonResponse({ profile: created }, { status: 201 }));

    renderProfiles();

    const primaryButton = await screen.findByRole("button", {
      name: /Ana Popescu, profil activ/,
    });
    const childButton = screen.getByRole("button", { name: "Copil" });
    expect(primaryButton).toHaveAttribute("aria-pressed", "true");

    await user.click(childButton);
    expect(childButton).toHaveAttribute("aria-pressed", "true");
    expect(
      JSON.parse(localStorage.getItem("cealeg_active_profile:42"))
    ).toMatchObject({ id: 2, name: "Copil" });

    await user.click(
      screen.getByRole("button", { name: "Șterge profilul Copil" })
    );
    await waitFor(() => expect(screen.queryByText("Copil")).not.toBeInTheDocument());
    expect(primaryButton).toHaveAttribute("aria-pressed", "true");

    const nameInput = screen.getByRole("textbox", {
      name: "Numele membrului nou",
    });
    await user.type(nameInput, "Mara");
    await user.click(screen.getByRole("button", { name: "Adaugă" }));

    expect(await screen.findByText("Mara")).toBeInTheDocument();
    expect(nameInput).toHaveValue("");
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      "/api/backend/family/profiles/2",
      { method: "DELETE" }
    );
    expect(global.fetch).toHaveBeenNthCalledWith(
      3,
      "/api/backend/family/profiles",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "Mara", color: "teal", avatar: "user" }),
      })
    );
  });

  it("surfaces a localized backend error without exposing an empty panel", async () => {
    global.fetch.mockResolvedValue(
      jsonResponse(
        { code: "service_unavailable", error: "Temporar indisponibil." },
        { ok: false, status: 503 }
      )
    );

    renderProfiles();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Temporar indisponibil."
    );
    expect(screen.getByRole("link", { name: "Vezi Family" })).toBeInTheDocument();
  });
});
