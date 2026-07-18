# Ce aleg? - handoff proiect

Ultima actualizare: 2026-07-18

## Stare curenta

- Portile locale sunt verzi: backend 357 teste si 73,13% coverage pentru `app.py`;
  frontend 71 teste Jest; Playwright 32 trecute, 10 skip
  intentionat si zero esecuri.
- PWA foloseste un service worker static, fara cache pentru API/date private;
  offline-ul este verificat desktop si mobil.
- Render Key Value free este configurat pentru rate limit/cache distribuit.
- Maintenance ruleaza gratuit din GitHub Actions; `CRON_SECRET` a fost adaugat in
  repository Actions secrets cu aceeasi valoare din Render.
- Render este configurat `checksPass`: dupa ce workflow-ul `CI` trece, publica
  automat commitul. Deploy hook-ul GitHub ramane doar fallback manual optional si
  verifica apoi commitul din `/version`.
- Configuratia OpenNext/Cloudflare Workers Free este pregatita, dar nu se face
  deploy pana cand jobul Linux este verde si proprietarul conecteaza domeniul.
- Emailurile live au fost raportate nefunctionale si raman blocant extern. Nu
  considera vechile mentiuni `Brevo OK` drept dovada curenta.
- Detaliile si cifrele authoritative sunt in
  `docs/production-improvement-report.md`; sectiunile de mai jos pastreaza si
  istoricul implementarilor anterioare.

Pachetul curent a adaugat warm-up pentru reducerea cold start-ului si a reparat smoke-ul pentru email verification:

- Frontend: `frontend/app/components/BackendWarmup.js`
- Frontend: `frontend/app/api/cron/warmup/route.js`
- Config Vercel: `frontend/vercel.json`
- Script: `scripts/smoke-test.ps1`
- Layout-ul face un ping oportunist catre `/api/backend/health`, cu cooldown local de 10 minute, ca backend-ul Render sa fie trezit inainte de scanare.
- Cron-ul Vercel are o ruta separata `/api/cron/warmup`, protejata cu `CRON_SECRET`, programata zilnic pentru compatibilitate cu limita Hobby.
- Smoke test-ul complet trateaza corect conturile nou create care raman pending pana la confirmarea emailului; in productie, `email_not_verified` este acum rezultat asteptat, nu fail fals.

Pachetul curent a adaugat polish mobil si notificari pentru produse corectate:

- Frontend: `frontend/app/dashboard/page.js`
- Frontend: `frontend/app/barcode-scan/page.js`
- Frontend: `frontend/app/scan/page.js`
- Frontend: `frontend/app/admin/page.js`
- Backend: `backend/app.py`
- Dashboard-ul mobil are acum actiuni principale clare pentru scanare/cautare si sumar compact pentru misiuni.
- Flow-ul `Produs negasit` este prezentat ca `Produs nou in Romania?`, cu confirmarea codului si mesajul de CeCoins.
- Admin-ul poate bifa anuntarea utilizatorilor cand corecteaza un produs; backend-ul trimite email doar utilizatorilor relevanti, cu cooldown anti-dublare.

Pachetul curent a adaugat editare rapida de produse in admin:

- Backend: `GET /admin/products/search`
- Backend: `PATCH /admin/products/<product_id>`
- Frontend: `frontend/app/admin/page.js`
- Admin-ul poate cauta produse dupa nume, cod de bare, categorie sau magazin, apoi poate corecta rapid numele, barcode-ul, magazinul, categoria, valorile nutritionale, ingredientele si flagurile.
- Salvarea cu recalculare aplica taxonomia curenta si regenereaza scorul, eticheta si motivul produsului.
- Smoke test-ul verifica acum ca search/update pentru admin products sunt blocate fara autentificare.

Pachetul curent a adaugat import targetat Open Food Facts pentru Romania:

