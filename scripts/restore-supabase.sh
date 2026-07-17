#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/restore-supabase.sh <encrypted-backup.tar.gz.enc> [--apply]

Default mode decrypts, validates checksums, and inspects the PostgreSQL dump.
Writing requires --apply plus RESTORE_TEST_DATABASE_URL, RESTORE_TARGET_LABEL
containing test/staging/disposable/restore, and
RESTORE_CONFIRM_DISPOSABLE_TARGET=YES_I_UNDERSTAND.
EOF
}

archive_path="${1:-}"
mode="${2:---dry-run}"

if [[ -z "$archive_path" || "$archive_path" == "--help" || "$archive_path" == "-h" ]]; then
  usage
  [[ -n "$archive_path" ]] && exit 0
  exit 2
fi

if [[ "$mode" != "--dry-run" && "$mode" != "--apply" ]]; then
  usage >&2
  exit 2
fi

if [[ ! -f "$archive_path" ]]; then
  echo "Backup archive not found: $archive_path" >&2
  exit 1
fi

for command_name in openssl tar sha256sum pg_restore; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command is missing: $command_name" >&2
    exit 1
  fi
done

encryption_key="${BACKUP_ENCRYPTION_KEY:?Set BACKUP_ENCRYPTION_KEY}"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/cealeg-restore.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT

openssl enc -d -aes-256-cbc -pbkdf2 \
  -in "$archive_path" \
  -pass env:BACKUP_ENCRYPTION_KEY \
  -out "$work_dir/backup.tar.gz"

if tar -tzf "$work_dir/backup.tar.gz" | grep -Eq '(^/|(^|/)\.\.(/|$))'; then
  echo "Archive contains an unsafe path." >&2
  exit 1
fi

tar -xzf "$work_dir/backup.tar.gz" -C "$work_dir"
dump_path="$work_dir/database/cealeg.dump"

if [[ ! -f "$dump_path" || ! -f "$work_dir/checksums.sha256" ]]; then
  echo "Archive is missing the database dump or checksum manifest." >&2
  exit 1
fi

(
  cd "$work_dir"
  sha256sum --check checksums.sha256
)
pg_restore --list "$dump_path" >/dev/null

if [[ "$mode" == "--dry-run" ]]; then
  echo "Dry run complete: archive, checksums, and PostgreSQL dump are valid."
  exit 0
fi

target_url="${RESTORE_TEST_DATABASE_URL:?Set RESTORE_TEST_DATABASE_URL for a disposable target}"
target_label="${RESTORE_TARGET_LABEL:-}"
confirmation="${RESTORE_CONFIRM_DISPOSABLE_TARGET:-}"

if [[ ! "$target_label" =~ (test|staging|disposable|restore) ]]; then
  echo "RESTORE_TARGET_LABEL must identify a non-production environment." >&2
  exit 1
fi

if [[ "$confirmation" != "YES_I_UNDERSTAND" ]]; then
  echo "Set RESTORE_CONFIRM_DISPOSABLE_TARGET=YES_I_UNDERSTAND to apply." >&2
  exit 1
fi

if [[ -n "${DATABASE_URL:-}" && "$target_url" == "$DATABASE_URL" ]]; then
  echo "Restore target matches DATABASE_URL; refusing to touch production." >&2
  exit 1
fi

if [[ -n "${BACKUP_DATABASE_URL:-}" && "$target_url" == "$BACKUP_DATABASE_URL" ]]; then
  echo "Restore target matches BACKUP_DATABASE_URL; refusing to continue." >&2
  exit 1
fi

pg_restore \
  --clean \
  --if-exists \
  --exit-on-error \
  --no-owner \
  --no-acl \
  --dbname="$target_url" \
  "$dump_path"

if [[ -n "${RESTORE_SUPABASE_URL:-}" || -n "${RESTORE_SUPABASE_SERVICE_ROLE_KEY:-}" ]]; then
  python backend/restore_supabase_storage.py --root "$work_dir/storage" --apply
else
  echo "Storage restore skipped: RESTORE_SUPABASE_URL/key were not provided."
fi

echo "Restore completed on disposable target: $target_label"
