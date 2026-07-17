# Arhitectura Ce aleg?

Documentul descrie arhitectura care exista in repository la 17 iulie 2026.
El trebuie actualizat cand se schimba o limita de sistem, un furnizor sau un
flux care proceseaza date personale ori plati.

## Obiective

- scanarea si cautarea produselor alimentare;
- analiza nutritionala si recomandarea de alternative compatibile;
- cresterea catalogului romanesc prin importuri si contributii verificate;
- conturi Free, Pro si Family, CeCoins, misiuni si profiluri de familie;
- operare sigura cu servicii gratuite si degradare controlata cand un serviciu
  extern nu raspunde.

## Componente

```text
Browser / PWA
    |
    | HTTPS, cookie HttpOnly, JSON / multipart
    v
Vercel - Next.js frontend
    |
    | /api/backend/* -> proxy same-origin
    v
Render - Flask API, Gunicorn (1 worker, 4 threads)
    |-- Supabase Postgres        date relationale
    |-- Supabase Storage         imagini produs si contributii
    |-- Open Food Facts          catalog extern, optional
    |-- Open Prices              observatii de pret, optional
    |-- Stripe                   Checkout, Portal si webhook
    |-- Brevo/Resend/SMTP        email tranzactional
    `-- Redis                    cache/rate limit optional
```

Frontendul este aplicatia Next.js din `frontend/`. Backendul este aplicatia
Flask din `backend/`. Domeniul public canonic este `https://www.cealeg.shop`.
Frontendul foloseste proxy-ul same-origin definit in `frontend/next.config.mjs`,
astfel incat browserul nu trebuie sa cunoasca URL-ul Render pentru operatiile
normale.

## Frontend

- Next.js App Router, pagini publice, cont, scanner, catalog, misiuni si admin.
- `LocaleProvider` pastreaza limba RO/EN; continutul public din catalog are
  traduceri si fallback controlat.
- service worker, manifest si pagina offline ofera comportament PWA fara un
  serviciu extern.
- OCR-ul de pe telefon foloseste Tesseract.js local in browser.
- CSP, HSTS, `frame-ancestors`, `nosniff`, Permissions Policy si redirecturile
  catre domeniul canonic sunt definite in configuratia Next.js.
- analytics si Sentry sunt optionale si nu pornesc fara configurare/consimtamant.

## Backend

`backend/app_factory.py` construieste aplicatia si aplica `RuntimeConfig`.
`backend/routes/registry.py` repartizeaza cele 104 rute intre 13 Blueprints:
system, auth, products, cart, favorites, history, submissions, billing,
gamification, family, admin, feedback si AI.

Handler-ele si o parte importanta din logica de domeniu se afla inca in
`backend/app.py`. Registry-ul Blueprint separa suprafata HTTP, dar extragerea
serviciilor din fisierul monolitic ramane o imbunatatire de mentenabilitate, nu
o conditie pentru functionarea fluxurilor curente.

Middleware-ul comun aplica:

- request ID si logging structurat;
- limita globala si limite specifice endpoint-urilor;
- limita pentru corpuri JSON si respingerea JSON-ului malformat;
- verificarea `Origin` si `Sec-Fetch-Site` pentru operatii mutabile;
- autentificarea, autorizarea admin si izolarea resurselor intre utilizatori;
- blocarea prelucrarii optionale pentru conturile restrictionate.

## Date

Modelele SQLAlchemy principale sunt:

| Model | Rol |
|---|---|
| `User` | identitate, verificare email, rol, CeCoins si preferinte GDPR |
| `Product` | catalog local si date nutritionale |
| `ProductSubmission` | produse propuse de comunitate si starea verificarii |
| `ScanHistory`, `Favorite`, `CartItem` | activitatea privata a utilizatorului |
| `PriceObservation`, `SearchEvent` | preturi raportate si lipsuri in catalog |
| `Subscription` | starea Free/Pro/Family sincronizata cu Stripe |
| `FamilyProfile` | profiluri nutritionale Family |
| `UsageEvent` | misiuni, recompense si evenimente idempotente |
| `StripeWebhookEvent` | procesarea idempotenta a webhook-urilor |
| `ConsentRecord` | dovada consimtamantului pe versiune si categorii |

