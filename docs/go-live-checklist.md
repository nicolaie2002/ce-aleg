# Ce aleg? - publicare pas cu pas

## Schema de productie

```text
Telefon / laptop
      |
      v
Domeniu (DNS Cloudflare)
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
FRONTEND_PUBLIC_URL=https://ce-aleg.vercel.app
FRONTEND_ORIGINS=https://ce-aleg.vercel.app
ADMIN_EMAIL=<emailul tau>
EMAIL_PROVIDER=brevo
EMAIL_FROM=<expeditor verificat in Brevo>
BREVO_API_KEY=<cheia Brevo>
STRIPE_SECRET_KEY=<cheia Stripe>
STRIPE_WEBHOOK_SECRET=<se completeaza dupa pasul Stripe>
STRIPE_PRO_PRICE_ID=<price id>
STRIPE_FAMILY_PRICE_ID=<price id>
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

Valorile corespunzatoare sunt deja salvate in `render.yaml`, iar Render le
sincronizeaza la urmatorul deploy.

## 5. Stripe

1. Cat timp testezi, pastreaza cheile Stripe test/sandbox.
2. Stripe -> Developers -> Webhooks -> `Add endpoint`.
3. Endpoint:

```text
https://cealeg-api.onrender.com/billing/stripe/webhook
```

4. Copiaza signing secret-ul `whsec_...` in Render ca
   `STRIPE_WEBHOOK_SECRET`.
5. Testeaza Checkout cu `4242 4242 4242 4242`, o data viitoare si orice CVC.
6. Treci pe chei live numai dupa ce firma, preturile si domeniul sunt gata.

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

Cand cumperi domeniul:

```text
www.domeniu.ro  -> Vercel
api.domeniu.ro  -> Render
```

Actualizeaza apoi:

```text
Vercel BACKEND_URL=https://api.domeniu.ro
Render FRONTEND_PUBLIC_URL=https://www.domeniu.ro
Render FRONTEND_ORIGINS=https://www.domeniu.ro,https://domeniu.ro
Stripe webhook=https://api.domeniu.ro/billing/stripe/webhook
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
- [x] Pagini Privacy si Terms
- [x] Resetare parola si stergere cont prin email
- [x] Rate limiting, limite payload si security headers
- [x] Fisierele `.env`, bazele locale si uploadurile sunt ignorate de Git
- [x] Buildul de productie trece
- [x] Cele 33 de teste smoke trec
- [x] GitHub Actions si Dependabot configurate

### De facut de tine

- [ ] Genereaza o cheie Brevo noua si actualizeaza `BREVO_API_KEY`
- [ ] Verifica expeditorul `EMAIL_FROM` in Brevo
- [ ] Copiaza noul `STRIPE_WEBHOOK_SECRET` din `backend/.env` in Render
- [x] Proiectul Vercel foloseste root `frontend`
- [x] Proxy-ul public Vercel -> Render raspunde corect
- [x] URL-urile Vercel/Render sunt configurate reciproc
- [ ] Creeaza webhookul Stripe public
- [ ] Testeaza cele trei emailuri din admin
- [ ] Testeaza inregistrare, login, scanare, cos, plata si stergere cont
- [ ] Cumpara si conecteaza domeniul
- [ ] Verifica textele legale si datele de contact

### Blocante pentru lansare

- [ ] `/readiness` nu raporteaza blocante
- [ ] `APP_ENV=production`
- [ ] `COOKIE_SECURE=true`
- [ ] Niciun URL localhost in variabilele de productie
- [ ] Buildul frontend si testele smoke trec
- [ ] Stripe este in modul dorit si webhookul returneaza `2xx`
- [ ] Emailurile ajung in inbox
- [ ] Scanarea este testata pe telefon prin HTTPS

## Stare verificata la 14 iunie 2026

```text
GitHub repository:      OK
Supabase Postgres:      OK
Supabase Storage:       OK
Stripe test prices:     OK
Frontend production:   OK
Smoke tests:            33/33
Brevo API:              EROARE 401 - cheia trebuie regenerata
Render deployment:      OK
Vercel deployment:      OK
Custom domain:          NEFACUT
```

Backendul public a fost verificat:

```text
/health:                HTTP 200
/readiness anonim:      HTTP 401
/auth/me anonim:        HTTP 401
Security headers:       OK
Stripe webhook:         asteapta secretul in Render
CORS frontend:          https://ce-aleg.vercel.app
```