- Backend script: `backend/prewarm_openfoodfacts_catalog.py`
- Wrapper: `scripts/prewarm-romania-focus.ps1`
- Preset nou: `romania_focus`, cu lactate, mezeluri, bere, dulciuri, conserve, sosuri, produse de baza, congelate si categorii private-label/retail.
- Implicit ruleaza dry-run. Pentru import real: `.\scripts\prewarm-romania-focus.ps1 -Apply`.
- Pentru rezultate mai multe, fara filtru strict de tara: `.\scripts\prewarm-romania-focus.ps1 -WorldFallback -Apply`.
- Pentru lot scurt: `.\scripts\prewarm-romania-focus.ps1 -Categories "en:yogurts,en:cold-cuts" -LimitPerCategory 20 -Apply`.

Pachetul curent a adaugat automatizare cron pentru mentenanta:

- Frontend: `frontend/app/api/cron/maintenance/route.js`
- Workflow: `.github/workflows/maintenance.yml`
- Backend: `POST /internal/cron/maintenance`
- GitHub Actions ruleaza zilnic la `04:20 UTC`, verifica `CRON_SECRET`, apoi cheama direct backend-ul cu acelasi secret. Vercel pastreaza numai warm-up-ul programat, pentru a evita o executie dubla.
- Mentenanta recategorizeaza automat un batch de produse `Altele` dintr-o zona diferita a catalogului in fiecare zi si trimite digest-ul de misiuni aproape gata cu cooldown-ul existent de 6 zile.
- Backend-ul foloseste un lock Redis, cu fallback local, si returneaza `runId`, durate si avertismente. Pentru activare, aceeasi valoare `CRON_SECRET` trebuie setata in GitHub Actions si Render; Vercel o foloseste numai pentru ruta protejata de warm-up/manual maintenance.

Pachetul curent a adaugat digest admin pentru misiuni aproape gata:

- Backend: `GET/POST /admin/missions/digest`
- Frontend: `frontend/app/admin/page.js`
- Admin-ul poate rula preview pentru utilizatorii cu misiuni peste 60% progres si poate trimite email branded catre `/missions`.
- Fiecare user are cooldown de 6 zile prin evenimentul `mission_digest_email`, ca sa nu primeasca spam.
- Smoke test-ul verifica acum si ca endpoint-ul digest este blocat fara autentificare.

Pachetul curent a imbunatatit recategorizarea catalogului din admin:

- Backend: `backend/app.py`
- Frontend: `frontend/app/admin/page.js`
- Endpoint-ul `GET/POST /admin/catalog/recategorize` intoarce acum `lastScannedId`, `nextMinId` si `hasMore`.
- Pagina admin poate continua cu "Urmatorul batch", astfel incat produsele `Altele` care nu pot fi reparate automat nu mai blocheaza verificarea restului de catalog.
- Recategorizarea ramane limitata la 500 de produse per batch, pentru a evita request-uri lungi pe Render.

## Pe scurt

Ce aleg? este o aplicație web publică pentru scanarea produselor alimentare, afișarea unui verdict orientativ și recomandarea de alternative mai potrivite după categorie, preferințe și criterii precum zahăr mai puțin, proteină mai multă, preț mai bun sau altă aromă.

## Goal

Obiectivul proiectului este să lansăm și să creștem `Ce aleg?` ca un asistent de cumpărături pentru România, rapid și ușor de folosit pe telefon, care ajută utilizatorii să scaneze produse la raft, să înțeleagă rapid eticheta și să aleagă alternative mai potrivite. Produsul trebuie să fie suficient de stabil pentru trafic public, plăți reale, conturi reale și promovare pe TikTok/Google, cu accent pe:

- scanare coduri de bare cât mai rapidă și precisă;
- catalog mare și relevant pentru produse din România;
- alternative corecte în aceeași familie de produs, nu recomandări fără sens;
- monetizare prin Pro, Family, CeCoins și bonusuri/recompense;
- protecție cont, plăți, emailuri, privacy/terms și admin pentru monitorizare;
- experiență mobilă fluidă, clară și profesională.

Site public: https://www.cealeg.shop  
Frontend Vercel: https://ce-aleg.vercel.app  
Backend Render: https://cealeg-api.onrender.com  
Contact public: contact@cealeg.shop

## Arhitectură

