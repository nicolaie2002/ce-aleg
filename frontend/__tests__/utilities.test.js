import {
  getApiErrorMessage,
  localizeApiMessage,
  readApiJson,
} from "../app/utils/apiResponse";
import { getImageUrl } from "../app/utils/getImageUrl";
import {
  getPasswordStrength,
  getPasswordStrengthLabel,
  PASSWORD_MIN_LENGTH,
} from "../app/utils/passwordStrength";
import {
  ACTIVE_PROFILE_KEY,
  LEGACY_PREFERENCES_KEY,
  clearProfilePreferences,
  clearUserProfileStorage,
  getActiveProfile,
  getActiveProfileId,
  getActiveProfilePayload,
  getPreferencesKey,
  readProfilePreferences,
  saveProfilePreferences,
  setActiveProfile,
} from "../app/utils/profilePreferences";

jest.mock("../app/config", () => ({ API_URL: "/api/backend" }));

const pickEnglish = (_romanian, english) => english;
const pickRomanian = (romanian) => romanian;

describe("API response utilities", () => {
  it("reads JSON responses without touching the text body", async () => {
    const payload = { ok: true };
    const response = {
      headers: { get: jest.fn(() => "application/json; charset=utf-8") },
      json: jest.fn().mockResolvedValue(payload),
      text: jest.fn(),
    };

    await expect(readApiJson(response)).resolves.toEqual(payload);
    expect(response.json).toHaveBeenCalledTimes(1);
    expect(response.text).not.toHaveBeenCalled();
  });

  it.each([
    ["<html>temporarily unavailable</html>", /pagin/],
    ["upstream unavailable", /serverului/],
  ])("normalizes a non-JSON body: %s", async (body, expectedError) => {
    const response = {
      headers: { get: jest.fn(() => "text/plain") },
      text: jest.fn().mockResolvedValue(body),
    };

    const result = await readApiJson(response);

    expect(result.code).toBe("invalid_server_response");
    expect(result.error).toMatch(expectedError);
  });

  it("handles an unreadable non-JSON body", async () => {
    const response = {
      headers: { get: jest.fn(() => null) },
      text: jest.fn().mockRejectedValue(new Error("stream closed")),
    };

    await expect(readApiJson(response)).resolves.toMatchObject({
      code: "invalid_server_response",
    });
  });

  it("localizes known codes, exact messages and account requirements", () => {
    expect(localizeApiMessage("ignored", pickEnglish, "auth_required")).toBe(
      "Sign in is required."
    );
    expect(localizeApiMessage("Autentificare necesara.", pickEnglish)).toBe(
      "Sign in is required."
    );
    expect(
      localizeApiMessage("Pentru cont trebuie acordul unui parinte.", pickEnglish)
    ).toMatch(/^To create an account/);
    expect(localizeApiMessage("", pickEnglish)).toBe("");
  });

  it.each([
    [
      "Parola trebuie sa aib\u0103 minimum 12 caractere.",
      "The password must have at least 12 characters.",
    ],
    [
      "Ai nevoie de 30 CeCoins pentru aceast\u0103 recompens\u0103.",
      "You need 30 CeCoins for this reward.",
    ],
    ["Mai ai nevoie de 4 CeCoins.", "You need 4 more CeCoins."],
    [
      "Po\u021bi revendica cel mult 20 CeCoins pe zi.",
      "You can claim up to 20 CeCoins per day.",
    ],
    [
      "Fi\u0219ierul eticheta.jpg este prea mare.",
      "eticheta.jpg is too large.",
    ],
  ])("localizes the dynamic API message %s", (message, expected) => {
    expect(localizeApiMessage(message, pickEnglish)).toBe(expected);
  });

  it("keeps unknown messages in Romanian and falls back in English", () => {
    expect(localizeApiMessage("Mesaj nou", pickRomanian)).toBe("Mesaj nou");
    expect(
      getApiErrorMessage({ error: "Mesaj nou" }, pickEnglish, "Eroare", "New error")
    ).toBe("New error");
    expect(getApiErrorMessage({}, pickEnglish, "Eroare", "Error")).toBe("Error");
  });

  it("prefers a translated API code over a server message", () => {
    expect(
      getApiErrorMessage(
        { message: "server detail", code: "wrong_account" },
        pickEnglish,
        "Eroare",
        "Error"
      )
    ).toBe("You cannot access another account's data.");
  });
});

