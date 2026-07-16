# Registru operational al furnizorilor si acordurilor DPA

Data ultimei revizuiri: 2026-07-16  
Proprietar registru: DE COMPLETAT  
Urmatoarea revizuire: DE COMPLETAT

Acesta este un registru tehnic de lucru, nu consultanta juridica si nu declara
automat ca o anumita incadrare, baza legala sau perioada de retentie este corecta.
Incadrarea operator/imputernicit/operator independent, transferurile internationale,
textele publice si obligatiile aplicabile trebuie confirmate de proprietar si, unde
este necesar, de un profesionist calificat.

## Identitatea operatorului - de completat

| Camp | Valoare |
| --- | --- |
| Denumire legala / nume operator | DE COMPLETAT |
| Forma juridica si identificator fiscal | DE COMPLETAT |
| Adresa | DE COMPLETAT |
| Tara de stabilire | DE COMPLETAT |
| Email confidentialitate | DE COMPLETAT; in produs apare `contact@cealeg.shop` |
| Responsabil/DPO, daca este cazul | DE COMPLETAT |
| Canal cereri persoane vizate | DE COMPLETAT |
| Canal incidente | DE COMPLETAT, privat |
| Termen intern de revizuire a cererilor | DE COMPLETAT |

## Cum se foloseste registrul

Pentru fiecare furnizor activ:

1. Confirma entitatea contractanta exacta din cont/factura, nu doar marca.
2. Salveaza privat DPA-ul acceptat, versiunea, data si linkul.
3. Confirma regiunea de procesare, lista de subprocesatori si mecanismul de transfer.
4. Stabileste scopul, minimizarea datelor si retentia in configuratia contului.
5. Noteaza proprietarul intern si procedura de stergere/export.
6. Revizuieste la schimbarea planului, regiunii, produsului sau termenilor.

`Activ` trebuie sa insemne confirmat in dashboard/environment, nu doar prezent ca
dependenta in cod.

## Registrul furnizorilor