```text
Utilizator
  -> Vercel / Next.js frontend
  -> proxy API frontend / api/backend
  -> Render / Flask backend
  -> Supabase Postgres + Storage
  -> Stripe pentru plăți și abonamente
  -> Brevo pentru emailuri tranzacționale
  -> Open Food Facts + catalog propriu pentru date produs
```

## Status general

- Site-ul este public pe `www.cealeg.shop`.
- DNS-ul pentru `cealeg.shop` și `www.cealeg.shop` este configurat în Vercel.
- Sitemap-ul a fost trimis în Google Search Console.
- Stripe este trecut pe live și plățile reale au fost testate.
- Brevo este configurat, domeniul are înregistrările verificate, iar `contact@cealeg.shop` redirecționează corect.
- Catalogul are 61.254 produse importate și validate în producție, conform endpoint-ului public de statistici.
- Asistentul AI vizual real este marcat ca indisponibil / în dezvoltare, deoarece nu folosim momentan OpenAI Vision cu plată.
- Fluxul principal se bazează pe barcode, OCR/căutare text și catalog.

## Ce funcționează

- Înregistrare cont, login, resetare parolă, verificare email.
- Ștergere cont cu confirmare email.
- Scanare cod de bare și căutare produs.
- Rezultat produs cu scor și valori nutriționale.
- Alternative după criterii.
- Coș, favorite, istoric.
- Planuri Free / Pro / Family.
- Stripe Checkout, Stripe Customer Portal și webhook pentru planuri.
- CeCoins, misiuni, recompense și pachete Bronze / Gold / Diamond.
- Pagină publică `Catalog România` cu statistici live despre catalog, lipsuri pe magazine și contribuții comunitare.
- Admin cu monitorizare, căutare utilizatori după email, stare sistem și rezolvare rapidă pentru alternative raportate.
- Raportare alternative greșite.
- Emailuri tranzacționale prin Brevo.
- Privacy, Terms, Support și documente de go-live.

## Schimbări recente importante

Ultimul pachet de lucru a făcut flow-ul de contribuție mai clar pe mobil:

- Frontend: `frontend/app/submit-product/page.js`
- Pe `/submit-product`, pozele pentru fața produsului și tabelul nutrițional sunt acum sus, înainte de OCR și înaintea câmpurilor lungi.
- Flow-ul afișează pașii rapizi: cod verificat, poză față produs, poză tabel nutrițional.
- Butonul final folosește textul `Trimite la verificare` și amintește recompensa de 10 CeCoins după aprobare.

Pachetul anterior a adăugat streak-uri pentru retenție în misiuni:

- Backend: `backend/app.py`
- Frontend: `frontend/app/missions/page.js`
- Misiunea nouă `streak_3` se calculează din zile consecutive cu scanări reale sau istoric de scanare.
- Recompensa este 35 CeCoins + 1 scanare bonus, revendicabilă o singură dată pentru prag.
- Pagina `/missions` afișează streak-ul ca indicator rapid, util mai ales pe mobil.

Pachetul anterior a îmbunătățit admin-ul pentru calitatea recomandărilor:

- Backend: `POST /admin/alternative-reports/<event_id>/resolve`
- Frontend: `frontend/app/admin/page.js`
- Admin-ul afișează alternativele raportate direct în zona de semnale, cu produs scanat, alternativă, utilizator, magazin și dată.
- Administratorul poate rula auto-fix pe raportare sau poate aplica manual categoria corectă; produsul primește scor/tag/reason recalculat.
- Raportarea salvează `adminReview` în metadata și eveniment separat `alternative_report_resolved`.

Pachetul anterior a curățat dashboard-ul și a adăugat onboarding mobil:

- Frontend: `frontend/app/dashboard/page.js`
- Frontend: `frontend/app/onboarding/page.js`
- Dashboard-ul nu mai dublează pagina `/missions`; afișează doar sumarul CeCoins/progres și trimite spre pagina dedicată.
- După confirmarea emailului, utilizatorul nou ajunge în onboarding-ul de 3 pași: magazin, scanare, produs lipsă cu CeCoins.
- `/onboarding` este neindexat în `robots`, dar public, ca să nu depindă de timing-ul sesiunii imediat după confirmare.

Pachetul anterior a adăugat pagina publică `Catalog România`:

