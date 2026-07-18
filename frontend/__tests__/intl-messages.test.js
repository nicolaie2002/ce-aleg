import englishCatalog from "../messages/en.json";
import romanianCatalog from "../messages/ro.json";
import { createIntlMessages } from "../messages/intlMessages";

function collectKeys(value, keys = []) {
  Object.entries(value || {}).forEach(([key, child]) => {
    keys.push(key);
    if (child && typeof child === "object") collectKeys(child, keys);
  });
  return keys;
}

describe("next-intl message catalogs", () => {
  it.each([
    ["Romanian", romanianCatalog],
    ["English", englishCatalog],
  ])("builds a valid keyed %s catalog", (_label, catalog) => {
    const messages = createIntlMessages(catalog);
    const keys = collectKeys(messages);

    expect(keys.length).toBeGreaterThan(10);
    expect(keys.filter((key) => key.includes("."))).toEqual([]);
    expect(Object.values(messages.common).every((message) => typeof message === "string"))
      .toBe(true);
  });
});
