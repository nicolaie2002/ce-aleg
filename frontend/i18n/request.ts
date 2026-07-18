import { getRequestConfig } from "next-intl/server";
import { cookies } from "next/headers";
import { defaultLocale, locales, type Locale } from "../i18n";
import { createIntlMessages } from "../messages/intlMessages";

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const requestedLocale = cookieStore.get("cealeg_locale")?.value;
  const locale = locales.includes(requestedLocale as Locale)
    ? (requestedLocale as Locale)
    : defaultLocale;

  const catalog = (await import(`../messages/${locale}.json`)).default;

  return {
    locale,
    messages: createIntlMessages(catalog),
  };
});
