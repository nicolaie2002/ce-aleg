# Ce aleg? - publicare pas cu pas

## Schema de productie

```text
Telefon / laptop
      |
      v
Domeniu (DNS Namecheap)
      |
      v
Vercel - Next.js
      |
      | HTTPS: /api/backend/*
      v
Render - Flask API
      |
      +-- Supabase Postgres (date)
      +-- Supabase Storage (imagini)
      +-- Open Food Facts / Open Prices (catalog extern)
      +-- Stripe (plati + webhook)
      `-- Brevo (emailuri)
```

## 1. GitHub

In proiect ruleaza:

```powershell
git init -b main
git add .
git status
git commit -m "Initial production-ready version"
```

Repository GitHub:

```text
https://github.com/nicolaie2002/ce-aleg
```

Repository-ul este deja creat si conectat. Pentru urmatoarele modificari este
suficient:

```powershell
git add .
git commit -m "Descrierea modificarilor"
git push
```

Fisierul `backend/.env` este ignorat si nu trebuie urcat niciodata.

## 2. Supabase

1. Supabase Dashboard -> proiect -> `Connect`.
2. Copiaza connection string-ul pentru `Transaction pooler` sau `Session pooler`.
3. Inlocuieste parola din string cu parola bazei de date.
4. Pune string-ul complet in `DATABASE_URL`.
5. Pastreaza `SUPABASE_URL` si cheia `service_role` numai in backend.
6. In Storage creeaza bucketurile:
   - `product-images` - public
   - `product-submissions` - privat

Testeaza conexiunea inainte de migrare:

```powershell
cd backend
.\venv\Scripts\python.exe -c "from app import app; print('Database connection OK')"
```

Daca vrei sa muti datele SQLite existente:

```powershell
.\venv\Scripts\python.exe migrate_sqlite_to_supabase.py
```

## 3. Backend pe Render

Nu publica backendul Flask pe Vercel pentru aceasta arhitectura. Foloseste
Render; `render.yaml` din radacina este deja pregatit.

1. Render Dashboard -> `New` -> `Blueprint`.
2. Conecteaza repository-ul GitHub.
3. Render va detecta `render.yaml`.
4. Completeaza variabilele marcate `sync: false`.

Valori importante:

```text
DATABASE_URL=<connection string Supabase>
SUPABASE_URL=<project URL>
SUPABASE_SERVICE_ROLE_KEY=<service role key>
FRONTEND_PUBLIC_URL=https://www.cealeg.shop
FRONTEND_ORIGINS=https://www.cealeg.shop,https://cealeg.shop,https://ce-aleg.vercel.app
ADMIN_EMAIL=<emailul tau>
EMAIL_PROVIDER=brevo
EMAIL_FROM=<expeditor verificat in Brevo>
BREVO_API_KEY=<cheia Brevo>
STRIPE_SECRET_KEY=<cheia Stripe>
STRIPE_WEBHOOK_SECRET=<se completeaza dupa pasul Stripe>
STRIPE_PRO_PRICE_ID=<price id lunar Pro>
STRIPE_PRO_YEARLY_PRICE_ID=<price id anual Pro>
STRIPE_FAMILY_PRICE_ID=<price id lunar Family>
STRIPE_FAMILY_YEARLY_PRICE_ID=<price id anual Family>
STRIPE_AUTOMATIC_TAX=false
STRIPE_TAX_ID_COLLECTION=false
```

Render genereaza automat `AUTH_SECRET`. Dupa deploy verifica:

```text
https://cealeg-api.onrender.com/health
```

Nota: serviciul Render gratuit poate intra in repaus cand nu este folosit.
Este bun pentru testare; pentru raspuns constant vei avea nevoie ulterior de
un plan fara repaus.

## 4. Frontend pe Vercel

1. Vercel -> `Add New` -> `Project`.
2. Importa repository-ul GitHub.
3. La `Root Directory` selecteaza `frontend`.
4. Framework-ul trebuie detectat ca Next.js.
5. Adauga:

```text
BACKEND_URL=https://cealeg-api.onrender.com
NEXT_PUBLIC_API_URL=/api/backend
```

6. Deploy.
7. URL-ul Vercel este:

```text
https://ce-aleg.vercel.app
```

8. Domeniul public conectat la Vercel este:

```text
https://www.cealeg.shop
```

Valorile corespunzatoare sunt deja salvate in `render.yaml`, iar Render le
sincronizeaza la urmatorul deploy.

## 5. Stripe

1. Cat timp testezi, pastreaza cheile Stripe test/sandbox.
2. In Stripe creeaza produse si preturi recurente, nu Payment Links manuale:
   - Pro lunar: `19.99 RON / month`
   - Pro anual: `149 RON / year`
   - Family lunar: `29.99 RON / month`
   - Family anual: `249 RON / year`
3. Copiaza ID-urile `price_...` in Render:
   - `STRIPE_PRO_PRICE_ID`
   - `STRIPE_PRO_YEARLY_PRICE_ID`
   - `STRIPE_FAMILY_PRICE_ID`
   - `STRIPE_FAMILY_YEARLY_PRICE_ID`
4. Lasa momentan:

```text
STRIPE_AUTOMATIC_TAX=false
STRIPE_TAX_ID_COLLECTION=false
```

Activeaza-le doar dupa ce ai configurat taxele in Stripe si stii exact cum vrei
sa colectezi datele de facturare.
5. Stripe -> Developers -> Webhooks -> `Add endpoint`.
6. Endpoint:

```text
https://cealeg-api.onrender.com/billing/stripe/webhook
```

Evenimente recomandate pentru endpoint:

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

7. Copiaza signing secret-ul `whsec_...` in Render ca
   `STRIPE_WEBHOOK_SECRET`.
8. Testeaza Checkout cu `4242 4242 4242 4242`, o data viitoare si orice CVC.
9. Treci pe chei live numai dupa ce firma, preturile si domeniul sunt gata.

Nota: aplicatia foloseste Stripe Checkout prin API, nu Payment Links. In Stripe
Dashboard nu trebuie sa creezi Payment Link pentru site. Preturile `price_...`
din produse sunt suficiente; backendul creeaza sesiunea Checkout pentru
utilizatorul autentificat si webhookul actualizeaza automat planul.

## 6. Brevo

1. Verifica expeditorul sau domeniul in Brevo.
2. Adauga SPF si DKIM cand ai domeniul.
3. Din pagina admin testeaza emailurile:
   - bun venit
   - resetare parola
   - confirmare stergere cont

LibreTranslate de pe portul local `5002` nu exista automat pe Render.
Interfata RO/EN functioneaza, dar traducerea dinamica externa trebuie fie
dezactivata, fie publicata ulterior ca serviciu separat.

## 7. Domeniu

Domeniul cumparat:

```text
cealeg.shop      -> redirect Vercel catre www
www.cealeg.shop  -> Vercel
```

DNS Namecheap:

```text
A @ -> 216.198.79.1
CNAME www -> recordul recomandat de Vercel
```

Backendul ramane momentan pe Render:

```text
https://cealeg-api.onrender.com
```

Daca se configureaza ulterior `api.cealeg.shop`, actualizeaza:

```text
Vercel BACKEND_URL=https://api.cealeg.shop
Render FRONTEND_PUBLIC_URL=https://www.cealeg.shop
Render FRONTEND_ORIGINS=https://www.cealeg.shop,https://cealeg.shop
Stripe webhook=https://api.cealeg.shop/billing/stripe/webhook
```

## Checklist

### Facut in proiect

- [x] Repository GitHub creat si conectat
- [x] Frontend Next.js si backend Flask separate
- [x] Proxy frontend `/api/backend`
- [x] Configuratie Render Blueprint
- [x] Backend publicat la `https://cealeg-api.onrender.com`
- [x] Frontend publicat la `https://ce-aleg.vercel.app`
- [x] Supabase Postgres conectat si testat
- [x] Bucketurile Supabase Storage create si testate
- [x] Stripe Checkout si webhook implementate
- [x] Produsele Stripe de test sunt valide
- [x] Endpointul Stripe de test a fost creat pentru backendul Render
- [x] Brevo integrat
- [x] Brevo trimite emailuri din productie
- [x] Pagini Privacy si Terms
- [x] Resetare parola si stergere cont prin email
- [x] Rate limiting, limite payload si security headers
- [x] Fisierele `.env`, bazele locale si uploadurile sunt ignorate de Git
- [x] Buildul de productie trece
- [x] Cele 33 de teste smoke trec
- [x] GitHub Actions si Dependabot configurate
- [x] Domeniu `cealeg.shop` cumparat si conectat la Vercel
- [x] UI premium: suprafete interactive, hover, tilt subtil si animatii controlate
- [x] Profiluri Family v1: creare membru, selectare profil si preferinte separate
- [x] Footer global profesional si header mai curat
- [x] Accente UI rafinate: verde pastrat pentru brand/scor, cyan/amber pentru navigatie si actiuni

