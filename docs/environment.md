# Inventar de mediu

Inventarul descrie numele, scopul si locul variabilelor, fara valori reale.
Sursele de adevar sunt `render.yaml`, `backend/.env.example`,
`frontend/.env.example` si citirile curente din cod. Secretele se pastreaza numai
in managerul de environment al platformei potrivite si, pentru dezvoltare, in
fisiere `.env` ignorate de Git.

## Medii

| Mediu | Frontend | Backend | Baza de date | Regula |
| --- | --- | --- | --- | --- |
| local | Next.js local | Flask local | Supabase de dezvoltare sau SQLite explicit | nu folosi chei live |
| preview | Vercel Preview | backend de test dedicat, daca exista | proiect Supabase separat recomandat | nu directiona webhook live |
| production | Vercel Production | Render `cealeg-api` | Supabase Postgres productie | numai secrete live si origin-uri publice |

Separarea reala preview/productie trebuie confirmata de proprietar. Daca preview
foloseste baza sau Stripe live, aceasta este o problema de izolare ce trebuie
corectata inainte de a acorda acces altor colaboratori.

## Render / backend obligatoriu in productie

| Variabila | Secret | Scop / regula |
| --- | --- | --- |
| `APP_ENV` | nu | `production`; activeaza validarile stricte |
| `DATABASE_URL` | da | connection string Supabase Postgres; nu folosi SQLite in productie |
| `SUPABASE_URL` | nu | URL proiect Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | da, critic | acces backend la Storage/API; nu ajunge in frontend |
| `AUTH_SECRET` | da, critic | semnare sesiuni si token-uri; unic, aleator, minimum 32 caractere |
| `COOKIE_SECURE` | nu | `true` in productie |
| `FRONTEND_PUBLIC_URL` | nu | URL canonic `https://www.cealeg.shop` |
| `FRONTEND_ORIGINS` | nu | lista exacta de origin-uri HTTPS permise, separate prin virgula |
| `PAYMENT_PROVIDER` | nu | `stripe` cand platile sunt active |
| `STRIPE_SECRET_KEY` | da, critic | cheia server-side pentru acelasi mod test/live ca price ID-urile |
| `STRIPE_WEBHOOK_SECRET` | da, critic | signing secret al endpoint-ului live corect |
| `STRIPE_PRO_PRICE_ID` | nu | pret lunar Pro |
| `STRIPE_PRO_YEARLY_PRICE_ID` | nu | pret anual Pro |
| `STRIPE_FAMILY_PRICE_ID` | nu | pret lunar Family |
| `STRIPE_FAMILY_YEARLY_PRICE_ID` | nu | pret anual Family |
| `STRIPE_CECOINS_BRONZE_PRICE_ID` | nu | plata unica Bronze |
| `STRIPE_CECOINS_GOLD_PRICE_ID` | nu | plata unica Gold |
| `STRIPE_CECOINS_DIAMOND_PRICE_ID` | nu | plata unica Diamond |
| `EMAIL_PROVIDER` | nu | un singur provider: `brevo`, `resend` sau `smtp` |
| `EMAIL_FROM` | nu | expeditor verificat la provider |
| `EMAIL_FROM_NAME` | nu | numele public al expeditorului |
| `CONTACT_EMAIL` | nu | Reply-To si destinatie suport, in prezent `contact@cealeg.shop` |
| `ADMIN_EMAIL` | date de contact | destinatia alertelor administrative |
| `CRON_SECRET` | da, critic | aceeasi valoare in Render si Vercel; protejeaza maintenance |

`render.yaml` marcheaza valorile care trebuie introduse manual cu `sync: false`.
Nu transforma price ID-urile in secrete, dar evita amestecarea obiectelor test si
live.

## Backend: email

Configureaza numai ramura providerului activ.

| Variabila | Secret | Cand este folosita |
| --- | --- | --- |
| `BREVO_API_KEY` | da | `EMAIL_PROVIDER=brevo` |
| `RESEND_API_KEY` | da | `EMAIL_PROVIDER=resend` |
| `EMAIL_SMTP_HOST` | nu | `EMAIL_PROVIDER=smtp` |
| `EMAIL_SMTP_PORT` | nu | port SMTP, implicit 587 |
| `EMAIL_SMTP_USERNAME` | sensibil | autentificare SMTP |
| `EMAIL_SMTP_PASSWORD` | da | autentificare SMTP |
| `EMAIL_USE_TLS` | nu | STARTTLS pentru SMTP |
| `EMAIL_USE_SSL` | nu | TLS implicit pentru SMTP; nu activa simultan fara cerinta providerului |

## Backend: limite, cache si securitate

