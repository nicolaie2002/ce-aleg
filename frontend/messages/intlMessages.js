const commonMessageSources = {
  dashboard: "Dashboard",
  scan: "Scanare",
  catalog: "Catalog",
  missions: "Misiuni",
  pricing: "Planuri",
  cart: "Coș",
  history: "Istoric",
  favorites: "Favorite",
  preferences: "Preferințe",
  help: "Ajutor",
  support: "Suport",
  login: "Autentificare",
  register: "Creează cont",
  logout: "Deconectare",
  back: "Înapoi",
  retry: "Reîncearcă",
  save: "Salvează",
  delete: "Șterge",
  close: "Închide",
};

export function createIntlMessages(catalog = {}) {
  const common = catalog.common || {};

  return {
    common: Object.fromEntries(
      Object.entries(commonMessageSources).map(([key, source]) => [
        key,
        common[source] || source,
      ])
    ),
  };
}
