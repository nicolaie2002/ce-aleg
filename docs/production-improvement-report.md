# Raport de implementare - Production Improvement Plan

**Data evaluării:** 17 iulie 2026

**Plan evaluat:** `docs/production-improvement-plan.md`

**Ramură:** `main`

**Ultimul commit inclus în istoric:** `87cad23` (`Harden production reliability and critical flows`)

**Sursa adevărului:** repository-ul și worktree-ul local existente la data evaluării

## Verdict

**Aplicația nu primește încă semnătura de pregătire pentru producție.** Există progrese importante și verificări locale verzi, însă toate porțile din plan nu sunt trecute. Blocajele dovedite sunt:

1. acoperirea backend este sub ținta de 70%; baza măsurată anterior a fost 24,03%, iar măsurarea proaspătă din acest audit este 53,67%;
2. suita E2E în configurația CI are un eșec serios de contrast pe `/pricing` în viewport mobil;
3. backupul și restore-ul sunt implementate, dar nu există dovadă în repository pentru un backup programat reușit și un restore complet într-o bază de test izolată;
4. testarea live pentru Stripe, email, Sentry, Redis și mediile Vercel/Render nu poate fi demonstrată doar din cod;
5. refactorizarea Flask este începută, dar handler-ele și serviciile nu sunt încă extrase din `backend/app.py`;
6. validarea, i18n, TypeScript strict și documentația cerută de plan sunt numai parțial închise;
7. raportul independent al celor trei revieweri și aprobarea legală nu există ca dovezi finale.

Acest document este un raport de progres și de diferențe față de plan. Nu este un certificat de go-live.

## Legendă

| Stare | Semnificație |
|---|---|
| **Implementat în cod** | Comportamentul și testele locale relevante există; poate rămâne o verificare externă. |
| **Parțial** | Există o implementare utilă, dar poarta din plan nu este îndeplinită integral. |
| **Neîndeplinit** | Livrabilul sau dovada cerută lipsește. |
| **Verificare externă** | Codul local nu poate demonstra starea serviciului, a secretelor, a DNS-ului sau a unui flux live. |
| **Blocant** | Împiedică semnătura de pregătire pentru producție. |

## Dovezi de verificare

La data raportului au fost rulate următoarele verificări pe worktree-ul curent:

| Verificare | Rezultat |
|---|---|
| `scripts/verify-project.ps1` | **Trecut**: sintaxă și lint backend, scanare locală de secrete, audit 39 rute frontend, ESLint, TypeScript, Jest și build Next.js. |
| Backend pytest | **244 teste trecute**; 53,67% coverage pentru `backend/app.py`; pragul CI curent este numai 20%. |
| Frontend Jest | **7 teste trecute**, 3 suite; raportul arată 100% doar pentru `app/error.tsx` și `LocaleProvider.js`, nu pentru întreaga interfață. |
| Next.js production build | **Trecut**; 66 pagini generate, inclusiv rutele publice, cont, catalog, admin, scanare, misiuni și ajutor. |
| Playwright full-stack în configurație CI | **20 trecute, 7 sărite intenționat, 1 eșuat**. Eșecul este `@a11y /pricing` pe mobil: contrast 2,93:1 pentru controlul „Lunar”, față de 4,5:1 cerut. |
| Fluxuri E2E desktop | Înregistrare/verificare/login, scanare/coș, căutare/favorite/alternative, Pro, referral, contribuție/admin, ștergere cont și offline au trecut în ultima rulare CI locală. |
| Backup/restore shell | Sintaxa este verificată de CI și există teste dedicate, dar nu s-a executat în acest audit un restore extern într-un proiect Supabase de test. |

### Acoperire backend: 24% față de ținta de 70%

Planul cere `--cov-fail-under=70`. Baza consemnată la începutul lucrărilor recente a fost **24,03%**. În timpul redactării raportului au fost adăugate teste concurente, iar ultima rerulare a măsurat **53,67%** și 244 teste trecute. Progresul este real, dar ținta nu este atinsă. `.github/workflows/test-backend.yml` și `scripts/verify-project.ps1` folosesc încă `--cov-fail-under=20`, deci CI nu aplică poarta de 70% din plan.

## Matricea planului

### Valul 1 - Fundație

