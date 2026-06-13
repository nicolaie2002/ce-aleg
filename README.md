# Ce aleg?

Aplicatie Next.js + Flask pentru scanarea produselor, analiza nutritionala,
alternative, conturi, plati si emailuri tranzactionale.

## Arhitectura recomandata

```text
Utilizator
    |
    v
Domeniu + DNS (Cloudflare)
    |
    v
Vercel - frontend Next.js
    |
    | /api/backend/* (proxy same-origin)
    v
Render - backend Flask
    |-- Supabase Postgres: conturi, produse, istoric, cos
    |-- Supabase Storage: imagini si contributii
    |-- Open Food Facts/Open Prices: catalog extern
    |-- Stripe: abonamente si webhook
    `-- Brevo: emailuri tranzactionale
```

Backendul nu este recomandat pe Vercel pentru aceasta aplicatie. Procesarea
imaginilor, uploadurile, rate limiting-ul si serviciile auxiliare se potrivesc
mai bine unui serviciu Flask pe Render.

## Pornire locala

Cu Supabase configurat:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-local.ps1 -Visible
```

Cu SQLite local, inclusiv atunci cand conexiunea Supabase este indisponibila:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-local.ps1 -LocalDatabase -Visible
```

Adrese:

- frontend: `http://localhost:3000`
- backend: `http://127.0.0.1:5001`
- LibreTranslate local: `http://127.0.0.1:5002`

## Verificare

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify-project.ps1 -Smoke
```

## Publicare

Pasii completi, variabilele necesare si verificarile de lansare sunt in
[`docs/go-live-checklist.md`](docs/go-live-checklist.md).
