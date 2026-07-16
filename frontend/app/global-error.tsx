"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="ro">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Eroare / Error - Ce aleg?</title>
        <style>{`
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body { font-family: system-ui, -apple-system, sans-serif; background: #0a0f1a; color: #e8edf5; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 2rem; }
          .container { max-width: 400px; width: 100%; text-align: center; }
          .icon { align-items: center; border: 2px solid #fca5a5; border-radius: 999px; color: #fecaca; display: inline-flex; font-size: 2rem; font-weight: 900; height: 4rem; justify-content: center; margin-bottom: 1.5rem; width: 4rem; }
          h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 1rem; }
          p { font-size: 0.9375rem; color: #b4c0d0; margin-bottom: 1.5rem; line-height: 1.6; }
          p span { display: block; margin-top: 0.75rem; }
          button { background: #06b6d4; color: #020617; font-weight: 800; padding: 0.75rem 1.5rem; border: none; border-radius: 0.5rem; cursor: pointer; transition: background 0.2s; }
          button:hover { background: #22d3ee; }
          button:focus-visible { outline: 3px solid #fff; outline-offset: 3px; }
        `}</style>
      </head>
      <body>
        <main className="container">
          <div className="icon" aria-hidden="true">
            !
          </div>
          <h1>A apărut o eroare critică</h1>
          <p>
            Aplicația a întâmpinat o problemă și nu poate continua. Te rugăm să reîncarci pagina.
            <span lang="en">
              The application encountered a problem and cannot continue. Please reload the page.
            </span>
          </p>
          <button type="button" onClick={reset}>
            Reîncarcă pagina / Reload page
          </button>
        </main>
      </body>
    </html>
  );
}