| Inițiativă | Stare | Dovezi | Ce mai lipsește / verificare externă |
|---|---|---|---|
| 1.1 Jest + React Testing Library | **Parțial** | `frontend/jest.config.js`, `jest.setup.js`, trei suite și 7 teste; rularea locală este verde. | Coverage-ul de 100% este limitat la două fișiere colectate. Nu demonstrează ținta de peste 60% pentru utilitare și componentele importante din plan. |
| 1.2 pytest backend | **Parțial, blocant** | `backend/tests/`, 244 teste trecute, Postgres 17 configurat în workflow. | Coverage curent 53,67%, față de 70%; pragul CI este 20%. Sunt necesare teste suplimentare pentru rutele și ramurile rămase. |
| 1.3 Validarea inputurilor | **Parțial** | `backend/validation.py` conține validatori reutilizabili și teste; `backend/app.py` limitează corpul cererii și JSON-ul malformat și are validări istorice pe rute. | Modulul comun nu este conectat direct la handler-ele din `app.py`; nu este demonstrat că toate endpoint-urile publice întorc aceeași structură 400. Implementarea este custom, nu Marshmallow, ceea ce este acceptabil numai dacă acoperirea contractului este demonstrată. |
| 1.4 OpenAPI 3.1 + Swagger | **Parțial** | `/api/openapi.json` și `/api/docs` există; `backend/api_docs.py` și testele verifică un contract OpenAPI 3.1. | Endpoint-ul runtime generează în principal rute și răspunsuri generice și nu folosește contractul bogat din `api_docs.py`. Schemele de payload și răspuns nu sunt dovedite pentru toate endpoint-urile. |
| 1.5 Error boundaries + Sentry frontend | **Implementat în cod; verificare externă** | `app/error.tsx`, `app/global-error.tsx`, instrumentarea Sentry și teste Jest verzi. | Trebuie confirmat într-un proiect Sentry gratuit că o eroare din producție ajunge, este anonimizată și are sourcemap corect. Sentry poate rămâne dezactivat pentru cost zero. |
| 1.6 Sentry backend | **Implementat în cod; verificare externă** | Inițializare condiționată de `SENTRY_DSN`, scrub pentru body/cookies/query/headers, `send_default_pii=False`. | Nu există dovadă locală că proiectul extern și alertele sunt active. Fără DSN, aplicația continuă prin logging, fără cost. |
| 1.7 Accesibilitate | **Parțial, blocant** | ESLint a11y trece; axe rulează pe desktop și mobil pentru paginile publice principale. | Ultimul E2E CI a eșuat pe `/pricing` mobil din cauza contrastului 2,93:1. Sunt necesare corecția și rerularea completă; auditul manual rămâne necesar. |

### Valul 2 - Infrastructură

| Inițiativă | Stare | Dovezi | Ce mai lipsește / verificare externă |
|---|---|---|---|
| 2.1 Redis/Upstash | **Parțial; verificare externă** | Dependența `redis` și `REDIS_URL` există. `render.yaml` nu creează un serviciu Redis și folosește Render `plan: free`. | Nu există dovadă că o instanță Redis gratuită este configurată. Fallback-ul local permite funcționarea fără cost, dar nu oferă stare distribuită. |
| 2.2 Rate limiting distribuit | **Parțial** | Implementare custom Redis cu chei pe scope/identitate și fallback în memorie; răspuns 429 și teste de securitate. | Nu este demonstrat comportamentul între mai mulți workeri. Pe configurația Render actuală există un singur worker; fallback-ul nu este distribuit. |
| 2.3 Cache distribuit | **Parțial** | Cache Redis opțional, metrici hit/miss/write/error și cache-uri locale cu limite/TTL. | Nu este demonstrată supraviețuirea la restart și nici ținta de peste 80% hit rate. Fără Redis, cache-ul se pierde la restart. |
| 2.4 Stripe Billing Portal | **Implementat în cod; verificare externă** | `/billing/portal`, verificarea customer-ului, tratarea customer-ului expirat și teste de fail-closed. | Trebuie testat cu un customer Stripe real: deschidere portal, schimbare/anulare și sincronizare webhook. |
| 2.5 Webhook Stripe idempotent | **Implementat și testat local; verificare externă** | `StripeWebhookEvent`, deduplicare după event ID, statusuri și alertare; testul de livrare duplicată trece. Checkout-ul folosește chei idempotente scoped. | Este necesar un eveniment semnat în mediul Stripe configurat și verificarea rezultatului în baza live, fără a cumpăra un abonament software suplimentar. Stripe are comision numai la tranzacții. |
| 2.6 Logging JSON | **Implementat în cod; verificare externă** | Formatter JSON cu timestamp, level, logger, message, request ID, metodă și cale; `LOG_FORMAT=json` în Blueprint Render. | Trebuie confirmat în logurile Render că toate procesele emit forma așteptată și că datele sensibile nu apar. |