Postgres este sursa autoritara in productie. SQLite este doar fallback local si
pentru teste. Imaginile sunt salvate in Supabase Storage cand este configurat;
fisierele locale nu trebuie tratate ca persistente pe Render.

## Autentificare si securitate

Autentificarea foloseste cookie-ul semnat `cealeg_session`, `HttpOnly`,
`SameSite=Lax` si `Secure` in productie. Tokenul contine ID-ul utilizatorului si
versiunea de autentificare; schimbarea parolei sau stergerea contului invalideaza
sesiunile vechi.

Secretele sunt variabile de mediu si nu se includ in repository. CORS accepta
doar originile frontend configurate. Endpoint-urile admin verifica rolul pe
server. Uploadurile au limite de dimensiune, tip si continut, iar imaginile sunt
normalizate inainte de procesare.

## Catalog si recomandari

Ordinea surselor este local-first:

1. catalogul local verificat;
2. Open Food Facts, numai daca integrarea externa este activa;
3. contributia ghidata pentru un produs negasit;
4. verificare si corectie din admin.

Alternativele sunt filtrate dupa familie de produs si compatibilitate, apoi
ordonate prin scor nutritional. Daca Open Food Facts este indisponibil, API-ul
poate returna alternative locale si marcheaza explicit sursa
`local-fallback`. Open Prices este optional si nu poate bloca analiza produsului.

## Plati

Browserul cere o sesiune Checkout sau Portal de la backend. Backendul valideaza
planul/pachetul si foloseste ID-urile de pret configurate, fara a accepta sume
arbitrare din client. Webhook-ul Stripe este sursa autoritara pentru activarea
planurilor si creditarea CeCoins. ID-ul evenimentului si cheile de idempotenta
previn aplicarea dubla.

## Email si notificari

Emailul tranzactional trece printr-un adaptor pentru Brevo, Resend sau SMTP.
Adresa de raspuns si destinatia suportului sunt `contact@cealeg.shop` cand
mediul de productie este configurat corect. Esecul providerului este raportat
fara a marca fals mesajul drept trimis; logurile si diagnosticul admin raman
disponibile.

## Joburi si recuperare

Endpoint-ul `/internal/cron/maintenance` este protejat cu `CRON_SECRET` si poate
rula digestul de misiuni, retentia si verificari de catalog. Operatiile
destructive au mod dry-run unde este relevant.

Backupul Postgres si Storage este implementat prin GitHub Actions si scripturi
shell. Arhiva are manifest SHA-256 si poate fi criptata. Restore-ul refuza
implicit tintele care seamana cu productia si trebuie executat mai intai intr-un
proiect Supabase disposable. Procedura completa este in
`docs/runbooks/database-restore.md`.

## Profil exclusiv gratuit

| Componenta | Configuratie fara cost nou | Degradare acceptata |
|---|---|---|
| AI vizual cloud | `ENABLE_OPENAI_VISION=false`, `VISION_PROVIDER=local` | scanner prin cod de bare si OCR local |
| Redis | `REDIS_URL` gol | cache si rate limit in memoria unui singur worker |
| Sentry/analytics | DSN/ID-uri goale | logging JSON, fara dashboard extern |
| Open Food Facts/Open Prices | API-uri publice, kill switch disponibil | catalog local si contributii |
| Hosting | nivelurile gratuite existente | cold start, cote si fara SLA |
| Backup | GitHub Actions si artifact criptat | limitat de cota gratuita GitHub |

Stripe nu necesita un abonament software nou, dar percepe comision la fiecare
incasare. Domeniul are costul normal de reinnoire. Vercel Hobby poate avea
restrictii pentru folosirea comerciala; acestea trebuie verificate de
proprietar in termenii curenti ai furnizorului.

## Observabilitate si operare

- `/health`: procesul Flask raspunde;
- `/readiness`: configuratia si dependintele necesare lansarii;
- `/version`: commitul si versiunea publicata;
- `/admin/monitoring`: stare operationala agregata pentru admin;
- loguri JSON cu request ID in productie;
- runbook-uri in `docs/runbooks/` si index in `docs/operations.md`.

Un raspuns `200` de la `/health` nu dovedeste singur ca platile, emailul sau
restore-ul functioneaza. Semnatura de productie necesita toate dovezile din
`docs/production-improvement-report.md` si `docs/go-live-checklist.md`.
