"use client";

import { Settings2 } from "lucide-react";
import { CONSENT_MANAGER_EVENT } from "../utils/consent";
import { useLocale } from "./LocaleProvider";

export function CookieManager({ className = "" }) {
  const { pick } = useLocale();

  function openManager() {
    window.dispatchEvent(new Event(CONSENT_MANAGER_EVENT));
  }

  return (
    <button
      type="button"
      onClick={openManager}
      className={className}
      aria-haspopup="dialog"
    >
      <Settings2 size={15} aria-hidden="true" />
      {pick("Gestionează cookie-urile", "Manage cookies")}
    </button>
  );
}