### Valul 3 - Experiența utilizatorului

| Inițiativă | Stare | Dovezi | Ce mai lipsește / verificare externă |
|---|---|---|---|
| 3.1 i18n RO/EN | **Parțial** | `LocaleProvider`, texte `pick(ro, en)`, localizare pentru catalog și teste de limbă; ruta `/help` în engleză trece E2E. | Nu s-a făcut migrarea la `next-intl`; există încă mecanism DOM de traducere automată și texte hardcodate. Cerința „toate paginile RO/EN, fără texte hardcodate” nu este demonstrată. |
| 3.2 PWA | **Parțial** | Manifest, `public/sw.js`, înregistrare service worker și pagină offline; testul offline desktop și mobil a trecut în configurația CI. | Lipsesc dovezi Lighthouse PWA >90, install prompt și testare pe dispozitive reale/iOS. Implementarea custom evită o dependență externă și nu costă. |
| 3.3 PostHog analytics | **Înlocuit parțial, gratuit** | Există analytics opțional GA/Meta/TikTok, încărcat numai după consimțământ; evenimentele server sunt allowlistate. | PostHog și feature flags nu sunt implementate. Pentru cost zero, toate ID-urile pot rămâne goale; nu trebuie activat niciun plan plătit. Dacă analytics este activat, dashboard-ul și consimțământul trebuie verificate extern. |
| 3.4 Asistent vizual AI | **Implementat cu fallback gratuit; verificare externă pentru cloud** | Abstracție de provider, validare strictă, provider local/disabled, teste fără rețea; OCR pe telefon folosește `tesseract.js`. `ENABLE_OPENAI_VISION` este fals implicit. | OpenAI este un serviciu cu cost și trebuie să rămână dezactivat pentru politica zero-cost. În producție este recomandat `VISION_PROVIDER=local` sau `disabled`; providerul cloud nu este necesar pentru lansarea gratuită. |
| 3.5 Consimțământ granular | **Implementat în cod; verificare legală externă** | Banner cu categorii, update pentru provideri, `ConsentRecord`, `/privacy/consent`, `/account/consent` și teste. | Trebuie verificat manual că niciun tracker nu pornește înainte de acord și că textul/temeiul juridic sunt aprobate. |

### Valul 4 - Operațiuni

| Inițiativă | Stare | Dovezi | Ce mai lipsește / verificare externă |
|---|---|---|---|
| 4.1 Backup Supabase automat | **Implementat în worktree; verificare externă, blocant** | `.github/workflows/backup.yml`, `scripts/backup-supabase.sh`, `scripts/restore-supabase.sh`, export Storage, manifest SHA-256, criptare AES-256 și 30 zile retenție artifact; teste de siguranță restore. | Fișierele sunt încă în worktree și trebuie publicate. Lipsesc dovada unui workflow reușit, artifactul criptat și un restore drill într-o bază disposable. Nu se declară recuperabilitate doar din existența scriptului. |
| 4.2 Calitatea catalogului | **Implementat în cod; poartă parțială** | `catalog_quality.py`, endpoint admin, health score, lipsuri, valori invalide, duplicate și exemple; teste de raport. | Nu există benchmark pe catalogul real care să demonstreze raport sub 5 secunde. Drill-down-ul admin trebuie verificat în producție. |
| 4.3 Alertare configurabilă | **Implementat în cod; verificare externă** | Rutare către Sentry, webhook și email, deduplicare/throttling și alerte pentru Stripe/catalog/rapoarte. | Nu există dovadă de alertă primită și escaladare on-call. Toate canalele pot rămâne neconfigurate pentru cost zero, cu logurile drept fallback. |
| 4.4 Runbook-uri operaționale | **Implementat în mare parte** | Runbook-uri pentru incident, restore, Stripe webhook, catalog, rate limit, deploy, rollback, email, securitate și outage Supabase; index în `docs/operations.md`. | Proprietarii, datele de contact, rotația on-call și rezultatele exercițiilor trebuie completate extern. |

### Valul 5 - Legal și conformitate

