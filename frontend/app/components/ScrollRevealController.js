"use client";

import { useEffect } from "react";

const revealSelectors = [
  ".ce-reveal",
  ".ce-panel",
  ".ce-lifted-shell",
  ".ce-interactive-surface",
  ".ce-plan-card",
  ".ce-store-card",
  ".ce-stat-card",
  ".ce-family-panel",
  ".ce-pricing-note",
  ".ce-usage-banner",
  "main article",
  "main .rounded-3xl.border",
  "main .rounded-2xl.border",
  "main .rounded-xl.border",
  "main .rounded-lg.border",
].join(",");

function shouldReveal(element) {
  if (!element || element.closest("[data-no-scroll-reveal]")) return false;
  if (element.closest(".ce-mobile-dock")) return false;
  if (element.matches("button, a, input, textarea, select, label")) return false;

  const rect = element.getBoundingClientRect();
  if (rect.width < 96 || rect.height < 44) return false;

  return true;
}

export function ScrollRevealController() {
  useEffect(() => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    if (reducedMotion.matches) return undefined;

    const seen = new WeakSet();
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.setAttribute("data-ce-scroll-reveal", "in");
            observer.unobserve(entry.target);
          }
        });
      },
      {
        rootMargin: "0px 0px -10% 0px",
        threshold: 0.12,
      }
    );

    function collect() {
      let index = 0;
      document.querySelectorAll(revealSelectors).forEach((element) => {
        if (seen.has(element) || !shouldReveal(element)) return;

        seen.add(element);
        element.style.setProperty("--ce-reveal-index", String(Math.min(index, 10)));
        element.setAttribute("data-ce-scroll-reveal", "pending");
        observer.observe(element);
        index += 1;
      });
    }

    collect();
    const mutationObserver = new MutationObserver(() => {
      window.requestAnimationFrame(collect);
    });

    mutationObserver.observe(document.body, {
      childList: true,
      subtree: true,
    });

    return () => {
      observer.disconnect();
      mutationObserver.disconnect();
    };
  }, []);

  return null;
}