- Frontend: `frontend/app/catalog-romania/page.js`
- Backend: `GET /catalog/romania/stats`
- Pagina afișează produse totale, acoperire coduri de bare/nutriție/imagini, categorii, magazine, lipsuri recente, top contribuitori și produse aprobate recent.
- Link-uri adăugate în homepage, header desktop și acțiunile rapide din dashboard.
- Endpoint-ul public folosește cache de 5 minute și nu expune emailuri sau date sensibile.

Pachetul anterior a optimizat scannerul de coduri de bare:

- Frontend: `frontend/app/barcode-scan/page.js`
- Scannerul confirmă codul din mai multe citiri stabile înainte să facă lookup.
- S-au redus formatele citite la cele relevante pentru produse de supermarket: `EAN-13`, `EAN-8`, `UPC-A`, `ITF`.
- Codurile invalide sunt respinse local prin checksum GS1 înainte să ajungă la backend.
- S-a adăugat cooldown pentru același cod și protecție împotriva lookup-urilor duplicate.
- Detectorul nativ este throttled ca să nu proceseze inutil fiecare frame pe telefoane slabe.
- Fallback-ul ZXing/OCR folosește aceeași logică de confirmare.

Pachetul anterior a extins masiv taxonomia pentru recomandări:

- Backend: `backend/app.py`
- Frontend: `frontend/app/alternatives/page.js`

S-au adăugat familii detaliate pentru:

- energizante, energizante zero, shot-uri, cola zero/clasic;
- cafea rece, cafea boabe, ceaiuri, sucuri, nectaruri, limonade, ape;
- bere lager, radler, fără alcool, brună, nefiltrată;
- iaurturi, kefir, budinci, lapte, băuturi vegetale, brânzeturi;
- ramen, cup noodles, Buldak/Samyang;
- mezeluri, carne, pește, conserve;
- snacks, chipsuri, biscuiți, ciocolată, patiserie;
- sosuri, condimente, muștar, maioneză, uleiuri;
- panificație, paste, orez, făină, conserve, congelate;
- baby food, produse proteice și spread-uri.

S-a adăugat criteriul `altă aromă`, folosit și când utilizatorul scrie cereri de tip:

- `altă aromă`
- `alt gust`
- `gust diferit`
- `alt sortiment`
- `altă variantă`

Exemple testate manual în backend:

- `Red Bull Zero fara zahar` -> `zero_energy_drink`
- `Hell Ice Coffee Cappuccino` -> `coffee_drink`
- `Ursus Premium bere blonda` -> `lager_beer`
- `Danette vanilie` -> `pudding`
- `Buldak Hot Chicken Ramen` -> `ramen_noodles`
- `Cup noodles chicken` -> `cup_noodles`
- `Muschi file afumat` -> `ham`
- `Lidl iaurt cu capsuni` -> `fruit_yogurt`
- `Chunky salsa mild` -> `salsa_sauce`
- `Lapte fara lactoza 1.5%` -> `lactose_free_milk`

## Verificări recente

Au trecut:

```powershell
cd D:\proiecte\ce_aleg\backend
.\venv\Scripts\python.exe -m py_compile app.py
```

```powershell
cd D:\proiecte\ce_aleg\frontend
npm.cmd run lint
npm.cmd run build
```

Observație: o verificare rapidă a readiness-ului public pe `https://www.cealeg.shop/api/backend/readiness` a dat timeout la 15 secunde. Cel mai probabil este cold start / latență Render. Pentru trafic real, acesta rămâne un risc.

## Probleme cunoscute / riscuri

1. Render pe plan gratuit poate avea cold start și poate pica health check-ul dacă backend-ul pornește lent.
2. Asistentul live nu are încă identificare vizuală reală prin AI. Este corect să fie prezentat ca funcție în dezvoltare sau limitat la barcode/OCR.
3. Alternativele depind de calitatea catalogului. Taxonomia a fost îmbunătățită, dar trebuie urmărite în admin alternativele raportate ca greșite.
4. Pentru recomandări foarte bune pe România, încă avem nevoie de date oficiale de la retaileri.
5. Google poate întârzia actualizarea titlului, descrierii și imaginii în Search. Modificările SEO nu apar imediat.
6. Dacă se schimbă price ID-urile Stripe, trebuie actualizate variabilele din Render.

