import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";

const accessibilityRules = {
  "jsx-a11y/anchor-is-valid": "error",
  "jsx-a11y/click-events-have-key-events": "error",
  "jsx-a11y/no-noninteractive-element-interactions": "error",
  "jsx-a11y/role-has-required-aria-props": "error",
  "jsx-a11y/aria-props": "error",
  "jsx-a11y/alt-text": "error",
  "jsx-a11y/img-redundant-alt": "error",
  "jsx-a11y/no-autofocus": "warn",
  "jsx-a11y/tabindex-no-positive": "error",
};

const eslintConfig = defineConfig([
  ...nextVitals.map((config, index) => (
    index === 0
      ? { ...config, rules: { ...config.rules, ...accessibilityRules } }
      : config
  )),
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    ".open-next/**",
    ".wrangler/**",
    "coverage/**",
    "test-results/**",
    "playwright-report/**",
    "blob-report/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "cloudflare-env.d.ts",
  ]),
]);

export default eslintConfig;
