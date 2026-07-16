# Runbook: rollback

## Scop

Rollback-ul readuce serviciul la o versiune cunoscuta ca buna. Nu este acelasi lucru
cu restaurarea bazei de date si nu anuleaza automat modificari de schema, evenimente
Stripe, emailuri trimise sau date create dupa deploy.

## Cand se foloseste

- noul deploy provoaca erori 5xx, blocarea login/scanare/billing sau regresii majore;
- hotfix-ul ar dura mai mult decat revenirea;
- cauza nu este clara, iar versiunea anterioara este compatibila cu datele curente;
- un feature nou trebuie retras rapid.

Nu face rollback automat daca versiunea veche nu intelege schema/datele noi, daca un
secret vechi este compromis sau daca problema este exclusiv la un provider extern.

## 1. Decizie si preconditii

Inregistreaza:

- incident ID, severitate si aprobator;
- commit/deployment defect si ultimul deployment bun verificat;
- schimbari DB, environment, cron, Stripe/webhook, Storage si DNS din release;
- date create/modificate dupa release;
- riscul versiunii vechi si criteriul de succes.

Confirma compatibilitatea:

| Schimbare | Intrebare obligatorie |
| --- | --- |
| schema DB | codul vechi poate citi/scrie schema curenta fara pierdere? |
| auth/token | versiunea veche accepta formatul curent in siguranta? |
| Stripe | handlerul vechi este compatibil cu evenimentele si price ID-urile curente? |
| environment | ce variabile au fost adaugate/eliminate si care sunt necesare versiunii vechi? |
| Storage | caile/politicile/formatul obiectelor sunt compatibile? |
| cron | versiunea veche ar repeta o operatie deja executata? |

Daca raspunsul este necunoscut pentru o componenta critica, opreste si pregateste un
forward fix sau o revenire coordonata de schema.

## 2. Conserva starea

1. Opreste importurile, recategorizarea si cron-urile care pot continua modificarile.
2. Salveaza logurile, deployment IDs, commit SHA si request/event IDs.
3. Fa backup DB inainte de rollback daca release-ul a scris date/schema.
4. Noteaza environment-ul dupa nume si ultima modificare, fara valori secrete.
5. Nu sterge deployment-ul defect; este necesar pentru diagnostic.

## 3. Rollback Vercel

Metoda preferata este promovarea/redeploy-ul deployment-ului anterior cunoscut ca
bun din Vercel, daca platforma si planul permit.

1. Selecteaza deployment-ul dupa commit SHA si verifica preview-ul/artefactul.
2. Confirma ca este pentru proiectul, domeniul si mediul Production corect.
3. Promoveaza/redeploy si urmareste logul pana la final.
4. Verifica domeniul canonic si proxy-ul backend.

Daca trebuie rollback prin Git, creeaza un commit nou cu `git revert`; nu folosi
`git reset --hard`, force-push sau rescrierea istoricului partajat:

```powershell
Set-Location D:\proiecte\ce_aleg
git status --short
git log -10 --oneline
git revert <commit_sha_defect>
git push
```

Pentru mai multe commit-uri, revizuieste individual ordinea si conflictele. Nu rula
comanda pana nu ai identificat exact schimbarea si worktree-ul este inteles.

## 4. Rollback Render

1. In Render, selecteaza deploy-ul reusit asociat commit-ului bun.
2. Confirma environment-ul curent; un redeploy vechi foloseste de regula configuratia
   curenta a serviciului, nu neaparat valorile istorice.
3. Redeploy/rollback conform optiunii platformei si urmareste Build/Start/Health.
4. Verifica `GET /version` pentru commit-ul asteptat.
5. Daca startup-ul esueaza din cauza schemei, nu continua redeploy-uri repetate;
   aplica planul de compatibilitate DB.

Configuratia asteptata ramane `render.yaml`, root `backend`, Gunicorn si `/health`.

## 5. Environment si secrete

- Revino o variabila non-secret numai daca versiunea veche o necesita si valoarea
  curenta este cauza confirmata.
- Nu restaura niciodata un secret compromis.
- Pentru `CRON_SECRET`, Render si Vercel trebuie sa ramana sincronizate.
- Pentru Stripe, cheia, webhook secret si price ID-urile trebuie sa ramana in acelasi
  mod/cont. Nu schimba toate simultan fara test.
- Noteaza fiecare modificare si aplica una cate una.

## 6. Baza de date

Un rollback de aplicatie este preferabil unei restaurari DB cand schema este
compatibila. Pentru schema incompatibila:

1. Pastreaza o strategie expand/contract sau o migrare inversa revizuita.
2. Ruleaza dry-run/numar exact de randuri si backup.
3. Testeaza intr-o baza izolata.
4. Nu elimina coloane/date doar pentru ca versiunea veche nu le foloseste.
5. Daca restaurarea este inevitabila, urmeaza
   [database-supabase-outage.md](database-supabase-outage.md) si reconciliaza toate
   scrierile aparute dupa backup, in special Stripe si conturi.

## 7. Stripe, email si cron

- Evenimentele Stripe continua sa fie retrimise. Confirma ca handlerul versiunii bune
  le proceseaza idempotent inainte de a reporni fluxul.
- Nu retrimite in masa evenimente in timpul rollback-ului.
- Emailurile deja trimise nu pot fi retrase; evita dublarea lor dupa revenire.
- Cron-urile Vercel `/api/cron/warmup` si `/api/cron/maintenance` se repornesc numai
  dupa ce secretul si backend-ul au fost verificate.
- Daca release-ul a creditat CeCoins sau a schimbat planuri, reconciliaza separat;
  rollback-ul codului nu corecteaza soldurile.

## 8. Verificare

```powershell
Set-Location D:\proiecte\ce_aleg
powershell -ExecutionPolicy Bypass -File scripts\check-production.ps1 `
  -BackendUrl "https://cealeg-api.onrender.com" `
  -FrontendUrl "https://www.cealeg.shop"
```

Checklist:

1. `/version` raporteaza commit-ul bun intentionat.
2. Home si proxy health raspund.
3. Contul de test se autentifica si `/auth/me` functioneaza.
4. Scanarea/cautarea unui produs cunoscut functioneaza.
5. Admin-ul se incarca si nu expune rute anonim.
6. Daca release-ul a atins billing, ruleaza un test Stripe controlat.
7. Daca a atins emailul, trimite un singur test si verifica livrarea.
8. Daca a atins Storage, testeaza obiectul de test.
9. Monitorizeaza 5xx/latenta minimum 30 minute.
10. Reporneste job-urile pe rand si observa primul ciclu.

## 9. Dupa rollback

- comunica revenirea si functiile temporar retrase;
- deschide un fix pe o ramura separata cu test de regresie;
- pastreaza deployment-ul defect si dovezile pana la inchiderea incidentului;
- documenteaza cauza, timpul de decizie si ce a facut rollback-ul dificil;
- transforma remedierea in forward deploy numai dupa CI, review si test public.

## Informatii externe necesare

Proprietarul trebuie sa completeze persoanele care aproba rollback-ul, ramura de
productie, politica de auto-deploy, retentia deployment-urilor, ultimul deployment
bun, contactele platformelor, fereastra de mentenanta si RTO/RPO. Optiunile exacte
de Promote/Rollback depind de planurile Vercel si Render active si trebuie confirmate
in dashboard.
