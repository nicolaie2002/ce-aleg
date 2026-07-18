import { expect, Page, test } from "@playwright/test";


const E2E_PASSWORD = "E2e-password-123";
const runFullStack = process.env.PLAYWRIGHT_FULL_STACK === "true";


function buildUniqueEan13(seed: number) {
  const base = `59${String(seed).slice(-10)}`;
  const weightedSum = [...base].reduce(
    (sum, digit, index) => sum + Number(digit) * (index % 2 === 0 ? 1 : 3),
    0
  );
  return `${base}${(10 - (weightedSum % 10)) % 10}`;
}


async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "Email", exact: true }).fill(email);
  await page.getByLabel("Parola", { exact: true }).fill(E2E_PASSWORD);
  await page.getByRole("button", { name: "Autentificare" }).click();
  await page.waitForURL(/\/dashboard(?:\?|$)/);
  await expect(page.getByRole("heading", { name: /Salut,/ })).toBeVisible();
}


async function registerAndVerify(page: Page, email: string, inviteCode = "") {
  await page.goto("/register");
  await page.getByLabel("Nume").fill("Membru E2E");
  await page.getByRole("textbox", { name: "Email", exact: true }).fill(email);
  if (inviteCode) {
    await page.getByPlaceholder("CE-XXXXXX").fill(inviteCode);
  }
  await page.getByLabel("Parola", { exact: true }).fill(E2E_PASSWORD);
  const checkboxes = page.getByRole("checkbox");
  await checkboxes.nth(0).check();
  await checkboxes.nth(1).check();
  await page.getByRole("button", { name: "Creează cont", exact: true }).click();

  const verificationLink = page.getByRole("link", {
    name: "Deschide linkul local de confirmare",
  });
  await expect(verificationLink).toBeVisible();
  const href = await verificationLink.getAttribute("href");
  expect(href).toBeTruthy();
  const verificationUrl = new URL(href as string, page.url());
  await page.evaluate(() => localStorage.setItem("cealeg_onboarding_completed", "1"));
  await page.goto(`${verificationUrl.pathname}${verificationUrl.search}`);
  await expect(page.getByRole("heading", { name: "Cont activat." })).toBeVisible();
  await page.waitForURL(/\/dashboard(?:\?|$)/);
}