### De facut de tine

- [x] Genereaza o cheie Brevo noua si actualizeaza `BREVO_API_KEY`
- [x] Verifica expeditorul `EMAIL_FROM` in Brevo
- [x] Autorizeaza IP-ul Render in Brevo
- [x] Copiaza noul `STRIPE_WEBHOOK_SECRET` din `backend/.env` in Render
- [x] Proiectul Vercel foloseste root `frontend`
- [x] Proxy-ul public Vercel -> Render raspunde corect
- [x] URL-urile Vercel/Render sunt configurate reciproc
- [x] Creeaza webhookul Stripe public
- [x] Testeaza emailurile din admin
- [x] Testeaza inregistrare, login, scanare, cos, plata si stergere cont
- [x] Cumpara si conecteaza domeniul
- [ ] Verifica textele legale si datele de contact

### Blocante pentru lansare

- [x] `/readiness` nu raporteaza blocante
- [x] `APP_ENV=production`
- [x] `COOKIE_SECURE=true`
- [x] Niciun URL localhost in variabilele de productie
- [x] Buildul frontend trece
- [x] Stripe test functioneaza si webhookul actualizeaza planurile
- [x] Emailurile ajung in inbox
- [x] Scanarea este testata pe telefon prin HTTPS

## Stare verificata la 17 iunie 2026