| Inițiativă | Stare | Dovezi | Ce mai lipsește / verificare externă |
|---|---|---|---|
| 5.1 Export date - Art. 20 | **Implementat și testat local** | `/account/export` și `/account/data-export`; autentificare și export testate. | Test manual cu un cont voluminos și revizuire juridică a câmpurilor exportate. |
| 5.2 Acces date - Art. 15 | **Implementat și testat local** | `/account/data`, sumar structurat și link de export. | Confirmare juridică privind completitudinea și termenii răspunsului. |
| 5.3 Restricționarea prelucrării - Art. 18 | **Implementat și testat local** | Câmpuri în model, `/account/restriction`, middleware de blocare și teste activate/dezactivate. | Revizuire juridică a operațiunilor care trebuie permise pe durata restricției. |
| 5.4 Registru DPA | **Parțial, blocant legal** | `docs/legal/dpa-register.md` inventariază furnizorii și datele. | Documentul conține explicit numeroase câmpuri `DE COMPLETAT`: entități, DPA, regiuni, transferuri, retenție și owner. Nu există aprobare juridică. |
| 5.5 Jurnal consimțământ server-side | **Implementat și testat local** | Model `ConsentRecord`, endpoint și teste de persistență/validare. | Verificarea politicii de retenție și a versiunilor textelor de consimțământ. |
| 5.6 Retenție și cleanup | **Implementat în cod; verificare externă** | Politici configurabile, dry-run/apply, teste și cron `/api/cron/maintenance` protejat cu `CRON_SECRET`. | Trebuie confirmată o execuție programată reușită în Vercel/Render și inspectate numerele șterse înainte de aplicare pe producție. |

### Valul 6 - Calitatea codului

| Inițiativă | Stare | Dovezi | Ce mai lipsește / verificare externă |
|---|---|---|---|
| 6.1 Flask factory + Blueprints | **Parțial** | `app_factory.py`, config runtime, 13 Blueprints în `backend/routes/`, 104 decoratori `@route`, zero `@app.route`; smoke test și teste de registry trec. | Blueprints fac rutarea, dar modulele de domeniu declară în principal obiectele Blueprint. Handler-ele și serviciile rămân în `backend/app.py` (aprox. 15.000 linii). Extragerea handler/service/model din plan nu este terminată. |
| 6.2 Stripe Python 11 -> 15 | **Parțial, abatere justificată** | `backend/requirements.txt` fixează `stripe>=14.4,<15`; codul are Checkout, Portal, webhook și idempotency testate local. | Planul a cerut v15, dar versiunea v15 nu era disponibilă/rezolvabilă în indexul oficial folosit la implementare. Pin-ul 14.4 a fost ales pentru build reproductibil și suport curent, fără a inventa o versiune inexistentă. Upgrade-ul la 15 se reia numai după publicare/compatibilitate și testare Stripe completă. |
| 6.3 TypeScript strict | **Parțial** | `strict: true`, typecheck verde. | `frontend/app` are aproximativ 82 fișiere JS/JSX și numai 2 TS/TSX; `checkJs` nu este activ și include-ul vizează TS. Strict mode nu acoperă majoritatea aplicației. |
| 6.4 Playwright E2E | **Parțial, blocant** | Scenarii pentru toate cele 8 fluxuri critice; ultima rulare CI locală: 20 trecute. | Un test a11y mobil eșuează, iar 7 scenarii mutabile sunt sărite intenționat pe mobil. Poarta „toate E2E trec” nu este îndeplinită. |
| 6.5 Porți CI | **Parțial; verificare externă** | Workflows pentru frontend, backend, E2E, Trivy secrets/vulnerabilities, imagini Docker și backup; verificarea locală principală trece. | Pragul coverage este 20, nu 70; E2E are un eșec; nu există dovadă în acest raport că ultimul workflow privat GitHub este verde. Deploy-ul staging automat din plan nu este implementat ca poartă CI. |

### Valul 7 - Review final

| Inițiativă | Stare | Dovezi | Ce mai lipsește / verificare externă |
|---|---|---|---|
| 7.1 Review independent cu 3 agenți | **Neîndeplinit** | Nu există în repository trei rapoarte PASS/FAIL pentru arhitectură, securitate și teste. | Review-uri independente, rezolvarea blockerelor și păstrarea rapoartelor. |
| 7.2 Regresie și performanță | **Neîndeplinit, blocant** | Unit/lint/typecheck/build sunt verzi, iar majoritatea E2E trec. | E2E nu este 100% verde; lipsesc Lighthouse PWA/accessibility/performance, bundle gzip, API p95, Redis multi-worker, cache hit >80%, restore drill și verificări live. |
| 7.3 Documentație finală | **Parțial** | Există README, checklist go-live, audit securitate, handoff, environment, operațiuni și runbook-uri; prezentul raport este adăugat. | `docs/architecture.md` și `docs/api.md` lipsesc. Unele documente conțin afirmații istorice/checklist-uri care trebuie reconfirmate cu starea live. |
| 7.4 Sign-off producție | **Neîndeplinit** | Nu există un set complet de dovezi care să treacă toate criteriile planului. | Se acordă numai după închiderea tuturor blockerelor și verificarea mediului live. |

