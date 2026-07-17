import argparse
import mimetypes
import os
from pathlib import Path
from urllib.parse import quote

import requests


RESTORE_CONFIRMATION = "YES_I_UNDERSTAND"


def iter_storage_objects(root):
    resolved_root = Path(root).resolve()

    if not resolved_root.is_dir():
        raise ValueError(f"Storage backup directory does not exist: {resolved_root}")

    for bucket_dir in sorted(resolved_root.iterdir()):
        if not bucket_dir.is_dir() or bucket_dir.is_symlink():
            continue

        for source in sorted(bucket_dir.rglob("*")):
            if not source.is_file() or source.is_symlink():
                continue

            resolved_source = source.resolve()
            if resolved_root not in resolved_source.parents:
                raise ValueError(f"Unsafe storage restore path: {source}")

            yield bucket_dir.name, source.relative_to(bucket_dir).as_posix(), source


def object_url(base_url, bucket, object_name):
    encoded_bucket = quote(bucket, safe="")
    encoded_name = "/".join(quote(part, safe="") for part in object_name.split("/"))
    return f"{base_url.rstrip('/')}/storage/v1/object/{encoded_bucket}/{encoded_name}"


def upload_object(base_url, service_key, bucket, object_name, source):
    content_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
    with source.open("rb") as payload:
        response = requests.post(
            object_url(base_url, bucket, object_name),
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Content-Type": content_type,
                "x-upsert": "true",
            },
            data=payload,
            timeout=(5, 120),
        )
    response.raise_for_status()


def restore_storage(root, apply=False):
    objects = list(iter_storage_objects(root))
    total_bytes = sum(source.stat().st_size for _, _, source in objects)

    if not apply:
        return {"objects": len(objects), "bytes": total_bytes, "applied": False}

    if os.environ.get("RESTORE_CONFIRM_DISPOSABLE_TARGET") != RESTORE_CONFIRMATION:
        raise RuntimeError("Disposable restore confirmation is missing.")

    base_url = os.environ.get("RESTORE_SUPABASE_URL", "").strip()
    service_key = os.environ.get("RESTORE_SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not base_url or not service_key:
        raise RuntimeError("RESTORE_SUPABASE_URL and RESTORE_SUPABASE_SERVICE_ROLE_KEY are required.")

    for bucket, object_name, source in objects:
        upload_object(base_url, service_key, bucket, object_name, source)

    return {"objects": len(objects), "bytes": total_bytes, "applied": True}


def main():
    parser = argparse.ArgumentParser(
        description="Validate or restore Supabase Storage backup files."
    )
    parser.add_argument("--root", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = restore_storage(args.root, apply=args.apply)
    action = "Restored" if result["applied"] else "Validated"
    print(f"{action} {result['objects']} objects ({result['bytes']} bytes).")


if __name__ == "__main__":
    main()
