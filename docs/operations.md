# Operarea serviciului Ce aleg?

Acest document este punctul de intrare pentru operarea productiei. Procedurile
detaliate sunt in `docs/runbooks/`. Nu se introduc parole, token-uri, chei API,
connection string-uri sau date personale in aceste fisiere, in issue-uri publice
sau in capturi de ecran.

## Arhitectura operationala

```text
Utilizator
  -> www.cealeg.shop (Next.js pe Vercel)
  -> /api/backend/* (proxy same-origin)
  -> cealeg-api.onrender.com (Flask + Gunicorn pe Render)
  -> Supabase Postgres si Supabase Storage
  -> Stripe (Checkout, Customer Portal, webhook)
  -> Brevo / Resend / SMTP (un singur provider activ)
  -> Open Food Facts si Open Prices (date publice externe)
```

Componente optionale sunt Redis, Sentry, Google Analytics, Meta Pixel, TikTok
Pixel, OpenAI Vision si LibreTranslate. Prezenta codului pentru o integrare nu
inseamna ca aceasta este activa; starea se confirma in mediul de productie.

## Fise de incident

- [Deploy esuat](runbooks/deploy-failure.md)
- [Indisponibilitate baza de date sau Supabase](runbooks/database-supabase-outage.md)
- [Stripe Checkout si webhook](runbooks/stripe-webhook.md)
- [Livrare email](runbooks/email-delivery.md)
- [Import si calitate catalog](runbooks/catalog-import.md)
- [Incident de securitate](runbooks/security-incident.md)
- [Rollback](runbooks/rollback.md)

Inventarul variabilelor este in [environment.md](environment.md), iar registrul
operational al procesatorilor este in [legal/dpa-register.md](legal/dpa-register.md).

## Responsabilitati de completat

| Rol | Nume | Canal principal | Inlocuitor |
| --- | --- | --- | --- |
| Proprietar produs | DE COMPLETAT | DE COMPLETAT | DE COMPLETAT |
| Responsabil tehnic | DE COMPLETAT | DE COMPLETAT | DE COMPLETAT |
| Responsabil incidente/securitate | DE COMPLETAT | DE COMPLETAT | DE COMPLETAT |
| Responsabil plati/rambursari | DE COMPLETAT | DE COMPLETAT | DE COMPLETAT |
| Responsabil confidentialitate | DE COMPLETAT | DE COMPLETAT | DE COMPLETAT |

Pentru un proiect operat de o singura persoana, acelasi nume poate ocupa mai
multe roluri, dar trebuie pastrat un contact alternativ pentru situatii urgente.

## Severitatea incidentelor

| Nivel | Exemple | Reactie tinta interna |
| --- | --- | --- |
| SEV-1 | acces neautorizat confirmat, secrete expuse, plati atribuite gresit, pierdere/corupere extinsa de date | incepe imediat; opreste actiunea daunatoare |
| SEV-2 | login, scanare, checkout, webhook, email de confirmare sau baza de date indisponibile pentru multi utilizatori | investigheaza in cel mult 30 minute |
| SEV-3 | degradare partiala, import oprit, provider extern lent, functie secundara indisponibila | investigheaza in aceeasi zi |
| SEV-4 | defect cosmetic sau operational fara impact direct asupra utilizatorilor | programeaza in backlog |

Tintele sunt reguli interne de lucru, nu garantii contractuale. Proprietarul
trebuie sa stabileasca RTO/RPO oficiale dupa ce confirma planurile furnizorilor.

## Verificari rapide

Din radacina proiectului:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check-production.ps1 `
  -BackendUrl "https://cealeg-api.onrender.com" `
  -FrontendUrl "https://www.cealeg.shop"
