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

Pe GitHub:

1. `New repository`
2. Nume recomandat: `ce-aleg`
3. Alege `Private` pentru inceput.
4. Nu adauga README, `.gitignore` sau licenta.

Apoi ruleaza, inlocuind utilizatorul:

```powershell
git remote add origin https://github.com/UTILIZATOR/ce-aleg.git
git push -u origin main
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
FRONTEND_PUBLIC_URL=https://NUME-PROIECT.vercel.app
FRONTEND_ORIGINS=https://NUME-PROIECT.vercel.app
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
https://NUME-BACKEND.onrender.com/health
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
BACKEND_URL=https://NUME-BACKEND.onrender.com
NEXT_PUBLIC_API_URL=/api/backend
```

6. Deploy.
7. Copiaza URL-ul Vercel si actualizeaza pe Render:

```text
FRONTEND_PUBLIC_URL=https://NUME-PROIECT.vercel.app
FRONTEND_ORIGINS=https://NUME-PROIECT.vercel.app
```

Redeploy backendul dupa modificarea variabilelor.

## 5. Stripe

1. Cat timp testezi, pastreaza cheile Stripe test/sandbox.
2. Stripe -> Developers -> Webhooks -> `Add endpoint`.
3. Endpoint:

```text
https://NUME-BACKEND.onrender.com/billing/stripe/webhook
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

- [x] Frontend Next.js si backend Flask separate
- [x] Proxy frontend `/api/backend`
- [x] Configuratie Render Blueprint
- [x] Supabase Postgres si Storage integrate in cod
- [x] Stripe Checkout si webhook implementate
- [x] Brevo integrat
- [x] Pagini Privacy si Terms
- [x] Resetare parola si stergere cont prin email
- [x] Rate limiting, limite payload si security headers
- [x] Fisierele `.env`, bazele locale si uploadurile sunt ignorate de Git

### De facut de tine

- [ ] Inlocuieste `DATABASE_URL` cu connection string-ul Supabase valid
- [ ] Verifica bucketurile Supabase
- [ ] Creeaza repository-ul GitHub si adauga remote-ul
- [ ] Creeaza Blueprint-ul Render
- [ ] Creeaza proiectul Vercel cu root `frontend`
- [ ] Actualizeaza URL-urile Vercel/Render reciproc
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