## Substituții pentru politica „numai gratuit”

Nicio modificare evaluată aici nu trebuie să activeze automat un abonament plătit. Strategia gratuită este:

| Cerință din plan | Variantă fără cost nou | Limită acceptată / acțiune |
|---|---|---|
| Redis/Upstash | `REDIS_URL` opțional; fallback în memorie | Nu este distribuit și se pierde la restart. Nu se activează un plan Redis plătit fără acord explicit. |
| Sentry | SDK condiționat de DSN; altfel logging JSON | Poate fi folosit numai în limita unui plan gratuit sau lăsat dezactivat. |
| PostHog | Nu este instalat; analytics existente pot rămâne complet dezactivate | Fără dashboard/feature flags PostHog. ID-urile goale înseamnă zero tracking și zero cost. |
| OpenAI Vision | `ENABLE_OPENAI_VISION=false`; Tesseract.js și provider local/disabled | OpenAI nu este gratuit și trebuie să rămână oprit. `VISION_PROVIDER` trebuie setat `local` sau `disabled` pentru o configurație explicit zero-cost. |
| Backup S3/GCS | GitHub Actions + artifact privat criptat, retenție 30 zile | Depinde de cota gratuită GitHub și trebuie monitorizată; restore drill rămâne obligatoriu. |
| PWA | Manifest și service worker propriu | Fără serviciu extern sau abonament. |
| Alerte | Loguri Render; webhook/email/Sentry opționale | Lipsesc alertele proactive dacă toate canalele sunt oprite. |
| Hosting | `render.yaml` cere `plan: free`; se păstrează nivelurile gratuite existente | Cold start, cote și lipsa SLA rămân riscuri operaționale. |
| Stripe | Fără abonament software suplimentar în cod | Stripe percepe comision numai când există o tranzacție; acest comision comercial nu poate fi eliminat prin cod. |

## Verificări externe obligatorii

Aceste puncte nu pot fi închise doar prin modificări locale:

1. Publicarea worktree-ului curent și confirmarea tuturor joburilor GitHub Actions.
2. Primul backup programat reușit, validarea hash-ului și restore complet într-o bază disposable, niciodată direct peste producție.
3. Test Stripe controlat pentru Pro, Family, cele trei pachete CeCoins, Portal și webhook semnat/idempotent.
4. Testarea emailurilor de verificare, resetare, suport și notificări, inclusiv SPF/DKIM și livrare la `contact@cealeg.shop`.
5. Confirmarea că Vercel și Render rulează exact commit-ul aprobat și că `/health`, `/readiness` și `/version` sunt coerente.
6. Confirmarea Redis multi-worker numai dacă se configurează o instanță gratuită; altfel acceptarea explicită a fallback-ului single-worker.
7. Test alertă Sentry/webhook/email sau decizia explicită de a funcționa numai cu loguri.
8. Completarea registrului DPA, aprobarea politicilor și desemnarea responsabilului/on-call.
9. Test manual pe telefon real pentru scanare, produs negăsit, OCR, misiuni, checkout, limbă și ștergere cont.

## Ordinea recomandată pentru închidere

1. Repară contrastul `/pricing` mobil și rulează din nou întreaga suită E2E.
2. Crește coverage backend la minimum 70% și schimbă poarta CI de la 20 la 70.
3. Conectează validarea comună și contractul OpenAPI bogat la rutele runtime.
4. Continuă extragerea handler-elor și serviciilor din `backend/app.py` în Blueprints/modules de domeniu.
5. Execută backupul programat și restore drill-ul izolat.
6. Închide i18n complet, migrarea TypeScript și testarea a11y/performance pe toate paginile critice.
7. Rulează verificările live Stripe/email/deploy și completează documentele legale.
8. Obține cele trei review-uri independente și abia apoi reevaluează sign-off-ul.

## Concluzie

Repository-ul este mai bine protejat, testat și operabil decât la începutul planului, iar strategia poate rămâne fără abonamente noi plătite. Totuși, dovezile actuale contrazic o declarație de „gata de producție”: coverage-ul este sub țintă, E2E nu este complet verde, restore-ul nu este demonstrat, iar mai multe verificări live și juridice lipsesc. Starea corectă este **îmbunătățire în curs, fără sign-off de producție**.
