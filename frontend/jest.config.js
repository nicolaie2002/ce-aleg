const nextJest = require("next/jest");

const createJestConfig = nextJest({
  dir: "./",
});

/** @type {import("jest").Config} */
const customJestConfig = {
  clearMocks: true,
  testEnvironment: "jsdom",
  setupFilesAfterEnv: ["<rootDir>/jest.setup.js"],
  testMatch: ["<rootDir>/__tests__/**/*.test.[jt]s?(x)"],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/$1",
  },
  collectCoverageFrom: [
    "app/**/*.{js,jsx,ts,tsx}",
    "instrumentation*.js",
    "proxy.js",
    "sentry.*.config.js",
    "!app/**/*.d.ts",
  ],
  coverageThreshold: {
    "./app/components/useTranslatedText.js": {
      branches: 75,
      functions: 95,
      lines: 95,
      statements: 95,
    },
    "./app/utils/analytics.js": {
      branches: 60,
      functions: 85,
      lines: 90,
      statements: 85,
    },
    "./app/utils/apiResponse.js": {
      branches: 90,
      functions: 95,
      lines: 95,
      statements: 95,
    },
    "./app/utils/authStorage.js": {
      branches: 50,
      functions: 60,
      lines: 75,
      statements: 70,
    },
  },
};

module.exports = createJestConfig(customJestConfig);
