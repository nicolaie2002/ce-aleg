"use client";

import { useEffect, useState } from "react";
import { Bot, CircleCheck, CircleDashed, Database, Languages, ScanText } from "lucide-react";
import { API_URL } from "../config";
import { useLocale } from "./LocaleProvider";

const fallbackItems = [
  { key: "localOcr", label: "Citire coduri si etichete", enabled: true },
  { key: "openFoodFacts", label: "Catalog Open Food Facts", enabled: true },
];

const icons = {
  localOcr: ScanText,
  localTranslation: Languages,
  cloudVision: Bot,
  openFoodFacts: Database,
};

const statusLabels = {
  localOcr: ["OCR local pentru coduri și etichete", "Local OCR for barcodes and labels"],
  localTranslation: ["Traducere locală", "Local translation"],
  cloudVision: ["Identificare vizuală opțională", "Optional visual identification"],
  openFoodFacts: ["Catalog Open Food Facts", "Open Food Facts catalog"],
  freeMode: ["Scanare și recomandări în modul gratuit", "Scanning and recommendations in free mode"],
};

export function AiStatusPanel({ compact = false }) {
  const { pick } = useLocale();
  const [items, setItems] = useState(fallbackItems);

  useEffect(() => {
    let active = true;

    async function loadStatus() {
      try {
        const response = await fetch(`${API_URL}/ai/status`);
        const data = await response.json();

        if (!response.ok || !active) return;

        setItems(
          Object.entries(data).map(([key, value]) => ({
            key,
            ...value,
          }))
        );
      } catch {
        // Păstrăm starea locală minimă dacă backend-ul nu răspunde temporar.
      }
    }

    loadStatus();

    return () => {
      active = false;
    };
  }, []);

  return (
    <section
      className="border-y border-white/10 bg-white/[0.035]"
      aria-label={pick("Starea serviciilor de scanare", "Scan service status")}
    >
      <div className={`ce-shell ${compact ? "py-3" : "py-5"}`}>
        {!compact && (
          <div className="mb-4">
            <p className="text-xs font-bold uppercase text-emerald-300">
              Asistent de cumpărături
            </p>
            <h2 className="mt-1 text-xl font-bold text-white">
              Totul este pregătit pentru scanare
            </h2>
          </div>
        )}

        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {items.map((item) => {
            const Icon = icons[item.key] || Bot;
            const StateIcon = item.enabled ? CircleCheck : CircleDashed;
            const localizedLabel = statusLabels[item.key]
              ? pick(...statusLabels[item.key])
              : item.label;

            return (
              <div
                key={item.key}
                className="flex items-center gap-3 rounded-lg border border-white/10 bg-black/20 px-3 py-3"
              >
                <Icon size={18} className="shrink-0 text-emerald-300" aria-hidden="true" />
                <span className="min-w-0 flex-1 text-xs font-semibold text-gray-200">
                  {localizedLabel}
                </span>
                <StateIcon
                  size={16}
                  className={item.enabled ? "text-emerald-300" : "text-gray-500"}
                  aria-hidden="true"
                />
                <span className="sr-only">
                  {item.enabled ? pick("disponibil", "available") : pick("indisponibil", "unavailable")}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
