# Disaster recovery

The scheduled GitHub workflow creates a logical PostgreSQL dump plus copies of the two Supabase Storage buckets. The archive is encrypted before it is uploaded and is retained for 30 days.

## Required GitHub secrets

- `BACKUP_DATABASE_URL`: a Supabase session-pooler or direct `postgresql://` connection string.
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `BACKUP_ENCRYPTION_KEY`: a long independent passphrase stored only in the password manager and GitHub Actions.

Never use the public/publishable key for this job. Never place these values in repository files.

## Restore drill

1. Download one encrypted artifact from a completed `Encrypted production backup` run.
2. Decrypt it in a temporary restricted directory:

   `openssl enc -d -aes-256-cbc -pbkdf2 -in cealeg-backup.tar.gz.enc -pass env:BACKUP_ENCRYPTION_KEY | tar -xzf -`

3. Verify the dump with `pg_restore --list database/cealeg.dump`.
4. Restore only into a disposable Supabase project: `pg_restore --clean --if-exists --no-owner --no-acl --dbname "$RESTORE_TEST_DATABASE_URL" database/cealeg.dump`.
5. Upload the files under `storage/<bucket>/` into buckets with the same names.
6. Run `/health`, `/readiness`, sign-in, one barcode scan, and a Stripe test checkout against the disposable environment.
7. Delete the temporary project and the decrypted local files.

Run this drill at least quarterly and after database/storage architecture changes. Supabase database backups do not contain Storage objects, which is why the workflow exports both separately.
