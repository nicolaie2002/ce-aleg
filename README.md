# Ce aleg?

### AI Shopping Assistant for smarter food choices

[Live Website](https://www.cealeg.shop)

Ce aleg? este o platforma de tip AI Shopping Assistant care ajuta utilizatorii sa ia decizii mai informate atunci cand cumpara produse alimentare.

Utilizatorii pot scana un cod de bare, cauta un produs sau trimite o imagine pentru a obtine informatii despre produs, analiza nutritionala si ingrediente, precum si alternative mai potrivite in functie de preferintele lor.

## Features

- 📷 Scanare produse prin cod de bare
- 🔎 Cautare si identificare produse
- 🤖 Analiza asistata de AI
- 🥗 Analiza ingredientelor si valorilor nutritionale
- 🔄 Recomandari si alternative pentru produse
- 👤 Conturi si preferinte personalizate
- ⭐ Favorite si istoric
- 🛒 Cos si functionalitati de shopping
- 💳 Abonamente si plati prin Stripe
- 📧 Emailuri tranzactionale
- 🌍 Suport pentru mai multe limbi
- 🔐 Autentificare si protectia conturilor

## Tech Stack

### Frontend
- Next.js
- React
- JavaScript / TypeScript
- CSS
- Jest
- Playwright

### Backend
- Python
- Flask
- REST API
- SQLAlchemy
- Marshmallow

### Database & Storage
- PostgreSQL
- Supabase
- Supabase Storage

### Integrations
- OpenAI API
- Stripe
- Brevo
- Open Food Facts
- Open Prices
- LibreTranslate
- Sentry

### Deployment
- Vercel
- Render
- Cloudflare

## Architecture

```text
User
 │
 ▼
Next.js Frontend
 │
 ▼
Flask REST API
 │
 ├── PostgreSQL / Supabase
 ├── Supabase Storage
 ├── Open Food Facts / Open Prices
 ├── OpenAI
 ├── Stripe
 └── Brevo