| Variabila | Valoare implicita in cod/example | Scop |
| --- | --- | --- |
| `FLASK_DEBUG` | `false` | trebuie sa ramana fals in productie |
| `ALLOW_DEV_TUNNEL_ORIGINS` | `false` | nu permite origin-uri de tunel in productie |
| `EXPOSE_DEV_AUTH_LINKS` | `false` | linkuri de verificare/reset numai in dezvoltare explicita |
| `PASSWORD_MIN_LENGTH` | 12 in example; codul impune minimum 10 | politica parole |
| `PASSWORD_RESET_MAX_AGE` | 3600 secunde | expirarea resetarii |
| `EMAIL_VERIFICATION_MAX_AGE` | 48 ore in cod | expirarea confirmarii email |
| `ACCOUNT_DELETE_MAX_AGE` | 24 ore in cod/example | expirarea stergerii contului |
| `GLOBAL_RATE_LIMIT` | 300 local, 180 in blueprint | cereri per fereastra |
| `GLOBAL_RATE_LIMIT_WINDOW` | 60 secunde | fereastra limitei globale |
| `AUTH_RATE_LIMIT` | 5 | incercari pe rutele auth |
| `AUTH_RATE_LIMIT_WINDOW` | 900 secunde | fereastra auth |
| `MAX_JSON_BODY_BYTES` | 204800 local, 1048576 in blueprint | limita JSON; armonizeaza deliberat valorile |
| `MAX_UPLOAD_MB` | 8 | limita request-urilor cu fisiere |
| `MAX_IMAGE_PIXELS` | 24000000 | protectie la imagini foarte mari |
| `SUBMISSION_DAILY_LIMIT` | 10 | contributii pe utilizator/zi |
| `SUBMISSION_PENDING_LIMIT` | 20 | contributii in asteptare per utilizator |
| `FREE_MONTHLY_SCAN_LIMIT` | 5 | limita planului Free |
| `FREE_WEEKLY_SCAN_LIMIT` | compatibilitate legacy | fallback daca limita lunara lipseste |
| `INVITE_BONUS_DAYS` | 2 | configurare gamification legacy |
| `SUBMISSION_APPROVAL_BONUS_CREDITS` | 1 | credite bonus legacy |
| `SUBMISSION_APPROVAL_CECOINS` | 10 | recompensa pentru produs aprobat |

## Backend: performanta si servicii optionale

| Variabila | Secret | Scop |
| --- | --- | --- |
| `REDIS_URL` | da | rate limit/cache distribuit cand Redis este configurat |
| `LOG_LEVEL` | nu | nivel logging, de regula `INFO` |
| `LOG_FORMAT` | nu | `json` recomandat in productie |
| `OPEN_FOOD_FACTS_CACHE_MAX_ITEMS` | nu | limita cache produs OFF |
| `OPEN_PRICES_CACHE_MAX_ITEMS` | nu | limita cache preturi |
| `PRODUCT_SEARCH_RESULT_CACHE_TTL` | nu | TTL cautari produse |
| `PRODUCT_SEARCH_RESULT_CACHE_MAX_ITEMS` | nu | dimensiune cache cautari |
| `LEADERBOARD_CACHE_TTL` | nu | TTL clasament |
| `PUBLIC_CATALOG_STATS_CACHE_TTL` | nu | TTL statistici publice |
| `RECOMMENDATION_DERIVED_CACHE_MAX_ITEMS` | nu | limita cache recomandari |
| `MAX_IMPORT_SOURCE_MB` | nu | limita fisierului sursa pentru import export |
| `SUPABASE_PRODUCT_IMAGES_BUCKET` | nu | bucket imagini produs; implicit `product-images` |
| `SUPABASE_SUBMISSIONS_BUCKET` | nu | bucket contributii; implicit `product-submissions` |
| `ENABLE_OPENAI_VISION` | nu | functie optionala; `false` fara buget/configurare |
| `OPENAI_API_KEY` | da | numai daca Vision este activ |
| `OPENAI_VISION_MODEL` | nu | modelul aprobat pentru Vision |
| `LIBRETRANSLATE_URL` | nu | serviciu extern/local optional de traducere |

Variabilele `PORT`, `RENDER_GIT_COMMIT` si `RENDER_DEPLOY_CREATED_AT` sunt
injectate de Render. `GIT_COMMIT`, `COMMIT_SHA`, `SOURCE_VERSION`, `BUILD_TIME`
si `VERCEL_GIT_COMMIT_SHA` sunt fallback-uri optionale pentru `/version`.

## Stripe: compatibilitate si taxe

| Variabila | Observatie |
| --- | --- |
| `STRIPE_AUTOMATIC_TAX` | activeaza doar dupa configurarea fiscala verificata |
| `STRIPE_TAX_ID_COLLECTION` | activeaza doar dupa decizie fiscala verificata |
| `STRIPE_CECOINS_STARTER_PRICE_ID` | nume legacy pentru Bronze; prefera numele curent |
| `STRIPE_CECOINS_BOOST_PRICE_ID` | nume legacy pentru Gold; prefera numele curent |
| `STRIPE_CECOINS_POWER_PRICE_ID` | nume legacy pentru Diamond; prefera numele curent |

