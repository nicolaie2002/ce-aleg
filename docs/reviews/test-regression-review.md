# Revizie independentă: teste și risc de regresie

> Snapshot istoric pentru `7be9c7c` din 17 iulie 2026. Raportul curent este
> `docs/production-improvement-report.md`. Erorile TypeScript, rutele dinamice și
> locatorul E2E descrise mai jos au fost reparate; cifrele și verdictul de mai jos
> nu trebuie folosite pentru release-ul curent.

**Data:** 17 iulie 2026  
**Repository:** `D:\proiecte\ce_aleg`  
**Bază:** `HEAD 7be9c7c` plus modificările necomise observate în timpul reviziei  
**Scope:** `docs/production-improvement-plan.md`, testele, build-ul și workflow-urile curente

## Verdict

**FAIL pentru production sign-off în starea curentă.** Backendul și testele Jest configurate trec, însă poarta frontend TypeScript și suita E2E curentă eșuează. Verificările externe pentru GitHub Actions, Stripe, email, Supabase/backup și Redis real nu au fost demonstrate și nu sunt declarate PASS.

| Zonă | Verdict | Dovadă |
|---|---|---|
| Backend | **PASS local** | `331 passed`, fără `DeprecationWarning`, acoperire totală `73,77%` |
| Frontend lint | **PASS local** | `npm run lint` a ieșit cu cod 0 și zero warnings |
| Frontend typecheck | **FAIL** | `npm run typecheck` a produs `2445` diagnostice TypeScript după activarea `checkJs` |
| Frontend Jest | **PASS pe scope-ul configurat** | `8/8` suite, `55/55` teste; acoperire `95,83%` statements și `88,55%` branches |
| Frontend build | **Nedovedit pe configurația curentă** | Build-ul cu 66 de pagini a trecut înainte de modificarea concurentă a `tsconfig.json`; poarta curentă se oprește la typecheck |
| E2E | **FAIL** | Din 32 teste: `17 passed`, `3 failed`, `7 skipped`, `5 did not run` |
| Acoperire backend | **PASS** | Pragul de 70% este aplicat și rezultatul curent este `73,77%` |
| Acoperire frontend | **PASS numeric / FAIL ca acoperire integrală** | Pragul de 60% trece, dar Jest colectează acoperire doar pentru 11 fișiere; cele 39 de pagini nu intră în metrică |
| CI configurat | **PASS static** | Workflow-ul principal leagă frontend, backend, E2E, Trivy și smoke-testele containerelor |
| CI executat pe starea curentă | **FAIL / nedovedit extern** | Simularea locală eșuează la typecheck și E2E; nu a fost verificat un run GitHub Actions verde pentru acest snapshot |
| Performanță API locală | **PASS local izolat** | p95: health `0,314 ms`, produse `2,025 ms`, statistici `0,404 ms`, toate sub 500 ms |

## Dovezi executate

### Backend

Comandă:

```powershell
cd backend
venv\Scripts\python.exe -m pytest tests -W error::DeprecationWarning `
  --cov=app --cov=routes --cov-report=term --cov-fail-under=70 -q