test.describe("critical full-stack journeys", () => {
  test.skip(!runFullStack, "Run with PLAYWRIGHT_FULL_STACK=true.");
  test.skip(({ isMobile }) => Boolean(isMobile), "Data-mutating journeys run once on desktop.");
  test.setTimeout(120_000);
  test.describe.configure({ mode: "serial" });

  test("register, verify email, sign out, and sign in", async ({ page }) => {
    const email = `register-${Date.now()}@cealeg.test`;
    await registerAndVerify(page, email);

    await page.getByRole("button", { name: "Deconectare" }).click();
    await page.waitForURL(/\/$/);
    await login(page, email);
  });

  test("scan a barcode and add the product to cart", async ({ page }) => {
    await login(page, "pro.e2e@cealeg.test");
    await page.goto("/barcode-scan");
    await page.getByPlaceholder("Ex: 5449000000996").fill("5449000000996");
    await page.getByRole("button", { name: "Caută produsul", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Iaurt natural E2E" })).toBeVisible();
    await page.getByRole("button", { name: "Adaugă în coș" }).click();
    await expect(page.getByText(/Produs adăugat în coș/)).toBeVisible();

    await page.goto("/cart");
    await expect(
      page.getByRole("heading", { level: 3, name: "Iaurt natural E2E" }),
    ).toBeVisible();
  });

  test("search a product, save it as favorite, and view alternatives", async ({ page }) => {
    await login(page, "pro.e2e@cealeg.test");
    await page.goto("/scan?store=any");
    await page.getByLabel("Nume sau cod de pe ambalaj").fill("Iaurt natural E2E");
    await page.getByRole("button", { name: /Iaurt natural E2E/ }).click();
    await page.getByRole("button", { name: "Vezi analiza produsului selectat" }).click();
    await page.waitForURL(/\/result(?:\?|$)/);
    await expect(page.getByText("Iaurt natural E2E").first()).toBeVisible();

    await page.getByRole("button", { name: "Adaugă la favorite" }).click();
    await expect(page.getByText("Produsul a fost salvat la favorite.")).toBeVisible();
    await page.getByRole("link", { name: "Caută alternative potrivite" }).click();
    await page.waitForURL(/\/alternatives\?/);
    await expect(page.getByRole("heading", { name: /Variante mai bune/ })).toBeVisible();
  });

  test("a Pro subscription exposes unlimited scans", async ({ page }) => {
    await login(page, "pro.e2e@cealeg.test");
    await page.goto("/pricing");
    await expect(page.getByText(/Planul Pro este activ/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Planul tău actual" })).toBeDisabled();
  });

  test("the administration surface follows the selected English locale", async ({ page }) => {
    await login(page, "admin.e2e@cealeg.test");
    await page.getByRole("button", { name: "English" }).click();
    await page.goto("/admin");

    await expect(page.getByText("Platform administration", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Post-launch monitoring." })).toBeVisible();
    await expect(page.getByRole("button", { name: "Reload data" })).toBeEnabled();
    await expect(page.getByRole("heading", { name: "Quality and recategorization" })).toBeVisible();
    await expect(page.getByText("Payments and emails", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "What people search for but cannot find" })).toBeVisible();

    const bodyText = await page.locator("body").innerText();
    const untranslatedPhrases = [
      "Administrare platformă",
      "Monitorizare după lansare.",
      "Reîncarcă datele",
      "Calitate și recategorizare",
      "Plăți și emailuri",
      "Ce caută oamenii și lipsește",
      "Caută utilizator după email",
    ];
    expect(untranslatedPhrases.filter((phrase) => bodyText.includes(phrase))).toEqual([]);
  });

  test("scanner, contribution, and alternatives flows follow the selected English locale", async ({ page }) => {
    const browserErrors: string[] = [];
    page.on("pageerror", (error) => browserErrors.push(error.message));
    page.on("console", (message) => {
      if (message.type() !== "error") return;
      const sourceUrl = message.location().url;
      browserErrors.push(
        sourceUrl ? `${message.text()} [${sourceUrl}]` : message.text(),
      );
    });

    await login(page, "pro.e2e@cealeg.test");
    await page.getByRole("button", { name: "English" }).click();

    await page.goto("/barcode-scan");
    await expect(page.getByRole("heading", {
      name: "Scan the barcode. Confirm the product.",
    })).toBeVisible();
    await expect(page.getByRole("link", { name: "Search by name" }).first()).toBeVisible();
    let bodyText = await page.locator("body").innerText();
    expect([
      "Scanare după nume",
      "Scanare cod de bare",
      "Magazin curent",
      "Camera folosită",
      "Introdu codul manual",
    ].filter((phrase) => bodyText.includes(phrase))).toEqual([]);

    await page.goto("/submit-product");
    await expect(page.getByRole("heading", { name: "Add a new product" })).toBeVisible();
    await expect(page.getByText("Fast mobile flow", { exact: true })).toBeVisible();
    await expect(page.getByText("Your submissions", { exact: true })).toBeVisible();
    bodyText = await page.locator("body").innerText();
    expect([
      "Adaugă un produs nou",
      "Flow rapid pe telefon",
      "Nume produs",
      "Propunerile tale",
    ].filter((phrase) => bodyText.includes(phrase))).toEqual([]);

    await page.goto("/alternatives?store=any");
    await expect(page.getByRole("heading", {
      name: "Better options for the scanned product.",
    })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Recommended alternatives", { exact: true })).toBeVisible();
    bodyText = await page.locator("body").innerText();
    expect([
      "Alternative recomandate",
      "Variante mai bune pentru produsul scanat",
      "Magazin selectat",
      "Produs scanat",
    ].filter((phrase) => bodyText.includes(phrase))).toEqual([]);
    expect(browserErrors).toEqual([]);
  });

  test("English action controls are localized across the application", async ({ page }) => {
    await login(page, "pro.e2e@cealeg.test");
    await page.getByRole("button", { name: "English" }).click();

    const routes = [
      "/dashboard",
      "/barcode-scan",
      "/scan?store=any",
      "/alternatives?store=any",
      "/cart",
      "/favorites",
      "/history",
      "/missions",
      "/live-assistant",
      "/submit-product",
      "/preferences",
      "/pricing",
      "/help",
      "/support",
      "/privacy",
      "/terms",
      "/catalog-romania",
      "/catalog-romania/magazine",
      "/catalog-romania/magazine/lidl",
      "/catalog-romania/categorii",
      "/catalog-romania/categorii/lactate",
      "/catalog-romania/produse",
      "/catalog-romania/alternative",
      "/store",
      "/onboarding",
      "/delete-account",
    ];
    const romanianAction = new RegExp(
      String.raw`\b(?:Înapoi|Inapoi|Scanează|Scaneaza|Caută|Cauta|Adaugă|Adauga|Șterge|Sterge|Salvează|Salveaza|Încarcă|Incarca|Reîncarcă|Reincarca|Încearcă|Incearca|Trimite|Vezi|Alege|Selectează|Selecteaza|Închide|Inchide|Pornește|Porneste|Oprește|Opreste|Schimbă|Schimba|Continuă|Continua|Refuză|Refuza|Acceptă|Accepta|Gestionează|Gestioneaza|Deconectare|Autentificare|Creează|Creeaza|Confirmă|Confirma|Verifică|Verifica|Publică|Publica|Anulează|Anuleaza|Cumpără|Cumpara|Plătește|Plateste|Deschide|Editează|Editeaza|Aplică|Aplica)\b`,
      "i",
    );
    const failures: string[] = [];

    for (const route of routes) {
      await page.goto(route);
      await page.waitForLoadState("domcontentloaded");
      await expect(page.locator("html")).toHaveAttribute("lang", "en");
      await page.waitForTimeout(250);

      const controlTexts = await page
        .locator("button, a, label, input, textarea, select, [role='button'], [role='link']")
        .evaluateAll((elements) => elements.map((element) => {
          const values = [
            element.textContent,
            element.getAttribute("aria-label"),
            element.getAttribute("placeholder"),
            element.getAttribute("title"),
            element.getAttribute("alt"),
          ];
          return values.filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
        }));
      const offenders = [...new Set(controlTexts.filter((value) => romanianAction.test(value)))];
      if (offenders.length > 0) {
        failures.push(`${route}: ${offenders.join(" | ")}`);
      }
    }

    expect(failures, failures.join("\n")).toEqual([]);
  });

  test("a verified invite grants the referral bonus", async ({ page }) => {
    const email = `invite-${Date.now()}@cealeg.test`;
    await registerAndVerify(page, email, "CE-PRO001");
    const response = await page.request.get("/api/backend/auth/me");
    expect(response.ok()).toBeTruthy();
    const payload = await response.json();
    expect(payload.user.bonusUnlimitedUntil).toBeTruthy();
  });

  test("submit a product, review it, and publish it as admin", async ({ browser, page }) => {
    const submissionSeed = Date.now();
    const productName = `Produs comunitate ${submissionSeed}`;
    const barcode = buildUniqueEan13(submissionSeed);
    await login(page, "pro.e2e@cealeg.test");
    await page.goto("/submit-product");
    await page.locator("#front-image-capture").setInputFiles("public/brand/ce-aleg-icon.png");
    await page.locator("#nutrition-image-capture").setInputFiles("public/brand/ce-aleg-icon.png");
    await page.getByPlaceholder("Ex: Monster Energy Ultra White").fill(productName);
    await page.getByPlaceholder("Ex: Monster", { exact: true }).fill("Brand E2E");
    await page.getByPlaceholder("Ex: 5941238013309").fill(barcode);
    await page.getByPlaceholder("Ex: 500").fill("500");
    await page.getByPlaceholder("Ex: 11").fill("70");
    const zeroInputs = page.getByPlaceholder("Ex: 0");
    await zeroInputs.nth(0).fill("8");
    await zeroInputs.nth(1).fill("4");
    await zeroInputs.nth(2).fill("2");
    await page.getByPlaceholder(/fără zahăr/).fill("lapte, culturi lactice");
    await page.getByRole("button", { name: /Trimite la verificare/ }).click();
    await expect(page.getByText(/Produsul a fost trimis la verificare/)).toBeVisible();

    const adminContext = await browser.newContext();
    const adminPage = await adminContext.newPage();
    await login(adminPage, "admin.e2e@cealeg.test");
    await adminPage.goto("/admin");
    await expect(adminPage.getByRole("button", { name: "Reîncarcă datele" })).toBeEnabled({
      timeout: 15_000,
    });
    const submission = adminPage.locator("article").filter({ hasText: productName });
    await expect(submission).toBeVisible();
    await submission.getByRole("button", { name: "Verifică" }).click();
    await expect(submission.getByText("Gata de publicat")).toBeVisible({ timeout: 15_000 });
    await submission.getByRole("button", { name: "Publica" }).click();
    await expect(submission.getByText("Aprobat")).toBeVisible({ timeout: 15_000 });
    await adminContext.close();
  });

  test("account deletion requires and consumes a confirmation link", async ({ page }) => {
    const email = `delete-${Date.now()}@cealeg.test`;
    await registerAndVerify(page, email);
    await page.getByRole("button", { name: "Șterge contul", exact: true }).click();
    await page.getByRole("button", { name: "Trimite confirmarea" }).click();
    const deletionLink = page.getByRole("link", { name: "Deschide linkul local de confirmare" });
    await expect(deletionLink).toBeVisible();
    const href = await deletionLink.getAttribute("href");
    const deletionUrl = new URL(href as string, page.url());
    await page.goto(`${deletionUrl.pathname}${deletionUrl.search}`);
    await page.getByRole("button", { name: "Șterge contul definitiv" }).click();
    await expect(page.getByRole("heading", { name: "Datele contului au fost eliminate." })).toBeVisible();

    const loginResponse = await page.request.post("/api/backend/login", {
      data: { email, password: E2E_PASSWORD },
    });
    expect(loginResponse.status()).toBe(401);
  });
});

test.describe("production offline support", () => {
  test.skip(!runFullStack, "Run with PLAYWRIGHT_FULL_STACK=true.");
  test.setTimeout(30_000);

  test("the web app manifest exposes an installable application shell", async ({ page }) => {
    const response = await page.request.get("/manifest.webmanifest");
    expect(response.ok()).toBeTruthy();

    const manifest = await response.json();
    expect(manifest.name).toBe("Ce aleg?");
    expect(manifest.start_url).toBe("/");
    expect(manifest.scope).toBe("/");
    expect(manifest.display).toBe("standalone");
    expect(manifest.icons).toEqual(expect.arrayContaining([
      expect.objectContaining({ src: "/icon.png", purpose: "any maskable" }),
    ]));

    const iconResponse = await page.request.get("/icon.png");
    expect(iconResponse.ok()).toBeTruthy();
    expect(iconResponse.headers()["content-type"]).toContain("image/png");
  });

  test("the production service worker serves the offline fallback", async ({ context, page }) => {
    await page.goto("/");
    await page.evaluate(async () => {
      await navigator.serviceWorker.ready;
    });
    await page.reload();
    await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller));
    await context.setOffline(true);
    try {
      await page.goto(`/offline-check-${Date.now()}`);
      await expect(page.getByRole("heading", { name: "Momentan ești offline" })).toBeVisible();
    } finally {
      await context.setOffline(false);
    }
  });
});