## Ce trebuie urmărit în admin după lansare

- Produse negăsite.
- Scanări eșuate sau coduri citite greșit.
- Alternative raportate ca nepotrivite.
- Produse fără categorie sau cu categoria `Altele`.
- Plăți Stripe eșuate.
- Webhook-uri Stripe nelivrate.
- Emailuri Brevo eșuate.
- Erori backend Render.
- Timp de răspuns mare la API.

## Ce mai merită lucrat

Prioritate mare:

- Reducerea cold start-ului sau trecerea backend-ului pe un plan mai stabil dacă începe reclama.
- Dashboard admin pentru corectare rapidă a produselor raportate.
- Job periodic care recalculează categoria produselor cu `Altele`.
- Reguli suplimentare pentru categorii din România: brânzeturi locale, mezeluri, conserve, dulciuri românești, bere, lactate, produse Lidl/Kaufland/Carrefour.
- Export periodic Supabase.
- Logging mai clar pentru scanări eșuate și alternative respinse.

Prioritate medie:

- Mai multe template-uri profesionale pentru emailuri.
- Flow de onboarding pentru preferințe alimentare.
- Leaderboard mai vizibil pentru CeCoins.
- Sistem de notificări pentru produse corectate după raportare.
- Texte de marketing pentru TikTok/Meta Ads.

Prioritate mică:

- Identificare vizuală cu AI real, după ce există buget pentru API.
- Parteneriate affiliate sau marketplace.
- Integrare cu retaileri prin feed/API.

## Variabile importante în cloud

Nu pune valori secrete în repo. Verifică doar că există în Render/Vercel:

Backend Render:

- `APP_ENV=production`
- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRO_PRICE_ID`
- `STRIPE_FAMILY_PRICE_ID`
- price ID-uri lunare/anuale dacă sunt folosite separat
- price ID-uri CeCoins Bronze / Gold / Diamond
- `BREVO_API_KEY`
- `EMAIL_PROVIDER=brevo`
- `EMAIL_FROM=contact@cealeg.shop`
- `EMAIL_FROM_NAME=Ce aleg?`
- `CRON_SECRET`
- `FRONTEND_PUBLIC_URL=https://www.cealeg.shop`
- `FRONTEND_ORIGINS=https://www.cealeg.shop,https://ce-aleg.vercel.app`
- `COOKIE_SECURE=true`

Frontend Vercel:

- `NEXT_PUBLIC_API_URL`
- `BACKEND_URL`
- `CRON_SECRET` cu aceeasi valoare ca in Render
- `NEXT_PUBLIC_GA_ID` dacă Analytics este activ
- `NEXT_PUBLIC_META_PIXEL_ID` dacă Meta Ads este activ
- `NEXT_PUBLIC_TIKTOK_PIXEL_ID` dacă TikTok Ads este activ

## Comenzi utile

Pornire locală:

```powershell
cd D:\proiecte\ce_aleg
.\scripts\start-local.ps1 -SkipTranslate
```

Test backend:

```powershell
cd D:\proiecte\ce_aleg\backend
.\venv\Scripts\python.exe -m py_compile app.py
```

Test frontend:

```powershell
cd D:\proiecte\ce_aleg\frontend
npm.cmd run lint
npm.cmd run build
```

Deploy:

- Commit + push pe `main`.
- Vercel redeploy automat pentru frontend.
- Render redeploy automat / blueprint sync pentru backend.

## Notă pentru următoarea fereastră Codex

Începe prin:

```powershell
cd D:\proiecte\ce_aleg
git status --short
git log -3 --oneline
```

Apoi verifică:

- dacă Render a terminat deploy-ul;
- dacă `/api/backend/readiness` răspunde rapid;
- dacă pachetele CeCoins încă pornesc corect checkout-ul;
- dacă alternativele pentru `Buldak`, `Ursus`, `Hell Ice Coffee`, `iaurt Zuzu`, `mușchi file` sunt în familii corecte.
