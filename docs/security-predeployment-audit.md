# Ce aleg? - audit securitate inainte de lansare

Reper folosit: checklist-ul de pre-deployment mentionat de Niko si adaptarile
necesare pentru arhitectura noastra Vercel + Render + Supabase + Stripe + Brevo.

## Rezumat

```text
Frontend public:     https://www.cealeg.shop
Backend public:      https://cealeg-api.onrender.com
Baza de date:        Supabase Postgres
Storage:             Supabase Storage
Plati:               Stripe Checkout + webhook
Emailuri:            Brevo
```

## Ce este deja acoperit

- [x] Autentificare obligatorie pe dashboard, cos, favorite, istoric, scanare,
      live assistant, checkout, admin si actiuni sensibile.
- [x] Verificare ownership pentru date pe `user_id`, item-uri de cos, favorite,
      istoric si propuneri.
- [x] Admin guard pentru rutele `/admin/*`.
- [x] Rate limiting global si separat pentru auth, scanare, traduceri si rute AI.
- [x] Resetare parola cu token semnat si expirare controlata prin
      `PASSWORD_RESET_MAX_AGE`.
- [x] Confirmare email la creare cont.
- [x] Parole hash-uite cu Werkzeug, fara parole in clar.
- [x] Limita upload prin `MAX_UPLOAD_MB`.
- [x] Limita payload JSON prin `MAX_JSON_BODY_BYTES`.
- [x] Validari pe barcode, text, preturi si valori nutritionale.
- [x] CORS limitat la domeniile din `FRONTEND_ORIGINS`.
- [x] Blocare request-uri state-changing venite din origin/referer necunoscut.
- [x] Protectie de baza prin Fetch Metadata pentru cereri cross-site suspecte.
- [x] Cookie-uri HttpOnly, SameSite=Lax si Secure in productie.
- [x] Security headers pe backend si frontend.
- [x] Erori 413/405/500 curate, fara stack trace expus userului.
- [x] Request ID pe raspunsuri pentru diagnostic.
- [x] Readiness endpoint care blocheaza productie fara Postgres, fara secret sigur
      sau cu Stripe test in productie.
- [x] `.env`, baze locale si uploaduri locale ignorate de Git.
- [x] Dependabot pentru npm, pip si GitHub Actions.
- [x] CI: backend compile, frontend lint si build.
- [x] Indexuri DB pentru produse, cos, favorite, preturi si cautari fara rezultat.

## Checklist inainte de reclame

- [ ] `/api/backend/readiness` nu are blocante pe `https://www.cealeg.shop`.
- [ ] Stripe este pe chei live: `STRIPE_SECRET_KEY` incepe cu `sk_live_`.
- [ ] Stripe webhook live trimite catre
      `https://cealeg-api.onrender.com/billing/stripe/webhook`.
- [ ] Stripe webhook are evenimentele:
      `checkout.session.completed`, `customer.subscription.created`,
      `customer.subscription.updated`, `customer.subscription.deleted`,
      `invoice.paid`, `invoice.payment_succeeded`, `invoice.payment_failed`,
      `invoice.payment_action_required`.
- [ ] Brevo sender este verificat; ideal domeniul `cealeg.shop` are SPF/DKIM.
- [ ] Google Search Console are sitemap:
      `https://www.cealeg.shop/sitemap.xml`.
- [ ] Test manual pe telefon: cont nou, confirmare email, login, scanare,
      alternative, cos, favorite, plata, resetare parola, stergere cont.
- [ ] Test admin: `/admin` incarca statistici, produse negasite si email test.
- [ ] Backup/export Supabase pregatit inainte de campanii mari.
- [ ] Plan de rollback: ultimul deploy bun in Vercel/Render identificat si
      posibilitatea de revert la commit-ul anterior.

## Atacuri si raspunsul nostru

| Risc | Protectie actuala | De urmarit |
| --- | --- | --- |
| Credential stuffing | Rate limit pe login/register/reset | Crestere `AUTH_RATE_LIMIT_WINDOW` daca apar atacuri |
| CSRF pe actiuni sensibile | Origin/Referer + Fetch Metadata + SameSite=Lax | Pentru aplicatie mare, token CSRF explicit |
| Acces la datele altui user | Ownership checks in `before_request` | Teste automate dedicate pe rute cu `user_id` |
| Payload mare / upload abuziv | `MAX_JSON_BODY_BYTES`, `MAX_UPLOAD_MB` | Rate limit per user cand traficul creste |
| Erori expuse | Handler 500 generic + request ID | Integrare Sentry/Logtail pentru productie |
| Chei expuse | `.env` ignorat, secrete doar in Render/Vercel | Scanare periodica cu GitHub secret scanning |
| Recommandari gresite | Filtru categorie/familie produs, admin pentru lipsuri | Moderare si blacklist explicit cand apar cazuri noi |
| Date pierdute | Postgres Supabase obligatoriu in productie | Backup programat si export inainte de campanii |

## Comenzi rapide de verificare locala

```powershell
cd D:\proiecte\ce_aleg
python -m py_compile backend\app.py backend\models.py backend\database.py
cd frontend
npm.cmd run lint
npm.cmd run build
npm.cmd audit --omit=dev --audit-level=high
```

## Comenzi rapide productie

```powershell
curl https://www.cealeg.shop/api/backend/health
curl https://www.cealeg.shop/api/backend/readiness
curl https://www.cealeg.shop/sitemap.xml
curl https://www.cealeg.shop/robots.txt
```