| Furnizor / serviciu | Stare tehnica observata | Date/scop observat | Rol de confirmat | DPA, regiune, transfer, retentie si proprietar |
| --- | --- | --- | --- | --- |
| Vercel | frontend productie si cron conform arhitecturii | request-uri web, IP/user-agent, cookie de sesiune in tranzit, loguri, artefacte build; variabile server-side | probabil imputernicit pentru hosting; CONFIRMA | entitate contractanta: DE COMPLETAT; DPA/versiune/data: DE COMPLETAT; regiune: DE COMPLETAT; transfer/SCC: DE COMPLETAT; retentie loguri: DE COMPLETAT; owner: DE COMPLETAT |
| Render | backend Flask `cealeg-api`, plan `free` in `render.yaml` | toate request-urile API in tranzit, IP/user-agent, identificatori cont, loguri, secrete environment | probabil imputernicit pentru hosting; CONFIRMA | entitate, DPA, regiune serviciu, subprocesatori, transfer, retentie loguri si owner: DE COMPLETAT |
| Supabase | Postgres + Storage sunt configurate in backend | conturi, email, hash parola, stare plan, istoric, favorite, cos, contributii, imagini, evenimente, identificatori Stripe | probabil imputernicit pentru DB/storage; CONFIRMA | project ref si regiune: DE COMPLETAT; entitate/DPA: DE COMPLETAT; backup/PITR/retentie: DE COMPLETAT; transfer: DE COMPLETAT; owner: DE COMPLETAT |
| Stripe | Checkout, Customer Portal si webhook implementate; productia trebuie confirmata | email si identificatori client/subscriptie/sesiune; date plata sunt colectate de Stripe Checkout, nu trebuie stocate ca numar complet de card in aplicatie | poate avea roluri diferite in functie de activitate; CONFIRMA | cont/entitate Stripe: DE COMPLETAT; DPA/termeni: DE COMPLETAT; tara contului: DE COMPLETAT; retentie si obligatii financiar-fiscale: DE COMPLETAT; owner: DE COMPLETAT |
| Brevo | provider implicit in `render.yaml`; codul suporta API | adresa email, nume daca este transmis, continut transactional, delivery/bounce metadata, IP Render | probabil imputernicit pentru email; CONFIRMA ACTIVAREA | cont/entitate/DPA: DE COMPLETAT; sender/domain: DE COMPLETAT; regiune/transfer: DE COMPLETAT; retentie event/log: DE COMPLETAT; restrictie IP: DE COMPLETAT; owner: DE COMPLETAT |
| Resend | integrare optionala, cheie disponibila ca variabila | aceleasi categorii ca emailul transactional daca este activat | probabil imputernicit daca activ; CONFIRMA | marcheaza INACTIV sau completeaza entitate/DPA/regiune/transfer/retentie/owner |
| Furnizor SMTP | fallback optional configurabil | destinatar, expeditor, continut email si metadata de livrare | depinde de furnizor; CONFIRMA | nume furnizor real, contract/DPA, regiune, retentie si owner: DE COMPLETAT sau INACTIV |
| GitHub | repository si GitHub Actions conform documentatiei/CI | cod, identitati colaboratori, commit-uri, loguri CI; date personale nu trebuie copiate in issue/log | probabil imputernicit pentru colaborare/CI; CONFIRMA | organizatie/account, entitate/DPA, regiune/transfer, retentie Actions/artifacts si owner: DE COMPLETAT |
| Sentry | SDK si variabile exista; activarea nu este dovedita | erori browser/server, URL, IP/headers si context tehnic; token-urile/query sensibile trebuie filtrate | probabil imputernicit daca activ | stare ACTIV/INACTIV: DE COMPLETAT; proiect/regiune/DPA/retentie/scrubbing/owner: DE COMPLETAT |
| Google Analytics | ID public optional si banner de consimtamant in cod | evenimente de utilizare, identificatori/cookies si date dispozitiv daca este activ | rol si temei de confirmat | ACTIV/INACTIV, proprietate GA4, consent mode, DPA/termeni, retentie, transfer si owner: DE COMPLETAT |
| Meta Pixel | ID public optional | evenimente browser/marketing daca este activ | rol si temei de confirmat; poate implica operatori asociati | ACTIV/INACTIV, business account, termeni, consimtamant, retentie si owner: DE COMPLETAT |
| TikTok Pixel | ID public optional | evenimente browser/marketing daca este activ | rol si temei de confirmat | ACTIV/INACTIV, account, termeni, consimtamant, retentie si owner: DE COMPLETAT |
| OpenAI API | Vision este optional si dezactivat implicit in example | imagini/text produs numai daca functia este activata; nu trimite date de cont nenecesare | furnizor/rol de confirmat daca activ | INACTIV recomandat pana la completarea DPA, setarilor de retentie, regiunii, minimizarii si informarii |
| LibreTranslate | URL optional, local in example | text trimis pentru traducere; instanta reala nu este identificata | depinde de operatorul instantei | ACTIV/INACTIV si operator/hosting/DPA/retentie: DE COMPLETAT; o instanta locala nu este automat fara risc |
| Open Food Facts | API/import extern utilizat pentru catalog | barcode, termeni/categorii de cautare si IP-ul backend; nu ar trebui trimise emailuri sau user ID-uri | serviciu/sursa terta; incadrarea trebuie evaluata | termeni/licenta, endpoint-uri, date trimise, log retention si owner: DE COMPLETAT |
| Open Prices | integrare externa pentru preturi | barcode, magazin/locatie/pret dupa caz si IP backend | serviciu/sursa terta; CONFIRMA | termeni/licenta, date trimise, retentie si owner: DE COMPLETAT |
| Registrator/DNS | documentele mentioneaza Namecheap, iar README recomanda Cloudflare; starea este contradictorie | domeniu, date cont administrator, loguri DNS; trafic numai daca proxy/CDN este activ | furnizor si rol de confirmat | confirma furnizorul activ, daca exista proxy/CDN, entitatea/DPA, log retention si owner |

## Activitati de prelucrare de validat

| Activitate | Persoane/date | Scop tehnic observat | Temei si retentie |
| --- | --- | --- | --- |
| Cont si autentificare | utilizatori; email, hash parola, stare verificare, sesiune, IP/loguri | creare cont, securizare acces, resetare si stergere | temei: DE VALIDAT; retentie cont/loguri: DE COMPLETAT |
| Scanare si cautare | utilizatori si vizitatori; barcode, query, rezultate, istoric, magazin | identificare produs si recomandari | temei: DE VALIDAT; retentie evenimente/istoric: DE COMPLETAT |
| Profiluri Family | titular si profiluri; nume/pseudonim, preferinte, cos | personalizarea planului Family | temei/varsta/minori: DE VALIDAT; retentie: DE COMPLETAT |
| Contributii catalog | utilizatori; imagini produs, nutritie, barcode, identificator contributor | cresterea si moderarea catalogului | temei/licenta continut/retentie imagini: DE VALIDAT |
| Plati si abonamente | clienti; email, Stripe IDs, plan, status, evenimente | checkout, activare plan, reconciliere, suport | roluri/temei/retentie fiscala: DE VALIDAT |
| Email transactional si suport | utilizatori; email, continut mesaj, status livrare | confirmare, resetare, notificari si raspuns suport | temei si retentie mailbox/provider: DE VALIDAT |
| Gamification | utilizatori; CeCoins, misiuni, referral, clasament | recompense si retentie produs | temei, reguli concurs/promotii si retentie: DE VALIDAT |
| Observabilitate si securitate | utilizatori/vizitatori; IP, user-agent, URL, request ID, erori | disponibilitate, diagnostic, prevenirea abuzului | interes/temei, minimizare si retentie: DE VALIDAT |
| Analytics/marketing | vizitatori; cookies/IDs/evenimente, numai daca activ | masurare si promovare | consimtamant/exceptii si retentie: DE VALIDAT inainte de activare |

