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
