# Runbook: indisponibilitate baza de date sau Supabase

## Scop

Procedura acopera Supabase Postgres, connection pooler si Storage. Productia nu se
comuta la SQLite: stocarea locala Render este efemera si ar produce divergenta sau
pierdere de date.

## Declansare si severitate

- SEV-1: corupere/pierdere confirmata, acces neautorizat, service role key expusa.
- SEV-2: login, conturile, scanarea persistenta, billing sau admin nu pot folosi DB.
- SEV-3: Storage sau o parte din citiri/scrieri este degradata, cu functiile de baza
  inca disponibile.

## Simptome

- backend-ul nu porneste si raporteaza lipsa/conectare `DATABASE_URL`;
- `/health` raspunde, dar rutele cu date intorc 5xx sau timeout;
- loguri cu connection timeout, pool exhaustion, DNS/TLS sau "too many connections";
- uploadurile esueaza, dar interogarile Postgres functioneaza;
- dupa deploy lipsesc tabele/coloane sau apar erori SQL repetate.

## 1. Stabilizare

1. Opreste importurile, recategorizarea, scripturile de migrare si retrimiterile in
   masa. Nu porni mai multe job-uri pentru a "testa" baza.
2. Evita deploy-uri care ruleaza schimbari de schema pana la clarificare.
3. Daca scrierile pot corupe date sau sunt partiale, limiteaza accesul public prin
   mecanismele platformei ori revino la ultimul deploy bun. Aplicatia nu are un flag
   documentat de read-only; nu pretinde ca este read-only daca nu este.
4. Pentru compromiterea unei chei, treci simultan la
   [security-incident.md](security-incident.md).

## 2. Delimiteaza Postgres, pooler si Storage

1. Verifica status page Supabase si starea proiectului in dashboard.
2. Verifica Render Logs in acelasi interval UTC.
3. Din admin, citeste `/readiness` si `/admin/monitoring`; nu expune aceste rute
   public si nu copia date personale din rezultate.
4. Verifica separat:
   - o citire controlata din Postgres;
   - o scriere controlata pe un cont/produs de test;
   - accesul la un obiect cunoscut din bucketul public `product-images`;
   - upload/citire/stergere a unui obiect de test in `product-submissions`.
5. Daca doar Storage esueaza, nu modifica `DATABASE_URL`. Verifica URL-ul proiectului,
   service role key, numele bucketurilor si politicile.

## 3. Verifica configuratia fara a o expune

- `DATABASE_URL` exista in Render Production si indica proiectul/regiunea corecta;
- schema este `postgres`, iar parola din connection string este actuala;
- endpoint-ul pooler si portul corespund modului ales;
- TLS este disponibil; backend-ul foloseste `sslmode=require` pentru Postgres;
- `SUPABASE_URL` si `SUPABASE_SERVICE_ROLE_KEY` provin din acelasi proiect;
- bucketurile sunt exact `product-images` si `product-submissions`, daca nu au fost
  suprascrise deliberat;
- nu exista un deploy Preview/alt serviciu care consuma toate conexiunile.

Nu tipari connection string-ul. Daca trebuie comparat, compara hostul/proiectul si
ultimele 4 caractere ale credentialului intr-un canal privat.

## 4. Cauze si actiuni

### Incident provider

1. Noteaza incidentul/statusul oficial si ora.
2. Nu roti chei si nu restaura backup in timpul unei intreruperi generale fara o
   dovada ca acestea sunt cauza.
3. Pastreaza serviciul in mod sigur si retesteaza la intervale rezonabile.

### Conexiuni epuizate

1. Identifica deploy-uri/job-uri/importuri care au crescut concurenta.
2. Opreste job-urile neesentiale si asteapta eliberarea conexiunilor.
3. Verifica Metrics/Database Reports si sesiunile lungi din instrumentele Supabase.
4. Nu omori sesiuni aleator. Inainte de terminarea unei sesiuni, identifica owner-ul,
   query-ul si riscul tranzactiei.
5. Dupa revenire, dimensioneaza pool-ul/planul pe baza metricilor, nu prin presupuneri.

### Credential sau proiect gresit

1. Creeaza/roteste credentialul din Supabase daca este invalid sau suspectat expus.
2. Actualizeaza Render intr-o fereastra controlata.
3. Testeaza startup, o citire si o scriere controlata.
4. Revoca credentialul vechi dupa confirmare.

### Schema incompatibila

1. Noteaza commit-ul care a introdus asteptarea de schema.
2. Nu rula manual fragmente SQL copiate din log.
3. Fa backup inainte de orice remediere.
4. Aplica o migrare revizuita si repetabila sau revino la codul compatibil.
5. Verifica numarul de randuri si constrangerile relevante inainte/dupa.

### Storage

1. Confirma starea bucketului si politica public/privat intentionata.
2. Confirma calea obiectului si ownership-ul utilizatorului pentru contributii.
3. Nu face bucketul privat public pentru a remedia o eroare de autorizare.
4. Pentru un service role key compromis, roteste cheia si verifica toate locurile in
   care a fost configurata; nu o muta in frontend.

## 5. Backup si restaurare

Procedura existenta de backup este in `docs/supabase-backup.md`. Inainte de restaurare:

1. Stabileste RPO: care este ultimul backup/PITR disponibil si cate modificari s-ar
   pierde. Acest RPO trebuie confirmat din planul Supabase, nu presupus.
2. Pastreaza copia suspecta pentru investigatie daca exista incident de securitate.
3. Restaureaza mai intai intr-un proiect/baza izolata.
4. Ruleaza `pg_restore --list`, apoi verifica schema, numarul de utilizatori,
   abonamente, evenimente de plata si produse.
5. Reconcilierea Stripe se face dupa evenimentele Stripe, nu dupa presupuneri dintr-un
   backup mai vechi.
6. Promoveaza restaurarea numai cu o fereastra aprobata, un plan DNS/connection
   string si o cale de revenire.

## 6. Verificare de revenire

1. Backend-ul porneste cu `APP_ENV=production` si `/health` da 200.
2. Admin readiness nu are blocker DB.
3. Un cont de test se poate autentifica si citi profilul.
4. O cautare/scanare cunoscuta functioneaza.
5. O modificare reversibila pe contul de test se salveaza si poate fi citita.
6. Uploadul de test merge in bucketul corect si este sters dupa verificare.
7. Nu exista crestere de connection errors/5xx timp de 30 minute.
8. Cron/importurile sunt repornite unul cate unul, nu simultan.

## Inchidere si follow-up

Documenteaza durata, componenta (DB/pooler/Storage), cauza, datele posibil pierdute,
restaurarea folosita si masurile preventive. Completeaza in `docs/operations.md`
RTO/RPO doar dupa aprobarea proprietarului.

## Informatii externe necesare

Proprietarul trebuie sa completeze project ref, regiunea, planul Supabase, starea
PITR/backups, retentia, contactele de suport, limita de conexiuni, locatia copiilor
exportate si persoanele autorizate sa initieze restaurarea.
