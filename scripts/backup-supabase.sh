#!/usr/bin/env bash
set -euo pipefail

output_dir="${1:-backup}"
database_url="${DATABASE_URL:?Set DATABASE_URL to a direct or session-pooler PostgreSQL URL}"
postgres_image="${BACKUP_POSTGRES_IMAGE:-postgres:17-alpine}"

mkdir -p "$output_dir/database" "$output_dir/storage"
output_dir_abs="$(cd "$output_dir" && pwd)"
dump_path="$output_dir/database/cealeg.dump"

if [[ -e "$dump_path" ]]; then
  echo "Refusing to overwrite existing dump: $dump_path" >&2
  exit 1
fi

if command -v pg_dump >/dev/null 2>&1 && command -v pg_restore >/dev/null 2>&1; then
  pg_dump "$database_url" \
    --format=custom \
    --no-owner \
    --no-acl \
    --file="$dump_path"
  pg_restore --list "$dump_path" > "$output_dir/database/manifest.txt"
elif command -v docker >/dev/null 2>&1; then
  docker run --rm \
    -e DATABASE_URL="$database_url" \
    -v "$output_dir_abs/database:/backup" \
    "$postgres_image" \
    sh -c 'pg_dump "$DATABASE_URL" --format=custom --no-owner --no-acl --file=/backup/cealeg.dump && pg_restore --list /backup/cealeg.dump > /backup/manifest.txt'
else
  echo "pg_dump/pg_restore or Docker is required." >&2
  exit 1
fi

python backend/backup_supabase_storage.py --output "$output_dir/storage"

(
  cd "$output_dir"
  find database storage -type f -print0 | sort -z | xargs -0 sha256sum > checksums.sha256
  {
    printf 'generated_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'postgres_image=%s\n' "$postgres_image"
    printf 'storage_buckets=%s\n' "${BACKUP_STORAGE_BUCKETS:-product-images,product-submissions}"
  } > backup-info.txt
)

echo "Backup payload created in $output_dir."
