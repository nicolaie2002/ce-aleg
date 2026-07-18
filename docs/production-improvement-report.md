# Raport Production Improvement Plan

**Actualizat:** 18 iulie 2026

**Ramură:** `main`

**Politică de cost:** fără servicii sau abonamente noi plătite

## Verdict

Codul este într-o stare mult mai apropiată de lansare și toate porțile locale
automatizate sunt verzi. Sign-off-ul final rămâne condiționat de verificările
live care nu pot fi demonstrate din repository: email real, Stripe live,
backup/restore, deployment și test pe telefoane reale.

## Dovezi curente

| Poartă | Rezultat |
| --- | --- |
| Backend pytest | 359 teste trecute; 73,35% `app.py`, 100% `api_docs.py`, prag 70% |
| Frontend Jest | 16 suite și 84 teste trecute |
| Coverage țintit frontend | componente 61,37% statements / 62,61% lines; utils 88,56% / 93,54%; prag automat 60% |
| Playwright full stack | 32 trecute, 10 sărite intenționat pe mobil, 0 eșuate |
| ESLint și TypeScript | trecute fără warnings/errors |
| Next.js build | trecut, 66 rute generate |
| Bundle | toate cele 41 rute sub 500 KB gzip; maxim 200,0 KB |
| Lighthouse `/` | performance 78, accessibility 100, best practices 100, SEO 100 |
| Lighthouse `/help` | performance 77, accessibility 100, best practices 100, SEO 100 |
| Lighthouse `/pricing` | performance 77, accessibility 100, best practices 96, SEO 100 |
| Backend p95 local | health 0,65 ms; produse 4,94 ms; catalog stats 0,82 ms |
| Dependențe Python | `pip-audit`: zero vulnerabilități cunoscute |
| Dependențe frontend | `npm audit`: zero vulnerabilități |
| Securitate Python | Bandit medium/high: zero constatări |

Cele 10 teste E2E sărite sunt scenariile mutabile din proiectul mobil. Ele
rulează o singură dată în proiectul desktop pentru a nu modifica simultan
aceeași bază E2E. Testele publice, traducerile, accesibilitatea, manifestul și
offline-ul rulează atât desktop, cât și mobil.

## Îmbunătățiri implementate

- Politici explicite de acces pentru toate cele 105 rute backend și teste care
  opresc apariția rutelor fără clasificare public/auth/admin/cron.
- OpenAPI descrie toate cele 109 operații runtime cu contracte explicite pentru
  răspunsuri, payload-uri și tipuri media, inclusiv dashboard, Family, coș,
  favorite, istoric, cont, confidențialitate, scanare AI, contribuții, admin,
  cron și Stripe. Securitatea documentată folosește aceeași politică declarativă
  ca runtime-ul, iar testele interzic reapariția contractelor `inferred`.
- App factory Flask, migrări Alembic versionate și verificarea migration head la
  pornirea în producție.
- Rate limiting și cache Redis distribuit cu fallback local, plus Render Key
  Value gratuit legat prin `REDIS_URL`.
- Validare de input, limite de payload, headere de securitate, logging JSON și
  tratare uniformă a erorilor API RO/EN.
- Stripe Checkout/Portal/webhook idempotent în cod și teste; activarea planului
  rămâne condiționată de confirmarea Stripe.
- Consimțământ granular, jurnal server-side, export/acces/restricționare date și
  retenție automată.
- Traduceri RO/EN extinse pe catalog, magazine, scanner, contribuții, admin și
  mesajele pentru utilizatorii nelogați.
- Pagină Help, protecție pentru checkout nelogat, timeout controlat la misiuni și
  retrimitere manuală a emailului de confirmare din admin.
- PWA refăcută cu service worker static: offline stabil, update controlat și fără
  cache pentru API/Supabase sau date private. Au fost eliminate 182 de pachete
  tranzitive Workbox/PWA.
- Convenția Next.js depreciată `middleware.js` a fost migrată la `proxy.js`;
  buildul nu mai emite avertismentul de compatibilitate. Proxy-ul este inclus
  explicit în TypeScript/Jest și are praguri de minimum 90% linii/statements,
  75% branches și 100% funcții.
- Fluxurile Family Profiles, statusul serviciilor AI și actualizarea PWA au teste
  dedicate. CI recalculează coverage-ul ponderat și oprește regresiile sub 60%
  statements/linii separat pentru `app/components` și `app/utils`.
- CI extins cu audit de dependențe, Bandit, coverage 70%, E2E, Lighthouse,
  verificare Cloudflare Workers și smoke test al runtime-ului Linux.
- Job gratuit GitHub Actions pentru maintenance zilnic și backup săptămânal;
  maintenance are lock Redis, identificator de rulare, durate și avertismente.
- Auto-deploy backend Render numai după ce CI trece; deploy hook-ul gratuit rămâne
  fallback manual cu verificarea commitului exact în `/version`, iar migrarea
  rulează la startup.
- Uptime-ul programat compară SHA-ul din `main` cu backendul direct și proxy-ul
  frontend, semnalând automat un deploy rămas în urmă.
- Brevo/Resend au retry limitat pentru erori temporare și diagnostice mai precise
  pentru sender invalid, cheie respinsă, rate limit și domeniu neverificat.
- Configurație pregătită pentru Cloudflare Workers Free, fără Images/R2 sau alte
  servicii facturabile. Deploy-ul nu este activat automat.

## Costuri și limite

Nu a fost activat niciun serviciu plătit. Configurația păstrează Sentry,
analytics și OpenAI opționale/dezactivate. Excepțiile inevitabile sunt comisionul
Stripe numai când există o tranzacție și reînnoirea domeniului. Nivelurile free
Render, Supabase, GitHub, Brevo/PostHog/Sentry și Cloudflare au cote și nu oferă
SLA; acestea trebuie monitorizate.

Vercel Hobby nu este o destinație potrivită pentru utilizare comercială conform
limitărilor curente. Migrarea frontendului către Cloudflare Workers Free este
pregătită în cod, dar se face numai după ce workflow-ul Linux este verde și
proprietarul conectează contul/domeniul, fără card sau upgrade.

## Verificări externe rămase

1. Confirmă workflow-urile GitHub după push, în special build-ul Cloudflare pe
   Linux. `CRON_SECRET` este adăugat. Confirmă o singură dată în Render că
   Auto-Deploy afișează `After CI Checks Pass`; deploy hook-ul este doar opțional.
   Verificarea publică din 18 iulie a găsit backendul sănătos, dar rămas la
   commitul `bb5cfef`, deci ultimul `main` trebuie încă publicat.
2. Repară livrarea Brevo: sender/domeniu SPF-DKIM, cheia API și testele Admin
   pentru confirmare cont, resetare și suport către `contact@cealeg.shop`.
3. Rulează Stripe în test mode și apoi un test live controlat pentru Pro, Family,
   trei pachete CeCoins, Portal și webhook. Stripe percepe comision la încasare.
4. Rulează backup-ul GitHub și un restore într-o bază Supabase disposable, nu
   peste producție.
5. Testează pe Android și iPhone reale: cont nou, limbă, scanner, OCR, misiuni,
   checkout, resetare și ștergere cont.
6. Completează registrul DPA, owner-ul operațional și aprobarea textelor legale.

Până la închiderea acestor verificări, starea corectă este: **cod local validat,
pregătire de producție avansată, fără sign-off live final**.
