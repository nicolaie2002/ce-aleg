import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("public navigation and English help work", async ({ page }) => {
  await page.goto("/");
  await page.waitForLoadState("domcontentloaded");
  await expect(page.locator("body")).toContainText("Ce aleg?");

  await page.getByRole("button", { name: "English" }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");

  await page.goto("/help");
  await expect(page.getByRole("heading", { name: /How to use Ce aleg\?/i })).toBeVisible();
  await page.getByLabel("Search help").fill("account");
  await expect(page.locator("#help-results")).toContainText(/account/i);
});

test("English catalog store pages render localized content", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "English" }).click();
  await page.goto("/catalog-romania/magazine/lidl");

  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(
    page.getByRole("heading", { name: "Lidl: scan products and compare alternatives." }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "What to check on the shelf" })).toBeVisible();
  await expect(page.getByText(/This page helps people looking for Lidl products in Romania/)).toBeVisible();
  await expect(page.getByText("Pentru ce e util", { exact: true })).toHaveCount(0);
});

test("English catalog indexes and detail pages are fully localized", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "English" }).click();

  const routes = [
    ["/catalog-romania/magazine", "Stores in Romania where you can use Ce aleg?."],
    ["/catalog-romania/categorii", "Product categories worth scanning."],
    ["/catalog-romania/produse", "Real products you can search for and scan."],
    ["/catalog-romania/alternative", "Product alternatives people actually search for."],
    ["/catalog-romania/categorii/lactate", "Dairy: scan products and compare alternatives."],
    ["/catalog-romania/produse/iaurt-grecesc-2", "Greek yogurt 2%: what to check before buying."],
    ["/catalog-romania/alternative/iaurturi", "Alternatives to sweet yogurts."],
  ] as const;

  const forbiddenPhrases = [
    "Magazine din România unde poți folosi Ce aleg?",
    "Categorii de produse pe care merită să le scanezi",
    "Produse concrete pe care le poți căuta și scana",
    "Alternative la produse pe care oamenii chiar le caută",
    "Ce merită verificat",
    "Flux recomandat",
    "Produse exemplu pentru comparație",
  ];

  for (const [path, heading] of routes) {
    await page.goto(path);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
    const bodyText = await page.locator("body").innerText();
    expect(
      forbiddenPhrases.filter((phrase) => bodyText.includes(phrase)),
      `Untranslated catalog copy on ${path}`,
    ).toEqual([]);
  }
});

test("signed-out checkout guidance follows the selected language", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "English" }).click();
  await page.goto("/pricing");
  await page.getByRole("button", { name: "Choose monthly" }).first().click();

  await expect(
    page.getByText(
      "You need an account to buy plans or CeCoins. Sign in or create an account, then return to checkout.",
    ),
  ).toBeVisible();
  await expect(page.getByText(/Ai nevoie de cont ca sa cumperi/)).toHaveCount(0);
});

test("private product flows redirect signed-out visitors", async ({ page }) => {
  await page.goto("/dashboard");
  await page.waitForURL(/\/login(?:\?|$)/);
  await expect(page).toHaveURL(/\/login(?:\?|$)/);

  await page.goto("/barcode-scan");
  await page.waitForURL(/\/login(?:\?|$)/);
  await expect(page).toHaveURL(/\/login(?:\?|$)/);
});

for (const path of ["/", "/login", "/help", "/pricing"]) {
  test(`@a11y ${path} has no serious accessibility violations`, async ({ page }) => {
    await page.goto(path);
    await page.waitForLoadState("domcontentloaded");
    await expect(page.locator("main")).toBeVisible();
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const blockingViolations = results.violations.filter((violation) =>
      ["serious", "critical"].includes(violation.impact || ""),
    );

    expect(blockingViolations, JSON.stringify(blockingViolations, null, 2)).toEqual([]);
  });
}
