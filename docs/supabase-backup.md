# Backup Supabase pentru Ce aleg?

Ultima actualizare: 17 iulie 2026

## Strategie fara cost suplimentar

Supabase recomanda proiectelor Free sa exporte regulat datele. Backupul automat al
bazei nu include obiectele din Storage, de aceea jobul nostru salveaza separat:

- un dump logic PostgreSQL in format custom;
- obiectele din `product-images` si `product-submissions`;
- manifestul dumpului si checksum SHA-256 pentru fiecare fisier;
- o arhiva criptata AES-256, pastrata ca artifact privat GitHub timp de 30 zile.

Workflow-ul este `.github/workflows/backup.yml` si ruleaza zilnic la 02:17 UTC.
Foloseste numai GitHub Actions si exporturile Supabase disponibile pe planul Free.
Nu activam PITR sau add-on-uri platite.

## Secrete GitHub necesare

- `BACKUP_DATABASE_URL`: conexiune directa sau session pooler, nu transaction pooler;
- `SUPABASE_URL`;
- `SUPABASE_SERVICE_ROLE_KEY`;
- `BACKUP_ENCRYPTION_KEY`: parola lunga, diferita de celelalte secrete.

Valorile se configureaza in GitHub Actions Secrets si nu se pun in repository,
loguri, issue-uri sau capturi de ecran.

## Crearea payloadului

Workflow-ul apeleaza:

```bash
bash scripts/backup-supabase.sh backup
```

Scriptul refuza sa suprascrie un dump existent. Foloseste clientul PostgreSQL
local sau, in GitHub Actions, imaginea gratuita `postgres:17-alpine`.

## Validare si restaurare

Descarca arhiva si fisierul `.sha256` dintr-un run reusit. Verifica mai intai
checksumul arhivei, apoi ruleaza validarea fara scrieri:

```bash
sha256sum --check cealeg-backup.tar.gz.enc.sha256
export BACKUP_ENCRYPTION_KEY='valoarea-din-managerul-de-parole'
bash scripts/restore-supabase.sh cealeg-backup.tar.gz.enc
```

Dry-run-ul decripteaza intr-un director temporar, blocheaza cai periculoase,
verifica toate checksumurile si inspecteaza dumpul cu `pg_restore --list`.

Aplicarea este permisa numai pe o baza separata si necesita toate garzile:

```bash
export RESTORE_TEST_DATABASE_URL='postgresql://...baza-de-test...'
export RESTORE_TARGET_LABEL='quarterly-restore-test'
export RESTORE_CONFIRM_DISPOSABLE_TARGET='YES_I_UNDERSTAND'
bash scripts/restore-supabase.sh cealeg-backup.tar.gz.enc --apply
```

Pentru Storage pe proiectul de test se adauga
`RESTORE_SUPABASE_URL` si `RESTORE_SUPABASE_SERVICE_ROLE_KEY`. Scriptul refuza
o adresa de restaurare identica cu `DATABASE_URL` sau `BACKUP_DATABASE_URL`.

## Frecventa verificarii

- zilnic: confirma ca workflow-ul s-a terminat cu succes;
- lunar: valideaza o arhiva prin dry-run;
- trimestrial: restaureaza intr-un proiect/baza disposable si ruleaza smoke tests;
- inainte de importuri sau migrari mari: confirma un backup recent.

Un artifact existent nu dovedeste recuperarea. Dovada finala este un restore drill
reusit, consemnat privat cu run ID, data, durata si rezultatele verificarilor.

## Limite importante

- artifactele GitHub sunt separate de Supabase, dar au cote de stocare; verifica
  periodic ca jobul nu a fost oprit de cota planului gratuit;
- stergerea proiectului Supabase este ireversibila si poate elimina backupurile
  pastrate de provider;
- rolurile/parolele custom si anumite setari trebuie verificate separat dupa restore;
- fisierele decriptate contin date personale si trebuie sterse dupa test.

Referinte oficiale:

- <https://supabase.com/docs/guides/platform/backups>
- <https://supabase.com/docs/reference/cli/supabase-db-dump>
- <https://www.postgresql.org/docs/current/app-pgdump.html>
