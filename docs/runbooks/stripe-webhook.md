# Runbook: Stripe Checkout, portal si webhook

## Scop

Procedura acopera abonamentele Free/Pro/Family, pachetele CeCoins, Customer Portal
si endpoint-ul `POST /billing/stripe/webhook`. Stripe este sursa externa pentru
starea platii; aplicatia nu trebuie sa acorde planuri sau CeCoins doar pe baza
redirectului din browser.

## Declansare si severitate

- SEV-1: plan/CeCoins acordate contului gresit, creditare repetata, secret webhook
  compromis sau plati live executate neintentionat.
- SEV-2: checkout-ul nu porneste, webhook-urile live esueaza in masa sau planurile
  platite nu se activeaza.
- SEV-3: un singur eveniment/client necesita reconciliere.

## Identificatori de colectat

- Stripe request ID, event ID (`evt_...`), Checkout Session ID (`cs_...`), Customer
  ID (`cus_...`) si Subscription ID (`sub_...`);
- user ID intern, fara a publica emailul complet;
- modul Stripe (test/live), ora UTC si endpoint ID;
- commit/deployment si request ID backend.

Nu colecta numarul complet al cardului, CVC, cookie-ul de sesiune, secret key sau
webhook signing secret.

## 1. Stabilizare

1. Daca exista creditare gresita/repetata, opreste promovarea checkout-ului si
   limiteaza temporar accesul la actiunea afectata prin cea mai sigura metoda a
   platformei. Nu sterge evenimente sau randuri inainte de reconciliere.
2. Daca secretul este expus, incepe rotirea si urmeaza
   [security-incident.md](security-incident.md).
3. Nu activa manual planuri pentru a ascunde problema. O exceptie de suport trebuie
   aprobata, jurnalizata si reconciliata ulterior cu Stripe.

## 2. Separa Checkout de webhook

| Test | Rezultat | Interpretare |
| --- | --- | --- |
| `POST /billing/checkout` autentificat nu produce URL | configuratie/price/customer/API Stripe |
| browserul ajunge in Stripe si plata reuseste, dar planul nu se schimba | webhook, secret, eveniment sau reconciliere |
| planul se schimba, dar redirectul arata eroare | frontend/sync dupa redirect; plata poate fi valida |
| pachetul CeCoins porneste, dar nu crediteaza | flux coin checkout/webhook/idempotenta |
| Customer Portal nu porneste | Customer ID sau configurare portal |

Rutele relevante sunt:

- `GET /billing/status`;
- `POST /billing/checkout`;
- `POST /billing/portal`;
- `POST /billing/stripe/webhook`;
- `POST /gamification/coin-checkout`;
- `POST /gamification/coin-checkout/sync`.

Toate actiunile utilizator, in afara webhook-ului semnat, trebuie testate cu o
sesiune autentificata.

## 3. Verifica configuratia

In Render, confirma fara a afisa valorile:

1. `PAYMENT_PROVIDER=stripe`.
2. `STRIPE_SECRET_KEY` apartine modului corect.
3. Toate price ID-urile Pro/Family lunar/anual si Bronze/Gold/Diamond apartin
   aceluiasi cont si aceluiasi mod.
4. `STRIPE_WEBHOOK_SECRET` apartine endpoint-ului live exact, nu Stripe CLI sau
   unui endpoint vechi.
5. Endpoint-ul este
   `https://cealeg-api.onrender.com/billing/stripe/webhook`, daca domeniul API nu
   a fost schimbat deliberat.
6. Success/cancel URL folosesc `FRONTEND_PUBLIC_URL` de productie.
7. Customer Portal este configurat in acelasi mod Stripe.

Evenimentele documentate pentru configurare sunt:

```text
checkout.session.completed
customer.subscription.created
customer.subscription.updated
customer.subscription.deleted
customer.subscription.paused
customer.subscription.resumed
invoice.paid
invoice.payment_succeeded
invoice.payment_failed
invoice.payment_action_required
```

Confirma lista efectiva in Stripe si comportamentul curent al codului inainte de a
elimina un eveniment.

## 4. Diagnostic webhook

1. Stripe Dashboard -> Developers -> Webhooks -> endpoint -> Events.
2. Gaseste evenimentul dupa ID si citeste statusul HTTP/raspunsul.
3. `400` indica de regula payload/semnatura; verifica secretul endpoint-ului si ca
   body-ul ajunge nemodificat la Flask.
4. `401/403` indica o protectie aplicata gresit webhook-ului sau URL gresit.
5. `404/405` indica path/metoda gresita ori deploy vechi.
6. `5xx` necesita corelare cu Render Logs dupa ora si request ID.
7. `2xx` nu dovedeste singur actualizarea corecta; verifica billing status si
   evenimentul intern aferent.

Nu loga payload-ul integral. Poate contine email si metadata de client.

## 5. Retrimitere si reconciliere

1. Confirma mai intai ca handlerul este idempotent pentru tipul de eveniment si ca
   evenimentul nu a fost deja aplicat.
2. Fa un snapshot/backup inainte de o reconciliere in masa.
3. Foloseste functia de resend din Stripe Dashboard pentru event ID-ul exact.
4. Retrimite un singur eveniment si verifica efectul inainte de urmatorul.
5. Pentru CeCoins, compara session/payment ID si inregistrarea interna de creditare;
   soldul singur nu este dovada suficienta.
6. Pentru abonamente, compara customer, subscription, status, price si perioada cu
   `GET /billing/status` si datele interne.
7. Daca un eveniment vechi ar retrograda o stare mai noua, opreste retrimiterea si
   remediaza ordonarea/reconcilierea in cod.

## 6. Test controlat

Preferabil testeaza intai in Stripe Test cu un cont de test separat:

1. Checkout Pro lunar si anulare inainte de plata.
2. Checkout finalizat si activare numai dupa confirmare Stripe.
3. Portal deschis pentru clientul creat.
4. Upgrade/downgrade/cancel conform regulii produsului.
5. Plata esuata si starea afisata utilizatorului.
6. Un pachet CeCoins, verificand o singura creditare.
7. Retrimiterea aceluiasi eveniment, verificand ca nu dubleaza beneficiul.

Un test live foloseste o plata minima aprobata de proprietar si se ramburseaza prin
procedura financiara stabilita; nu folosi numere de card test in modul live.

## 7. Verificare de revenire

- checkout returneaza URL Stripe pentru planul/pachetul corect;
- endpoint-ul webhook raspunde 2xx evenimentelor valide si respinge semnaturile
  invalide;
- billing status corespunde Stripe pentru contul de test;
- CeCoins sunt creditati exact o data;
- portalul apartine aceluiasi customer;
- emailurile/mesajele de dupa plata nu contin date incorecte;
- nu exista un val nou de `payment_error` sau webhook 5xx timp de 30 minute.

## Rotirea secretului webhook

1. Creeaza/roteste secretul in Stripe conform optiunilor disponibile contului.
2. Actualizeaza `STRIPE_WEBHOOK_SECRET` in Render fara a-l copia in Git/log.
3. Redeploy si trimite un eveniment test controlat.
4. Confirma semnatura si efectul idempotent.
5. Revoca secretul vechi dupa confirmare, daca Stripe permite o perioada de
   suprapunere.

## Inchidere

Documenteaza event IDs, conturile afectate, orice ajustare/rambursare, cine a aprobat
si dovada reconcilierii. Datele financiar-fiscale, politica de rambursare si
retentia trebuie stabilite de proprietar cu suport profesional adecvat.
