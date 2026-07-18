const { chromium } = require("@playwright/test");

module.exports = {
  ci: {
    collect: {
      startServerCommand: "npm run start -- -H 127.0.0.1 -p 3100",
      startServerReadyPattern: "Ready in",
      startServerReadyTimeout: 120000,
      chromePath: chromium.executablePath(),
      url: [
        "http://127.0.0.1:3100/",
        "http://127.0.0.1:3100/help",
        "http://127.0.0.1:3100/pricing",
      ],
      numberOfRuns: 1,
      settings: {
        chromeFlags: "--no-sandbox --disable-dev-shm-usage",
      },
    },
    assert: {
      assertions: {
        "categories:performance": ["error", { minScore: 0.7 }],
        "categories:accessibility": ["error", { minScore: 0.95 }],
        "categories:best-practices": ["error", { minScore: 0.9 }],
        "categories:seo": ["error", { minScore: 0.9 }],
      },
    },
    upload: {
      target: "filesystem",
      outputDir: ".lighthouseci/reports",
    },
  },
};