describe("profile preference storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  function storeUser(id) {
    localStorage.setItem("cealeg_user", JSON.stringify({ id }));
  }

  it("does nothing when no valid account owns the storage", () => {
    expect(getActiveProfile()).toBeNull();
    expect(getActiveProfileId()).toBeNull();
    expect(getActiveProfilePayload()).toEqual({});
    expect(getPreferencesKey("child")).toBeNull();

    setActiveProfile({ id: 4 });
    saveProfilePreferences("child", { vegetarian: true });
    clearProfilePreferences("child");

    expect(localStorage.length).toBe(0);
  });

  it("namespaces the active profile and dispatches a change event", () => {
    storeUser("user/7");
    const listener = jest.fn();
    window.addEventListener("cealeg:profile-change", listener);

    setActiveProfile({ id: 12, name: "Ana" });

    expect(localStorage.getItem(`${ACTIVE_PROFILE_KEY}:user%2F7`)).toContain("Ana");
    expect(getActiveProfile()).toEqual({ id: 12, name: "Ana" });
    expect(getActiveProfileId()).toBe(12);
    expect(getActiveProfilePayload()).toEqual({ family_profile_id: 12 });
    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener.mock.calls[0][0].detail).toEqual({ id: 12, name: "Ana" });

    window.removeEventListener("cealeg:profile-change", listener);
  });

  it("saves, reads and clears primary and profile-specific preferences", () => {
    storeUser(7);
    const preferences = { vegetarian: true, allergens: ["nuts"] };

    expect(getPreferencesKey(null)).toBe(`${LEGACY_PREFERENCES_KEY}:7:primary`);
    expect(getPreferencesKey("child/a")).toBe(
      `${LEGACY_PREFERENCES_KEY}:7:child%2Fa`
    );

    saveProfilePreferences("child/a", preferences);
    expect(readProfilePreferences("child/a")).toEqual(preferences);

    clearProfilePreferences("child/a");
    expect(readProfilePreferences("child/a")).toBeNull();
  });

  it("returns null for corrupt account and preference records", () => {
    localStorage.setItem("cealeg_user", "not-json");
    expect(getActiveProfile()).toBeNull();
    expect(getPreferencesKey("child")).toBeNull();

    storeUser(7);
    localStorage.setItem(getPreferencesKey("child"), "not-json");
    localStorage.setItem(`${ACTIVE_PROFILE_KEY}:7`, "not-json");

    expect(readProfilePreferences("child")).toBeNull();
    expect(getActiveProfile()).toBeNull();
  });

  it("clears only the requested user's namespaced data plus unsafe legacy keys", () => {
    localStorage.setItem(`${ACTIVE_PROFILE_KEY}:7`, JSON.stringify({ id: 1 }));
    localStorage.setItem(`${LEGACY_PREFERENCES_KEY}:7:primary`, "{}");
    localStorage.setItem(`${LEGACY_PREFERENCES_KEY}:7:child`, "{}");
    localStorage.setItem(`${LEGACY_PREFERENCES_KEY}:8:primary`, "keep");
    localStorage.setItem(`${LEGACY_PREFERENCES_KEY}:old-profile`, "legacy");
    localStorage.setItem(ACTIVE_PROFILE_KEY, "legacy-active");
    localStorage.setItem(LEGACY_PREFERENCES_KEY, "legacy-preferences");

    clearUserProfileStorage(7);

    expect(localStorage.getItem(`${ACTIVE_PROFILE_KEY}:7`)).toBeNull();
    expect(localStorage.getItem(`${LEGACY_PREFERENCES_KEY}:7:primary`)).toBeNull();
    expect(localStorage.getItem(`${LEGACY_PREFERENCES_KEY}:7:child`)).toBeNull();
    expect(localStorage.getItem(`${LEGACY_PREFERENCES_KEY}:8:primary`)).toBe("keep");
    expect(localStorage.getItem(`${LEGACY_PREFERENCES_KEY}:old-profile`)).toBeNull();
    expect(localStorage.getItem(ACTIVE_PROFILE_KEY)).toBeNull();
    expect(localStorage.getItem(LEGACY_PREFERENCES_KEY)).toBeNull();
  });
});

describe("password strength", () => {
  it("returns actionable suggestions for an empty password", () => {
    const strength = getPasswordStrength("");

    expect(PASSWORD_MIN_LENGTH).toBe(8);
    expect(strength).toMatchObject({ label: "slaba", score: 0, percent: 25 });
    expect(strength.suggestions).toHaveLength(4);
  });

  it.each([
    ["abcdefgh", "slaba", 1, 35],
    ["Abcdefg1", "medie", 3, 66],
    ["Aa1!aaaa", "medie", 4, 66],
    ["Aa1!aaaaaaaa", "puternica", 5, 100],
  ])("classifies %s as %s", (password, label, score, percent) => {
    expect(getPasswordStrength(password)).toMatchObject({ label, score, percent });
  });

  it.each([
    ["slaba", "Weak"],
    ["medie", "Medium"],
    ["puternica", "Strong"],
  ])("localizes the %s label", (label, expected) => {
    expect(getPasswordStrengthLabel({ label }, pickEnglish)).toBe(expected);
  });
});

describe("image URL normalization", () => {
  it.each([
    [null, ""],
    ["", ""],
    ["https://cdn.example/product.jpg", "https://cdn.example/product.jpg"],
    ["http://cdn.example/product.jpg", "http://cdn.example/product.jpg"],
    ["/uploads/product.jpg", "/api/backend/uploads/product.jpg"],
    ["/images/placeholder.png", "/images/placeholder.png"],
  ])("maps %p to %p", (input, expected) => {
    expect(getImageUrl(input)).toBe(expected);
  });
});
