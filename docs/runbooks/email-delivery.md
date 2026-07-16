# Runbook: livrare email

## Scop

Procedura acopera confirmarea contului, resetarea parolei, stergerea contului,
notificarile, mesajele din `/support` si alertele admin. Backend-ul suporta Brevo,
Resend sau SMTP, dar un singur `EMAIL_PROVIDER` trebuie tratat ca activ.

## Destinatii distincte

- `CONTACT_EMAIL`: Reply-To public si destinatia formularului `/support/contact`;
  pentru produs este intentionat `contact@cealeg.shop`.
- `ADMIN_EMAIL`: alerte operationale generate de `send_admin_alert`.
- adresa utilizatorului: emailuri de verificare, resetare si cont.
- `EMAIL_FROM`: expeditorul verificat la provider; poate fi diferit de Reply-To.

Nu confunda forwardingul casutei `contact@cealeg.shop` cu livrarea API. Ambele pot
avea incidente separate.

## Severitate

- SEV-2: utilizatorii nu-si pot confirma contul/reseta parola sau suportul nu ajunge.
- SEV-3: intarzieri, spam/bounce pentru o parte dintre destinatari ori alerte admin
  indisponibile.
- SEV-1: cheia providerului sau continutul mailboxului a fost expus; urmeaza si
  [security-incident.md](security-incident.md).

## 1. Colecteaza dovezi minime

- tipul emailului si destinatarul mascat;
- ora UTC, providerul activ si sender domain;
- request ID backend si provider message ID, daca exista;
- status API/SMTP, bounce/blocked/deferred si motivul providerului;
- daca problema afecteaza toate domeniile sau un singur furnizor de inbox.

Nu copia token-ul din linkul de verificare/resetare, cheia API, parola SMTP sau
continutul privat complet intr-un ticket.

## 2. Test din admin

1. Autentifica-te cu administratorul pe `/admin`.
2. In diagnosticul email confirma providerul, From, Reply-To si problemele raportate.
3. Trimite un singur email de test catre o adresa controlata. UI foloseste
   `POST /admin/email-test`.
4. Verifica Inbox, Spam, provider Activity/Logs si header-ele mesajului.
5. Daca testul trece, testeaza tipul concret care esueaza; template/token/rate limit
   poate fi cauza, nu providerul.

Endpoint-urile admin sunt protejate. Nu le face publice si nu trimite teste in masa.

## 3. Verifica environment

Pentru Brevo:

- `EMAIL_PROVIDER=brevo`;
- `BREVO_API_KEY` este prezenta si activa;
- `EMAIL_FROM` este sender/domeniu verificat;
- `CONTACT_EMAIL=contact@cealeg.shop`;
- `EMAIL_FROM_NAME` este cel intentionat;
- daca Brevo aplica allowlist IP, IP-ul de iesire Render curent este permis.

Pentru Resend verifica `RESEND_API_KEY`; pentru SMTP verifica host, port, username,
password si exact unul dintre modurile TLS/SSL cerute de provider. Nu lasa configurari
partial active pentru mai multi provideri daca acestea fac diagnosticul ambiguu.

## 4. Clasifica raspunsul

| Simptom | Verificare |
| --- | --- |
| 401/403 API | cheia, permisiunile, IP allowlist, cont suspendat |
| 400 API | From neverificat, payload/destinatar invalid, politica provider |
| 429 | limita/rate plan; opreste retrimiterile repetate |
| 5xx/timeout | status provider/retea; retesteaza controlat |
| API acceptat, mesaj absent | activity log, deferred/bounce/suppression, SPF/DKIM/DMARC, spam |
| numai suportul lipseste | `CONTACT_EMAIL`, deliverability catre aceeasi casuta si forwarding |
| numai alertele lipsesc | `ADMIN_EMAIL` si throttlingul alertelor |
| numai verificarea lipseste | rate limit, cont deja verificat, adresa gresita, template/token |

Codul pastreaza ultima eroare provider in memoria procesului pentru diagnostic admin;
aceasta se poate pierde la restart si nu inlocuieste logul providerului.

## 5. DNS si reputatie

1. Verifica in provider ca domeniul/senderul este validat.
2. Confirma SPF si DKIM prin valorile recomandate de providerul activ.
3. Evalueaza DMARC deliberat; nu publica o politica restrictiva fara monitorizare si
   fara a include toti expeditorii legitimi.
4. Verifica daca domeniul From si Reply-To sunt intentionate.
5. Verifica bounce/suppression list inainte de retrimiterea catre aceeasi adresa.
6. Nu autoriza permanent intervale IP largi doar ca remediere rapida.

Modificarile DNS se fac in furnizorul activ, care trebuie confirmat deoarece
documentele proiectului mentioneaza atat Namecheap, cat si Cloudflare.

## 6. Retrimitere confirmare cont

Exista doua fluxuri:

- utilizatorul cere controlat prin `POST /auth/resend-verification`, cu rate limit;
- administratorul foloseste adresa exacta in UI, care apeleaza
  `POST /admin/users/resend-verification`.

Inainte de retrimiterea admin:

1. Confirma solicitarea si adresa cu utilizatorul.
2. Verifica daca adresa este deja confirmata sau contul nu exista.
3. Trimite o singura data si cauta provider message ID.
4. Nu activa `EXPOSE_DEV_AUTH_LINKS` in productie si nu transmite tokenul manual.
5. Daca mesajul este bounced/suppressed, rezolva cauza in provider inainte de o noua
   incercare.

## 7. Formular suport

1. Trimite un mesaj de test din `https://www.cealeg.shop/support`.
2. Confirma request 2xx si mesajul in casuta `CONTACT_EMAIL`.
3. Raspunde folosind adresa din continut; Reply-To al mesajului generat de aplicatie
   este adresa de contact a produsului, nu neaparat adresa utilizatorului.
4. Verifica separat forwardingul casutei daca mesajul apare la providerul domeniului,
   dar nu in inboxul final.
5. Mesajele utilizatorilor contin date personale; limiteaza accesul si stabileste o
   retentie in registrul DPA.

## 8. Revenire si verificare

Ruleaza, pe rand:

1. email test admin catre `contact@cealeg.shop`;
2. cont nou de test si confirmare email;
3. resetare parola pentru contul de test;
4. mesaj formular suport;
5. retrimitere admin numai daca testul initial a fost eliminat/expirat conform
   fluxului, evitand spamul.

Pentru fiecare confirma acceptarea providerului si livrarea in inbox. Monitorizeaza
30 minute rata de erori si bounce-uri.

## Rotirea credentialelor

1. Creeaza o cheie noua cu permisiunea minima necesara.
2. Actualizeaza Render, redeploy si trimite un test.
3. Confirma livrarea si ID-ul providerului.
4. Revoca cheia veche.
5. Noteaza data si operatorul fara valoarea cheii.

## Informatii externe necesare

Proprietarul trebuie sa completeze contul/providerul activ, senderul verificat,
registrar/DNS, politica SPF/DKIM/DMARC, allowlist-ul IP, limitele planului, retentia
provider/mailbox, adresa reala din `ADMIN_EMAIL` si persoanele cu acces la casuta
`contact@cealeg.shop`.
