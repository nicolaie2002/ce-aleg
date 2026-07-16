# Runbook: incident de securitate

## Scop

Foloseste procedura pentru secrete expuse, acces neautorizat, abuz de cont/admin,
creditare/plati frauduloase, exfiltrare, modificari neautorizate de catalog, upload
abuziv sau suspiciune de compromitere a furnizorilor. Siguranta persoanelor si
pastrarea dovezilor au prioritate fata de revenirea rapida.

Acesta este un runbook tehnic. Decizia privind notificarea persoanelor, autoritatilor,
asiguratorului sau fortelor de ordine se ia de responsabilul legal desemnat pe baza
faptelor si a legii aplicabile.

## Severitate

Trateaza ca SEV-1 pana la infirmare cand exista:

- acces administrator neautorizat sau sesiuni/token-uri compromise;
- cheie `SUPABASE_SERVICE_ROLE_KEY`, `AUTH_SECRET`, Stripe, email, cron, DB sau
  credential de deploy expus;
- date personale citite/exportate de o persoana neautorizata;
- planuri, CeCoins, plati sau refund-uri atribuite/manipulate gresit;
- cod sau pipeline modificat prin cont compromis;
- corupere/stergere intentionata ori ransomware.

SEV-2 acopera tentativa activa sau vulnerabilitatea exploatabila fara dovada de
acces la date. SEV-3 acopera evenimente blocate, cu impact redus si dovezi suficiente.

## Roluri de incident - de completat

| Rol | Persoana | Contact privat |
| --- | --- | --- |
| Incident commander | DE COMPLETAT | DE COMPLETAT |
| Investigatie tehnica | DE COMPLETAT | DE COMPLETAT |
| Legal/confidentialitate | DE COMPLETAT | DE COMPLETAT |
| Comunicare utilizatori | DE COMPLETAT | DE COMPLETAT |
| Plati/Stripe | DE COMPLETAT | DE COMPLETAT |

O singura persoana poate ocupa roluri multiple, dar deciziile si orele trebuie
notate explicit.

## 1. Deschide incidentul

1. Creeaza un canal/document privat cu acces minim.
2. Noteaza ora descoperirii si ora estimata de inceput, ambele in UTC.
3. Aloca un ID incident si severitate initiala.
4. Noteaza cine decide containment-ul si cine pastreaza cronologia.
5. Opreste discutiile cu date sensibile in issue-uri/public chat.

## 2. Pastreaza dovezile

Inainte de schimbari distructive, unde este sigur:

- exporta logurile relevante Vercel/Render/Supabase/Stripe/email/Sentry cu interval
  si fus orar;
- noteaza deployment IDs, commit SHA, request IDs, event IDs si adrese IP relevante;
- salveaza configuratia si lista de acces fara valorile secretelor;
- fa snapshot/backup DB si Storage conform capabilitatilor planului;
- calculeaza hash-uri pentru fisierele exportate si pastreaza-le read-only;
- documenteaza fiecare actiune si operatorul.

Nu sterge contul atacator, randuri, deploy-uri sau evenimente inainte de a conserva
dovezile, exceptand cazul in care actiunea continua sa produca prejudiciu. Nu copia
mai multe date personale decat este necesar pentru investigatie.

## 3. Containment

Alege masura minima care opreste actiunea, apoi extinde daca dovezile o cer:

1. Revoca sesiunea/contul administrativ compromis si impune MFA pe furnizori.
2. Opreste job-urile de import/cron si actiunile cu scrieri in masa.
3. Restrictioneaza temporar serviciul/ruta afectata prin platforma, WAF sau un deploy
   de urgenta revizuit.
4. Pentru credential compromis, creeaza unul nou, actualizeaza consumatorul, testeaza
   si revoca vechiul. Nu astepta un release normal.
5. Pentru `AUTH_SECRET` compromis, rotirea invalideaza sesiunile/token-urile semnate;
   planifica relogarea tuturor utilizatorilor si testeaza reset/confirmare.
6. Pentru DB/Storage, roteste parola/cheia service role si verifica ca nicio cheie
   server-side nu a ajuns in bundle-ul frontend.
7. Pentru Stripe, roteste secret key/webhook secret dupa procedura Stripe si verifica
   fiecare endpoint. Nu dezactiva dovezile/event history.
8. Pentru email, roteste cheia/SMTP si verifica reguli de forwarding sau senderi
   neautorizati.
