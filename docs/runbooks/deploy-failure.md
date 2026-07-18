# Runbook: deploy esuat

## Scop

Foloseste procedura cand un build Vercel, un deploy Render sau verificarea imediat
dupa publicare esueaza. Obiectivul este sa pastrezi ultima versiune buna disponibila,
sa identifici cauza pe baza commit-ului si sa eviti repetarea deploy-urilor oarbe.

## Declansare si severitate

- SEV-2 daca productia nu raspunde, login/scanarea nu functioneaza sau noul deploy
  a inlocuit versiunea buna.
- SEV-3 daca build-ul nou a esuat, dar versiunea anterioara functioneaza.
- SEV-1 daca logurile arata secrete expuse, corupere de date sau acces neautorizat;
  treci si la [security-incident.md](security-incident.md).

## Date de strans

- commit SHA asteptat si commit SHA raportat de `GET /version`;
- Vercel deployment ID/URL si Render deploy ID;
- ora in UTC, etapa exacta si primul mesaj de eroare relevant;
- statusul frontend, backend direct si proxy;
- modificari recente in environment, build image sau dependente.

Nu copia valori environment in raport. Redacteaza token-uri, connection string-uri,
cookie-uri si date personale din loguri.

## 1. Stabilizare

1. Opreste alte push-uri si importuri pana cand cauza este inteleasa.
2. Verifica daca ultima versiune buna este inca activa. Un build esuat nu necesita
   automat rollback daca traficul continua pe versiunea anterioara.
3. Daca versiunea defecta este activa si impactul este SEV-2/SEV-1, urmeaza
   [rollback.md](rollback.md) fara a astepta o reparatie complexa.
4. Daca incidentul este doar backend si Vercel functioneaza, evita modificari DNS;
   izoleaza componenta care a esuat.

## 2. Localizeaza componenta

```powershell
Invoke-WebRequest "https://www.cealeg.shop" -UseBasicParsing -TimeoutSec 90
Invoke-RestMethod "https://cealeg-api.onrender.com/health" -TimeoutSec 90
Invoke-RestMethod "https://www.cealeg.shop/api/backend/health" -TimeoutSec 90
Invoke-RestMethod "https://cealeg-api.onrender.com/version" -TimeoutSec 90
```

Interpretare:

| Rezultat | Zona probabila |
| --- | --- |
| frontend nu raspunde, backend da 200 | Vercel, domeniu sau build frontend |
| backend direct nu raspunde | Render, startup Flask/Gunicorn, environment sau baza de date |
| backend direct da 200, proxy esueaza | `BACKEND_URL`, proxy Vercel sau retea |
| `/health` da 200, fluxurile cu date esueaza | Supabase/configuratie; vezi runbook-ul DB |
| commit-ul din `/version` nu este cel asteptat | deploy nepromovat, rollback sau proiect/ramura gresita |

`/health` este intentionat superficial. Diagnosticele `/readiness` si
`/admin/monitoring` se citesc numai autentificat din admin.

## 3. Vercel

1. Deschide deployment-ul asociat commit-ului, nu doar ultimul din lista.
2. Verifica Root Directory: trebuie sa fie `frontend`.
3. Identifica prima eroare din Build Logs; erorile ulterioare pot fi efecte.
4. Confirma versiunea Node compatibila cu `package.json`/CI si ca instalarea foloseste
   lockfile-ul curent.
5. Verifica numai prezenta variabilelor din `docs/environment.md`; nu le tipari.
6. Reproduce local:

```powershell
Set-Location D:\proiecte\ce_aleg\frontend
npm.cmd ci
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test:ci
npm.cmd run build
```

7. Daca build-ul trece local, compara Node, working directory, environment si
   commit SHA cu deployment-ul. Nu apasa Redeploy repetat fara o ipoteza noua.

Probleme tipice:

- `BACKEND_URL` absent sau setat la localhost in Production;
- module/lockfile nealiniate;
- eroare TypeScript/ESLint tratata strict in CI;
- sourcemap upload Sentry esuat din cauza configuratiei build-only;
- route dinamica incompatibila cu build-ul static/server;
- cron fara `CRON_SECRET` in mediul Production.

## 4. Render

Configuratia asteptata este in `render.yaml`:

- root `backend`;
- build `pip install -r requirements.txt`;
- start `python migration.py release`, apoi Gunicorn `app:create_application()` cu
  worker `gthread`;
- health check `/health`;
- Python 3.12.4 in blueprint.

1. Verifica daca esecul este Build, migrare/start sau Health Check.
2. Pentru build, cauta prima dependenta care nu se instaleaza.
3. Pentru startup, cauta eroarea anterioara mesajului "exited". Aplicatia refuza
   intentionat productia fara `DATABASE_URL` sau cu `AUTH_SECRET` nesigur.
4. Pentru health timeout, separa cold start de crash: un proces care porneste trebuie
   sa ajunga la `GET /health`; un crash va lasa traceback in log.
5. Confirma prezenta variabilelor `sync: false` si mediul `APP_ENV=production`.
6. Reproduce backend-ul fara a folosi secrete live in terminal partajat:

```powershell
Set-Location D:\proiecte\ce_aleg\backend
python -m pip install -r requirements.txt
python -m py_compile app.py models.py database.py
python -m pytest -q
```

7. Daca problema apare doar la conectarea DB, urmeaza
   [database-supabase-outage.md](database-supabase-outage.md).

Fluxul normal foloseste `autoDeployTrigger: checksPass`: Render publica numai dupa
ce workflow-ul `CI` al commitului a trecut. Fallback-ul manual
`.github/workflows/release-backend.yml` foloseste, daca este configurat, secretul
repository `RENDER_DEPLOY_HOOK_URL`, trimite `ref=<commit SHA>` si asteapta pana
cand `/version` raporteaza exact acel commit. Niciun flux nu necesita acces direct
la baza de date din GitHub, deoarece migrarea versionata ruleaza la startup Render.

## 5. Reparatie sau rollback

Alege reparatia directa numai daca:

- cauza este clara si modificarea este mica;
- datele nu au fost migrate intr-un format incompatibil;
- testele relevante pot fi rulate inainte de deploy;
- timpul estimat este mai scurt decat rollback-ul si impactul este limitat.

Alege rollback daca impactul utilizatorului continua, cauza nu este clara, reparatia
atinge mai multe componente sau noua versiune a modificat autentificarea/platile.

## 6. Verificare dupa remediere

```powershell
Set-Location D:\proiecte\ce_aleg
powershell -ExecutionPolicy Bypass -File scripts\check-production.ps1 `
  -BackendUrl "https://cealeg-api.onrender.com" `
  -FrontendUrl "https://www.cealeg.shop"
```

Verifica apoi:

1. `/version` raporteaza commit-ul intentionat.
2. Login-ul si `/auth/me` functioneaza pentru un cont de test verificat.
3. O cautare si o scanare cunoscuta raspund prin proxy.
4. Pagina admin se incarca pentru administrator.
5. Daca s-a schimbat billing/email/storage, ruleaza testul specific din runbook-ul
   acelei componente.
6. Logurile nu contin un nou val de 5xx timp de cel putin 15 minute.

## Inchidere

Noteaza cauza radacina, commit-ul bun, commit-ul reparat/revenit, durata impactului si
actiunea preventiva. Nu declara incidentul inchis doar pentru ca dashboard-ul arata
verde; dovada este fluxul relevant testat pe domeniul public.

## Escaladare externa

Deschide ticket la Vercel/Render cand status page sau logurile indica platforma,
cand un deploy identic esueaza doar in cloud ori cand nu exista acces la logurile
necesare. Proprietarul trebuie sa completeze planul, ID-urile serviciilor si canalul
de suport in registrul operational privat.
