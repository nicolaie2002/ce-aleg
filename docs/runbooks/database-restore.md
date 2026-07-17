# Runbook: restaurare baza de date si Storage

## Scop si severitate

Procedura se foloseste pentru un restore drill sau dupa pierdere/corupere confirmata.
O restaurare peste productie este SEV-1 si nu se executa direct din acest runbook.

## Garzi obligatorii

1. Identifica backup run ID, data UTC si RPO-ul rezultat.
2. Creeaza o baza sau un proiect disposable separat.
3. Confirma ca URL-ul tinta difera de `DATABASE_URL` si `BACKUP_DATABASE_URL`.
4. Pastreaza `BACKUP_ENCRYPTION_KEY` si service role key numai in secrete private.
5. Ruleaza intai dry-run-ul din [supabase-backup.md](../supabase-backup.md).

## Restaurare controlata

```bash
export BACKUP_ENCRYPTION_KEY='...'
export RESTORE_TEST_DATABASE_URL='postgresql://...'
export RESTORE_TARGET_LABEL='quarterly-restore-test'
export RESTORE_CONFIRM_DISPOSABLE_TARGET='YES_I_UNDERSTAND'
bash scripts/restore-supabase.sh cealeg-backup.tar.gz.enc --apply
```

Pentru Storage configureaza credentialele proiectului disposable sub numele
`RESTORE_SUPABASE_URL` si `RESTORE_SUPABASE_SERVICE_ROLE_KEY`. Nu reutiliza
variabilele de productie sub aceste nume.

## Verificare

1. Confirma tabelele si numarul aproximativ de utilizatori, produse, abonamente,
   contributii si evenimente Stripe.
2. Porneste backend-ul de test si verifica `/health` si `/readiness`.
3. Testeaza login, scanare, imagine produs, contributie si stergere cont.
4. Foloseste exclusiv Stripe test mode pentru checkout si webhook.
5. Confirma ca fisierele Storage pot fi citite, apoi sterge proiectul disposable.
6. Noteaza durata, erorile si RTO/RPO observate in jurnalul privat.

## Escaladare spre productie

Schimbarea conexiunii de productie necesita o fereastra aprobata, backup nou,
reconciliere Stripe, plan de rollback si verificare manuala. Nu promova baza
restaurata doar pentru ca `pg_restore` s-a terminat fara eroare.