## Vercel / frontend server-side

| Variabila | Secret | Scop |
| --- | --- | --- |
| `BACKEND_URL` | nu | URL intern/public al backend-ului Render, fara slash final |
| `NEXT_PUBLIC_API_URL` | nu, public | `/api/backend` pentru proxy same-origin |
| `CRON_SECRET` | da, critic | aceeasi valoare ca in Render; nu prefixa manual cu numele variabilei |
| `SENTRY_DSN` | sensibil operational | DSN server/edge, daca Sentry este activ |
| `SENTRY_ORG` | nu | organizatia Sentry pentru upload sourcemap |
| `SENTRY_PROJECT` | nu | proiectul Sentry |
| `SENTRY_AUTH_TOKEN` | da, critic | build-only pentru sourcemaps; nu devine `NEXT_PUBLIC_*` |

Vercel injecteaza `NODE_ENV`, `VERCEL_ENV`, `PORT` si `NEXT_RUNTIME` unde sunt
relevante. `CI` este folosita in pipeline, nu se seteaza manual in productie.

## Frontend public

Orice variabila `NEXT_PUBLIC_*` ajunge in bundle-ul browserului si nu poate fi
considerata secret.

| Variabila | Scop |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | baza API utilizata de client |
| `NEXT_PUBLIC_SITE_URL` | URL canonic, daca este configurat |
| `NEXT_PUBLIC_APP_ENV` | eticheta mediului |
| `NEXT_PUBLIC_APP_VERSION` | versiune/release pentru diagnostic |
| `NEXT_PUBLIC_SENTRY_DSN` | DSN browser Sentry; nu este credential de administrare |
| `NEXT_PUBLIC_GA_ID` | Google Analytics, numai cu decizie si consimtamant aplicabil |
| `NEXT_PUBLIC_META_PIXEL_ID` | Meta Pixel, numai cu decizie si consimtamant aplicabil |
| `NEXT_PUBLIC_TIKTOK_PIXEL_ID` | TikTok Pixel, numai cu decizie si consimtamant aplicabil |

Lasarea unui ID analytics gol trebuie sa dezactiveze integrarea. Prezenta unui ID
nu inlocuieste configurarea bannerului, politicii de confidentialitate si a
consimtamantului.

## Matrice de secrete si rotire

| Secret | Locatii | Dupa rotire |
| --- | --- | --- |
| `AUTH_SECRET` | Render | toate sesiunile/token-urile existente devin invalide; testeaza login/reset |
| `DATABASE_URL` | Render, statie operator autorizata temporar | testeaza conectarea, health si o citire/scriere controlata |
| `SUPABASE_SERVICE_ROLE_KEY` | Render | actualizeaza imediat backend-ul si testeaza Storage |
| Stripe secret/webhook | Render + Stripe | testeaza Checkout, portal si un eveniment semnat |
| cheia provider email | Render + provider | trimite email test si verifica provider message ID |
| `CRON_SECRET` | Render + Vercel | actualizeaza ambele parti in aceeasi fereastra si testeaza cron |
| `REDIS_URL` | Render | testeaza rate limiting si fallback-ul |
| `OPENAI_API_KEY` | Render | testeaza numai daca functia este activata |
| `SENTRY_AUTH_TOKEN` | Vercel | ruleaza build si confirma sourcemap upload fara a expune token-ul |

Rotirea trebuie jurnalizata fara a copia valoarea. Pentru un secret suspectat
compromis, urmeaza [runbooks/security-incident.md](runbooks/security-incident.md).

## Verificare fara expunerea valorilor

In dashboard-uri, confirma doar prezenta, mediul si data ultimei modificari. Nu
folosi comenzi care tiparesc toate variabilele in log. Local, fisierele example pot
fi comparate dupa nume, iar valorile reale se verifica individual si mascat.

Checklist productie:

1. Nu exista chei test Stripe impreuna cu price ID-uri live sau invers.
2. `CRON_SECRET` este identic in Vercel si Render.
3. `FRONTEND_ORIGINS` nu contine localhost sau tuneluri de dezvoltare.
4. `SUPABASE_SERVICE_ROLE_KEY`, `AUTH_SECRET` si cheile API nu au prefix
   `NEXT_PUBLIC_`.
5. Providerul email activ are expeditorul verificat.
6. Variabilele Preview nu folosesc date sau plati live, daca mediul Preview exista.
7. Valorile eliminate sunt sterse si din medii vechi/preview, nu doar din Production.

## De completat de proprietar

- separarea exacta a mediilor si proiectele externe asociate;
- regiunea Render si Supabase;
- planurile active, limitele si persoanele cu acces;
- politica si calendarul de rotire;
- ID-urile externe, pastrate intr-un registru privat;
- decizia privind Redis, Sentry, analytics, OpenAI si LibreTranslate;
- armonizarea deliberata a `MAX_JSON_BODY_BYTES` dintre example si `render.yaml`.
