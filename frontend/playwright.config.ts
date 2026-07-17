import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const port = Number(process.env.PLAYWRIGHT_PORT || 3000);
const localBaseUrl = `http://127.0.0.1:${port}`;
const externalBaseUrl = process.env.PLAYWRIGHT_BASE_URL;
const runFullStack = process.env.PLAYWRIGHT_FULL_STACK === "true";
const e2eDatabasePath = path
  .resolve(process.cwd(), "../backend/instance/e2e.db")
  .replaceAll("\\", "/");

const frontendServer = {
  command: process.env.CI
    ? `npm run start -- -H 127.0.0.1 -p ${port}`
    : `npm run dev -- --hostname 127.0.0.1 --port ${port}`,
  url: localBaseUrl,
  reuseExistingServer: !process.env.CI && !runFullStack,
  timeout: 120_000,
  env: {
    ...process.env,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "/api/backend",
    BACKEND_URL: process.env.BACKEND_URL || "http://127.0.0.1:5001",
    NEXT_TELEMETRY_DISABLED: "1",
  },
};

const backendServer = {
  command: "python ../backend/seed_e2e.py && python ../backend/app.py",
  url: "http://127.0.0.1:5001/health",
  reuseExistingServer: false,
  timeout: 120_000,
  env: {
    ...process.env,
    APP_ENV: "test",
    E2E_TEST_MODE: "true",
    DATABASE_URL: `sqlite:///${e2eDatabasePath}`,
    AUTH_SECRET: "e2e-only-auth-secret-with-at-least-32-characters",
    AUTH_RATE_LIMIT: "1000",
    AUTH_RATE_LIMIT_WINDOW: "60",
    GLOBAL_RATE_LIMIT: "10000",
    COOKIE_SECURE: "false",
    EXPOSE_DEV_AUTH_LINKS: "true",
    EMAIL_PROVIDER: "smtp",
    EMAIL_SMTP_HOST: "",
    OPENAI_API_KEY: "",
    SUPABASE_URL: "",
    SUPABASE_SERVICE_ROLE_KEY: "",
    SUPABASE_STORAGE_ENABLED: "false",
    EXTERNAL_CATALOG_ENABLED: "false",
    OPEN_PRICES_ENABLED: "false",
    STRIPE_SECRET_KEY: "",
    STRIPE_WEBHOOK_SECRET: "",
    FRONTEND_ORIGINS: localBaseUrl,
    PORT: "5001",
  },
};

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  workers: 2,
  reporter: process.env.CI ? [["line"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: externalBaseUrl || localBaseUrl,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    serviceWorkers: "allow",
  },
  webServer: externalBaseUrl
    ? undefined
    : runFullStack
      ? [backendServer, frontendServer]
      : frontendServer,
  projects: [
    {
      name: "chromium-desktop",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "chromium-mobile",
      use: { ...devices["Pixel 7"] },
    },
  ],
});
