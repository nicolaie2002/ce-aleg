# Backup Supabase pentru Ce aleg?

Ultima actualizare: 4 iulie 2026

Scop: să avem o copie recuperabilă a bazei de date dacă se strică o migrare, se șterg date greșit sau apare o problemă la provider.

## Ce trebuie salvat

- baza Postgres: utilizatori, produse, coșuri, favorite, istoric, abonamente, misiuni, CeCoins
- fișierele din Supabase Storage: imagini produse și contribuții
- variabilele de mediu: nu se pun în Git; se păstrează separat, într-un manager de parole

## Recomandare

- Dacă planul Supabase permite backup/PITR, activează backup-ul din dashboard.
- Chiar dacă există backup la provider, fă export manual înainte de modificări mari: migrare, import masiv, schimbări la abonamente sau gamification.
- Păstrează minimum 3 copii recente: ultima zi, ultima săptămână, ultima lună.

## Export manual Postgres pe Windows

Rulează din PowerShell, cu `DATABASE_URL` setat în sesiune. Nu lipi cheia în Git sau în screenshot-uri publice.

```powershell
cd D:\proiecte\ce_aleg
New-Item -ItemType Directory -Force backups
$stamp = Get-Date -Format "yyyyMMdd-HHmm"
pg_dump "$env:DATABASE_URL" --format=custom --no-owner --no-acl --file "backups\cealeg-$stamp.dump"
```

Dacă `pg_dump` nu există, instalează PostgreSQL client tools sau folosește terminalul oferit de provider.

## Verificare backup

Un backup care nu poate fi restaurat nu este backup. Testează periodic restaurarea într-o bază separată, niciodată peste producție.

```powershell
pg_restore --list "backups\cealeg-YYYYMMDD-HHMM.dump" | Select-Object -First 20
```

## Restaurare într-o bază de test

```powershell
createdb cealeg_restore_test
pg_restore --dbname cealeg_restore_test --no-owner --no-acl "backups\cealeg-YYYYMMDD-HHMM.dump"
```

## Supabase Storage

Pentru imaginile din bucket-uri:

- `product-images`
- `product-submissions`

Exportă periodic fișierele prin dashboard, CLI sau script separat. Nu șterge imaginile vechi până nu confirmi că produsele încă au imagini valide.

## Când facem backup obligatoriu

- înainte de importuri mari de produse
- înainte de modificări la schema bazei de date
- înainte de schimbări la Stripe/webhook/subscription logic
- înainte de ștergeri sau curățări automate
- înainte de lansări majore de funcții

## Note de securitate

- Backup-urile pot conține date personale; nu le urca pe GitHub.
- Păstrează backup-urile local criptat sau într-un storage securizat.
- Accesul la backup-uri trebuie limitat doar la administrator.
- Dacă un backup ajunge public accidental, tratează situația ca incident de securitate.

## Referințe utile

- Supabase database backups: https://supabase.com/docs/guides/platform/backups
- Supabase CLI: https://supabase.com/docs/reference/cli/introduction
- PostgreSQL pg_dump: https://www.postgresql.org/docs/current/app-pgdump.html