```

Rezultat: `331 passed in 19.35s`; `TOTAL 6484 statements`, `1701 missed`, `73.77%`. Este o dovadă bună pentru logica locală și integrarea Flask. Rularea independentă a folosit Python 3.14 și SQLite în memorie; workflow-ul GitHub este configurat pentru Python 3.12 și PostgreSQL 17, deci compatibilitatea acelui mediu rămâne dependentă de CI.

Comandă benchmark:

```powershell
python scripts/benchmark-backend.py --iterations 100 --threshold-ms 500
```

Rezultat: toate cele trei endpoint-uri reprezentative au trecut. Benchmark-ul este intenționat izolat, cu SQLite în memorie; nu demonstrează latența Render, Supabase, cold start-ul sau traficul concurent din producție.

### Frontend

Comenzi:

```powershell
cd frontend
npm run lint
npm run typecheck
npm run test:ci -- --runInBand --passWithNoTests
npm run build
```

Rezultate observate:

- lint: PASS;
- typecheck: FAIL cu 2445 erori, inclusiv `app/admin/page.js`, paginile de suport/termeni, utilitarele și `proxy.js`;
- Jest, rulat înaintea schimbării concurente din `tsconfig.json`: `8/8` suite și `55/55` teste PASS;
- build-ul anterior: 66 de pagini generate, PASS; nu poate fi atribuit configurației stricte curente deoarece lanțul actual se oprește la typecheck.

Configurația `frontend/jest.config.js` aplică pragul de 60%, dar `collectCoverageFrom` include doar 11 fișiere: error boundary, șase componente și patru utilitare. Cifra de 95,83% nu reprezintă întregul frontend și nu trebuie prezentată ca atare.

### E2E și accesibilitate

Comandă:

```powershell
cd frontend
$env:PLAYWRIGHT_FULL_STACK = "true"
$env:CI = "true"
npm run test:e2e
```

Rezultat curent: `17 passed`, `3 failed`, `7 skipped`, `5 did not run`.

Defecte demonstrate:

1. Pagina `/catalog-romania/magazine/lidl` răspunde cu interfața 404 pe desktop și mobil. `frontend/app/catalog-romania/magazine/[slug]/page.js` citește `params` sincron, deși în Next.js 16 acesta este asincron. Același tipar apare și la paginile dinamice `categorii`, `produse` și `alternative`, deci riscul este mai larg decât Lidl.
2. Scenariul „scan barcode -> add to cart” ajunge în coș și găsește produsul, dar aserțiunea `getByText("Iaurt natural E2E")` este ambiguă după introducerea textului `sr-only` pentru imagine. Acesta este un defect de locator E2E; trebuie folosit un rol sau un locator unic.
3. Cele șapte scenarii care modifică date sunt omise intenționat pe proiectul mobil. Public navigation și auditul axe rulează pe mobil, dar înregistrarea, scanarea, favoritele, planul Pro, invitația, aprobarea admin și ștergerea contului nu sunt validate cap-coadă în viewport mobil.

Un run anterior, înaintea adăugării celor două teste i18n, a avut `21 passed` și `7 skipped`. Nu înlocuiește verdictul run-ului curent și arată de ce noul test pentru catalog a fost util.

## CI

Au fost consultate:

- `.github/workflows/ci.yml`;
- `.github/workflows/test-backend.yml`;
- `.github/workflows/test-frontend.yml`;
- `.github/workflows/test-e2e.yml`;
- `scripts/verify-project.ps1`.

Configurația leagă corect lint, typecheck, Jest, build, a11y, pytest cu prag 70%, E2E full-stack, scanare Trivy și build/smoke Docker. Totuși:

- `actionlint` nu este instalat local, deci sintaxa semantică GitHub Actions nu a fost validată cu acel instrument;
- nu a fost demonstrat un run GitHub Actions verde pentru snapshot-ul curent;
- starea locală curentă ar face `frontend-quality` și `full-stack-e2e` să eșueze;
- branch protection și obligativitatea check-urilor înainte de merge sunt setări externe neverificate.

## Riscuri rămase

- Emailul real nu este trimis în E2E: `EMAIL_SMTP_HOST` este gol, iar verificarea contului folosește linkul local de test.
- Stripe este testat cu stub-uri și chei locale fictive; Checkout, Portal și webhook-urile reale nu sunt demonstrate.
- Redis este testat prin fake client, inclusiv concurența/fallback-ul; comportamentul unui serviciu Redis real și rata de cache de peste 80% nu sunt demonstrate.
- Backup/restore are teste și verificări de script, dar restaurarea într-o bază Supabase temporară și verificarea artefactului criptat sunt externe.
- Serviciile Open Food Facts/Open Prices, Supabase Storage și integrarea catalogului extern sunt dezactivate în E2E.
- Fișierele Alembic (`migration.py`, `migrations/` și dependența nouă) au apărut concurent după rularea celor 331 de teste. Compilarea Python trece, dar nu a fost demonstrat un ciclu `upgrade -> current -> downgrade` pe o bază temporară PostgreSQL și nici rularea `release` pe o copie de date; migrarea nu primește PASS din această revizie.
- Auditul axe acoperă doar `/`, `/login`, `/help` și `/pricing`; nu dovedește accesibilitatea scannerului, dashboard-ului, adminului și fluxurilor modale.
- Nu există dovadă de browser real iOS/Safari sau telefon fizic; proiectele Playwright folosesc Chromium desktop și emulare Pixel 7.
- Backendul rămâne concentrat în `app.py`; procentul ridicat al modulelor `routes` include în principal registrul/delegarea, nu separarea completă a logicii.

## Blockere reale

1. **Typecheck frontend:** repararea celor 2445 de diagnostice sau restrângerea incrementală, explicită și justificată a `checkJs`; în forma actuală CI nu poate fi verde.
2. **Rutele dinamice din catalog:** tratarea asincronă corectă a `params` în Next.js 16 și teste pentru toate cele patru familii de slug-uri.
3. **E2E coș:** înlocuirea locatorului ambiguu și rerularea completă până la `0 failed` și `0 did not run`.
4. **CI curent:** obținerea și păstrarea unui run GitHub Actions verde pe commitul care va fi lansat.
5. **Semnare externă:** email tranzacțional real, Stripe test/live, restore Supabase și serviciile de producție nu pot primi PASS din această revizie până când sunt executate în mediile lor.

Până la rezolvarea primelor trei blockere și rerularea tuturor porților, criteriul din plan „Regression testing 100% pass” nu este îndeplinit.