## Cereri privind datele

Repository-ul are stergerea contului prin email si rute pentru datele de cont, dar
existenta acestora nu dovedeste singura acoperirea tuturor drepturilor sau a tuturor
copiilor din procesatori/backup. Pentru fiecare cerere:

1. Verifica identitatea printr-o metoda proportionala; nu cere date excesive.
2. Inregistreaza privat data, tipul cererii, termenul si operatorul.
3. Identifica datele in Supabase, Storage, Stripe, email, suport, observabilitate,
   analytics si backup-uri conform scopului cererii.
4. Aplica exceptiile/obligatiile de pastrare numai dupa validare juridica.
5. Livreaza datele printr-un canal sigur si documenteaza inchiderea.
6. Nu furniza date despre alti utilizatori, secrete interne sau semnale antifrauda
   care nu trebuie divulgate.

Procedura si termenul legal aplicabil trebuie completate de proprietar. Nu scrie in
politica publica un termen pe care operarea reala nu il poate respecta.

## Retentie - decizii obligatorii

Completeaza o durata, evenimentul de pornire, mecanismul de stergere si exceptia
pentru fiecare categorie:

| Categorie | Retentie aprobata | Stergere/anonymizare | Exceptii aprobate |
| --- | --- | --- | --- |
| cont activ si preferinte | DE COMPLETAT | DE COMPLETAT | DE COMPLETAT |
| cont sters | DE COMPLETAT | DE COMPLETAT | DE COMPLETAT |
| sesiuni si token-uri | DE COMPLETAT | expirare/rotire de verificat | DE COMPLETAT |
| scan history, cautari, favorite, cos | DE COMPLETAT | DE COMPLETAT | DE COMPLETAT |
| contributii si imagini | DE COMPLETAT | DE COMPLETAT | licenta/interes catalog: DE VALIDAT |
| evenimente plati | DE COMPLETAT | DE COMPLETAT | obligatii financiar-fiscale: DE VALIDAT |
| email si suport | DE COMPLETAT | provider + mailbox | litigiu/securitate: DE VALIDAT |
| loguri Render/Vercel/Sentry | DE COMPLETAT | configuratie provider | incident activ: DE VALIDAT |
| analytics/marketing | DE COMPLETAT | configuratie provider/browser | DE COMPLETAT |
| backup-uri | DE COMPLETAT | rotatie criptata | restaurare/incident: DE VALIDAT |

## Transferuri si subprocesatori

Pentru fiecare furnizor activ pastreaza privat:

- URL-ul listei de subprocesatori si data ultimei verificari;
- tarile/regiunile folosite efectiv de cont;
- mecanismul contractual invocat si versiunea documentului;
- setarile de regionalizare disponibile pe plan;
- data notificarii unei schimbari si decizia luata;
- evaluarea necesitatii unei analize suplimentare.

Nu presupune ca selectarea unei regiuni pentru baza de date regionalizeaza automat
logurile, suportul, backup-urile sau toti subprocesatorii.

## Revizuire la schimbare

Actualizeaza registrul inainte de a activa un nou SDK, pixel, AI provider, provider
email, CDN, sistem de suport sau export de date. Pull request-ul trebuie sa indice:

- ce date pleaca din aplicatie;
- scopul si minimizarea;
- secretul si proprietarul configuratiei;
- consimtamantul/informarea necesara;
- stergerea, exportul si retentia;
- DPA-ul si subprocesatorii verificati.

## Dovezi private de completat

- copii/URL-uri si date de acceptare pentru DPA-urile active;
- facturi sau pagina contului care identifica entitatea contractanta;
- capturi fara secrete ale regiunilor si retentiei;
- lista accesului administrativ si MFA;
- dovada testului de stergere/export;
- jurnalul revizuirilor acestui registru;
- decizia documentata pentru analytics, pixeli, AI si profiluri Family/minori.
