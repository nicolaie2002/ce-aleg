export const locales = ["ro", "en"] as const;
export const defaultLocale = "ro" as const;
export type Locale = (typeof locales)[number];