```

Verificari fara autentificare:

```powershell
Invoke-WebRequest "https://www.cealeg.shop" -UseBasicParsing -TimeoutSec 90
Invoke-RestMethod "https://cealeg-api.onrender.com/health" -TimeoutSec 90
Invoke-RestMethod "https://cealeg-api.onrender.com/version" -TimeoutSec 90
Invoke-RestMethod "https://www.cealeg.shop/api/backend/health" -TimeoutSec 90
```

`/health` confirma doar ca procesul web raspunde. `/readiness` si
`/admin/monitoring` contin diagnostice si necesita o sesiune de administrator;
se verifica din pagina `/admin`, nu se transforma in endpoint-uri publice.

## Rutina operationala

### Zilnic

1. Verifica deployment-urile esuate in Vercel si Render.
2. Verifica erorile noi si latenta in Render; daca Sentry este activ, verifica
   evenimentele noi si regresiile.
3. Verifica in Stripe evenimentele webhook nelivrate si platile esuate.
4. Verifica in providerul de email bounce-uri, blocari si rata de livrare.
5. Verifica in admin produse negasite, raportari si coada de contributii.
6. Confirma rezultatul cron-urilor Vercel de warm-up si maintenance.

### Saptamanal

1. Ruleaza verificarile de productie si un test manual fara plata reala.
2. Revizuieste cautarile fara rezultat si alternativele raportate.
3. Confirma ca nu exista utilizatori blocati la verificare email; foloseste
   retrimiterea din admin numai la cererea adresei respective.
4. Revizuieste Dependabot si rezultatele CI/security scanning.
5. Confirma ca ultimul backup este recent si ca destinatia lui este protejata.

### Lunar

1. Testeaza restaurarea unui backup intr-o baza izolata, niciodata peste productie.
2. Verifica membrii si permisiunile in GitHub, Vercel, Render, Supabase, Stripe si
   providerul de email.
3. Revizuieste lista de procesatori, scopurile si perioadele de retentie.
4. Verifica cheile nefolosite si programeaza rotirea secretelor cu risc ridicat.
5. Testeaza fluxurile: cont nou, confirmare email, resetare parola, scanare,
   contributie, checkout test, portal si stergere cont.

## Deploy normal

1. Porneste de la un worktree curat sau intelege fiecare modificare inclusa.
2. Ruleaza validarea completa locala:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify-project.ps1
```

3. Confirma ca CI este verde pe commit-ul care urmeaza sa fie publicat.
4. Creeaza commit si push pe ramura folosita de productie.
5. Urmareste build-ul Vercel si deploy-ul Render pana la final.
6. Noteaza commit SHA, deployment ID, ora si operatorul in jurnalul de release.
7. Ruleaza `scripts\check-production.ps1` si testeaza manual fluxul schimbat.

Publicarea automata din Git trebuie confirmata in dashboard-urile Vercel si Render;
documentatia nu presupune ca setarea este activa doar pentru ca repository-ul este
conectat.

## Jurnal minim de release/incident

Pentru fiecare release sau incident pastreaza, intr-un spatiu privat:

- data si intervalul orar in UTC;
- persoana care a actionat;
- commit SHA si ID-urile deployment-urilor;
- componenta si mediul afectat;
- simptomele si numarul aproximativ de utilizatori afectati;
- request ID-uri, Stripe event ID-uri si provider message ID-uri relevante;
- actiunile executate si rezultatul fiecareia;
- momentul revenirii si verificarile efectuate;
- follow-up-uri, proprietar si termen.

Nu copia corpuri de request, token-uri, parole, imagini de produs private sau date
personale complete in jurnal. Foloseste identificatori tehnici strict necesari.

## Dependente si mod degradat

| Dependenta indisponibila | Comportament operational recomandat |
| --- | --- |
| Supabase Postgres | opreste scrierile/importurile; nu comuta productia la SQLite |
| Supabase Storage | pastreaza API-ul disponibil daca este sigur; suspenda uploadurile afectate |
| Stripe | dezactiveaza promovarea checkout-ului; nu activa manual planuri fara reconciliere |
| Provider email | pastreaza conturile/datele; comunica incidentul si retrimite controlat dupa remediere |
| Open Food Facts/Open Prices | foloseste catalogul local; amana importurile si fallback-urile externe |
| OpenAI/LibreTranslate | mentine functiile de baza; integrarea este optionala |
| Redis | codul poate folosi limitare/cache local; monitorizeaza comportamentul pe mai multe instante |

## Reguli de siguranta

- Nu rula importuri, migrari sau scripturi de remediere simultan pe aceeasi baza.
- Orice operatie care scrie multe randuri incepe cu backup si dry-run.
- Nu sterge evenimente Stripe sau dovezi de incident in timpul investigatiei.
- Nu restaura direct peste productia activa.
- Nu roti mai multe secrete simultan fara o ordine si un test dupa fiecare pas.
- Nu comunica utilizatorilor o cauza neconfirmata si nu face promisiuni juridice
  fara validare profesionala.

## Informatii externe care lipsesc

Proprietarul trebuie sa completeze: persoanele de contact, planurile si regiunile
furnizorilor, RTO/RPO, locatia backupurilor, canalul privat de incidente, politica
de retentie, conturile/ID-urile externe si procedura aprobata de notificare. Acestea
nu pot fi deduse in siguranta doar din repository.