9. Pentru GitHub/Vercel/Render, revoca token-uri, sesiuni si deploy keys nefolosite;
   verifica commit-uri, webhooks si modificari environment.

Un secret suspectat compromis nu se "roteste inapoi" la valoarea veche.

## 4. Stabileste aria afectata

Raspunde cu dovezi la:

- Ce identitate/credential/ruta a fost folosita si cu ce privilegii?
- Care este prima si ultima activitate confirmata?
- Ce tabele, bucketuri, endpoint-uri, conturi si furnizori au fost accesati?
- Au fost doar citiri, sau si modificari/stergere/export?
- Ce categorii de date si cate persoane aproximativ sunt afectate?
- Au fost afectate parole in clar? Aplicatia ar trebui sa stocheze hash-uri, dar
  confirma datele efective, nu presupune.
- Au fost afectate date de plata? Aplicatia foloseste Stripe Checkout; confirma ce
  metadata/IDs exista local si ce a ramas la Stripe.
- Atacatorul a obtinut persistenta prin user admin, token, workflow, webhook, DNS,
  environment sau dependency?
- Exista acces in medii Preview/development cu date de productie?

Coreleaza request ID, user ID, IP, Stripe event ID si commit/deploy. Evita concluzii
doar dintr-un singur log; retentia providerilor poate fi incompleta.

## 5. Eradicare

1. Remediaza vulnerabilitatea in cod/configuratie si adauga un test de regresie.
2. Elimina conturile/token-urile/persistenta neautorizata dupa conservarea dovezilor.
3. Verifica repository history si artefactele build pentru secrete. Daca un secret a
   fost comis, rotirea este obligatorie chiar daca commit-ul este sters ulterior.
4. Actualizeaza dependentele vulnerabile dupa validare si rebuild complet.
5. Verifica toate mediile (Production, Preview, local shared) si toate copiile
   credentialului.
6. Reconciliaza randurile modificate cu backup-uri, Stripe si logurile sursa.
7. Nu executa SQL de remediere direct pe productie fara backup, peer review si
   numarul exact de randuri din dry-run.

## 6. Recuperare

1. Publica un build curat din commit verificat.
2. Restabileste accesul furnizorilor cu credentiale noi si MFA.
3. Ruleaza verificarile de productie si testele specifice componentei.
4. Verifica autentificarea, autorizarea admin, billing, email si Storage.
5. Monitorizeaza intensiv 24-72 ore, conform riscului, pentru aceiasi indicatori.
6. Reporneste cron/importurile pe rand.
7. Daca datele au fost restaurate, reconciliaza evenimentele valide aparute dupa RPO.

## 7. Evaluare juridica si comunicare

Responsabilul desemnat trebuie sa evalueze imediat obligatiile aplicabile. In UE,
GDPR poate impune notificarea autoritatii intr-un interval scurt (in anumite cazuri
72 de ore de la luarea la cunostinta) si, pentru risc ridicat, informarea persoanelor;
incadrarea si momentul se confirma juridic, nu de catre acest document.

Comunicarea trebuie sa contina numai fapte confirmate:

- ce s-a intamplat si intervalul cunoscut;
- ce date/servicii sunt afectate;
- ce masuri au fost luate;
- ce trebuie sa faca utilizatorul;
- un contact si actualizari ulterioare.

Nu minimiza, nu specula cauza si nu promite ca "nu s-au accesat date" fara dovada.
Pastreaza versiunea si aprobarea fiecarui mesaj.

## 8. Verificare si inchidere

Incident commander inchide numai cand:

- vectorul este inchis si credentialele afectate sunt revocate;
- toate mediile si conturile administrative au fost verificate;
- datele/platile au fost reconciliate;
- serviciile trec testele si monitorizarea nu arata activitate recurenta;
- obligatiile de notificare au o decizie documentata;
- actiunile post-incident au owner si termen.

Fa un postmortem fara vina, cu cronologie, cauza radacina, factori contributivi,
ce a functionat, ce a lipsit si teste/alerte/preventii concrete.

## Informatii externe necesare

Proprietarul trebuie sa completeze contactele de incident, autoritatea/consilierul
relevant, polita de asigurare daca exista, contactele de urgenta ale furnizorilor,
retentia logurilor, locatia dovezilor, procedura de comunicare si persoanele care pot
aproba oprirea serviciului sau notificarea publica.
