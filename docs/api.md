# API Ce aleg?

Referinta executabila este expusa de backend:

- OpenAPI 3.1 JSON: `/api/openapi.json`;
- Swagger UI: `/api/docs`;
- aliasuri directe: `/openapi.json` si `/docs`.

Documentul de fata explica regulile de integrare. Contractul OpenAPI ramane
sursa principala pentru schema exacta a rutelor documentate.

Toate cele 109 operatii runtime au schema explicita pentru raspuns, parametri,
payload si tipul media relevant. Testele resping automat orice ruta noua care ar
ramane cu `x-contract-source: inferred`. Politica de autentificare din OpenAPI
este verificata fata de acelasi registru declarativ folosit de backend la
executie, inclusiv semnatura Stripe si bearer-ul cron.

## URL-uri

| Mediu | Baza recomandata |
|---|---|
| Browser productie | `https://www.cealeg.shop/api/backend` |
| Backend direct | URL-ul serviciului Render, numai pentru webhook/operare |
| Frontend local | `http://localhost:3000/api/backend` |
| Backend local | `http://127.0.0.1:5001` |

Aplicatia web trebuie sa foloseasca proxy-ul same-origin. Exemplele de mai jos
presupun prefixul `/api/backend`.

## Autentificare

Loginul seteaza cookie-ul `cealeg_session`. Clientul nu salveaza tokenul in
`localStorage`. Pentru cereri din browser se foloseste:

```js
await fetch("/api/backend/auth/me", {
  credentials: "include",
});
```

Operatiile `POST`, `PATCH`, `PUT` si `DELETE` sunt acceptate numai din origini
frontend de incredere. Integrarile server-to-server speciale folosesc secretul
lor dedicat: semnatura Stripe sau `CRON_SECRET`; nu folosesc cookie-ul unui
utilizator.

## Format

- request/response implicit: `application/json`;
- uploaduri: `multipart/form-data`;
- codificare: UTF-8;
- date: ISO 8601 unde endpoint-ul returneaza timestampuri;
- identificatorii interni: numere intregi; codurile de bare raman siruri.

Eroarea minima este:

```json
{
  "error": "Mesaj pentru utilizator",
  "code": "machine_readable_code"
}
```

Validarea poate adauga lista `errors`, iar rate limiting poate adauga `limit`.
Coduri uzuale: `400` input invalid, `401` autentificare, `402` plan platit,
`403` interzis, `404` lipsa, `409` conflict, `413` prea mare, `423` prelucrare
restrictionata, `429` prea multe cereri, `502/503` furnizor indisponibil.

## Grupe de endpoint-uri

| Grup | Exemple | Acces |
|---|---|---|
| Sistem | `/health`, `/readiness`, `/version`, `/api/docs` | public/admin dupa caz |
| Cont | `/register`, `/login`, `/auth/me`, `/logout` | public sau autentificat |
| Recuperare | `/forgot-password`, `/reset-password`, `/auth/verify-email` | public, limitat |
| GDPR | `/account/data`, `/account/export`, `/account/restriction`, `/privacy/consent` | autentificat |
| Produse | `/products`, `/products/search`, `/barcode/lookup/{barcode}`, `/analyze` | mixt |
| Catalog public | `/catalog/romania/stats`, `/prices/{barcode}` | public |
| Contributii | `/submissions/add`, `/submissions/{user_id}` | autentificat |
| Activitate | `/cart/*`, `/favorites/*`, `/history/*` | proprietarul resursei |
| Billing | `/billing/status`, `/billing/checkout`, `/billing/portal` | autentificat |
| Stripe | `/billing/stripe/webhook` | semnatura Stripe |
| CeCoins/misiuni | `/gamification/summary`, `/gamification/claim`, `/gamification/redeem` | autentificat |
| Family | `/family/profiles` | plan Family |
| Suport/feedback | `/support/contact`, `/feedback/product`, `/feedback/alternative` | mixt, limitat |
| Admin | `/admin/overview`, `/admin/products/*`, `/admin/submissions` | admin |
| Mentenanta | `/internal/cron/maintenance` | `CRON_SECRET` |

Rutele cu un `user_id` in cale verifica pe server ca utilizatorul autentificat
este proprietarul. Un ID schimbat manual nu acorda acces la datele altui cont.

## Exemple

### Inregistrare

```http
POST /api/backend/register
Content-Type: application/json

{
  "name": "Ana Pop",
  "email": "ana@example.com",
  "password": "o-parola-lunga-si-unica",
  "ageConfirmed": true,
  "acceptedTerms": true
}
```

Contul trebuie verificat prin email inaintea autentificarii normale. Adminul
poate retrimite verificarea prin endpoint-ul dedicat fara a modifica parola.

### Cautare produs

```http
GET /api/backend/products/search?q=iaurt&limit=20
```

Rezultatele locale au prioritate. Integrarea externa poate fi oprita prin kill
switch fara a opri catalogul local.

### Scanare dupa cod de bare

```http
GET /api/backend/barcode/lookup/5941234567890
```

Codul de bare trebuie confirmat de utilizator inaintea contributiei pentru un
produs negasit. Daca sursa externa nu raspunde, API-ul returneaza o eroare
controlata sau fallback local, nu un succes atribuit gresit furnizorului extern.

### Checkout plan

```http
POST /api/backend/billing/checkout
Content-Type: application/json

{
  "plan": "pro",
  "billingInterval": "monthly"
}
```

Este necesara autentificarea. Backendul alege Price ID-ul din configuratie;
clientul nu trimite suma. Activarea finala este facuta de webhook-ul Stripe.

### Contact suport

```http
POST /api/backend/support/contact
Content-Type: application/json

{
  "name": "Ana Pop",
  "email": "ana@example.com",
  "topic": "Nu am primit emailul",
  "message": "Am verificat si folderul Spam."
}
```

Destinatia operationala este `CONTACT_EMAIL`, configurata in productie ca
`contact@cealeg.shop`.

## Rate limiting

Exista o limita globala si limite mai stricte pentru autentificare, scanare,
AI/OCR server-side, cautare, suport, contributii si recompense. Productia
foloseste Render Key Value/Redis pentru contoare distribuite. Daca Redis este
temporar indisponibil, fallback-ul local este protejat pentru acces concurent,
dar se reseteaza la restart. Clientul trebuie sa trateze `429` si sa permita
reincercarea dupa o pauza, fara bucle automate agresive.

## Idempotenta

- evenimentele Stripe sunt deduplicate dupa `event.id`;
- checkouturile folosesc chei de idempotenta scoped;
- creditarea CeCoins si recompensele au evenimente persistente;
- clientul nu trebuie sa presupuna esec doar pentru ca redirectul Stripe a fost
  inchis; trebuie sa reciteasca `/billing/status` sau endpoint-ul de sync.

## Uploaduri

Uploadurile accepta numai formatele si dimensiunile definite de endpoint.
Imaginile sunt validate prin continut, normalizate si stocate sub nume generate
de server. Nu se foloseste numele de fisier furnizat de utilizator ca o cale.

## Observabilitate

Fiecare request primeste un request ID, returnat si in logurile structurate.
Pentru investigatii se noteaza timestampul, endpoint-ul, codul HTTP si request
ID-ul, niciodata parola, cookie-ul sau cheia furnizorului.

## Compatibilitate

Schimbarile incompatibile necesita o versiune noua sau o perioada de tranzitie.
Adaugarea unor campuri JSON este compatibila; clientii trebuie sa ignore
campurile necunoscute. Eliminarea/renumirea unui camp documentat necesita
actualizarea OpenAPI, a testelor de contract si a frontendului in acelasi release.
