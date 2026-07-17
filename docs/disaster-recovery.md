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
2. Verify the artifact checksum and set `BACKUP_ENCRYPTION_KEY` from the password manager.
3. Run `bash scripts/restore-supabase.sh cealeg-backup.tar.gz.enc` for a no-write validation.
4. Restore only into a disposable target with the guarded `--apply` procedure in
   `docs/runbooks/database-restore.md`.
5. Upload the files under `storage/<bucket>/` into buckets with the same names.
6. Run `/health`, `/readiness`, sign-in, one barcode scan, and a Stripe test checkout against the disposable environment.
7. Delete the temporary project and the decrypted local files.

Run this drill at least quarterly and after database/storage architecture changes. Supabase database backups do not contain Storage objects, which is why the workflow exports both separately.