```text
GitHub repository:      OK
Supabase Postgres:      OK
Supabase Storage:       OK
Stripe test prices:     OK
Frontend production:   OK
Smoke tests:            33/33
Brevo API:              OK
Brevo email productie:  OK
Render deployment:      OK
Vercel deployment:      OK
Custom domain:          https://www.cealeg.shop
UI polish local:        lint OK, build OK
Family profiles local:  API + UI OK
Smoke local fara scrieri: 25/25
```

Backendul public a fost verificat:

```text
/health:                HTTP 200
/readiness anonim:      HTTP 401
/auth/me anonim:        HTTP 401
Security headers:       OK
Stripe webhook:         OK in modul test
CORS frontend:          https://www.cealeg.shop, https://cealeg.shop, https://ce-aleg.vercel.app
Email productie:        OK
```

Brevo a blocat initial serverul Render pentru IP neautorizat. IP-ul folosit la
test a fost adaugat in Brevo -> Security -> Authorised IPs. Pe Render Free,
IP-ul de iesire se poate schimba; daca emailurile se opresc din nou, verifica
logurile Render si autorizeaza noul IP sau dezactiveaza restrictia de IP in
Brevo.

Atentie: verificarea din 14 iunie 2026 a aratat ca instanta Render nu avea
`DATABASE_URL` configurat si folosea SQLite temporar. Codul refuza acum sa
porneasca un deploy nou de productie fara Postgres, pentru a evita pierderea
conturilor.

In Render -> `cealeg-api` -> `Environment`, copiaza din `backend/.env`:

```text
DATABASE_URL
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
STRIPE_PRO_PRICE_ID
STRIPE_PRO_YEARLY_PRICE_ID
STRIPE_FAMILY_PRICE_ID
STRIPE_FAMILY_YEARLY_PRICE_ID
BREVO_API_KEY
EMAIL_FROM
ADMIN_EMAIL
```

Nu copia valorile in documentatie, GitHub sau conversatii. Dupa salvare,
Render trebuie sa faca un deploy reusit, iar apoi se retesteaza inregistrarea.
