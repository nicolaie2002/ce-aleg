import argparse
import os
from pathlib import Path, PurePosixPath

import requests


def safe_target(root, bucket, object_name):
    relative = PurePosixPath(object_name)

    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe storage object path: {object_name}")

    target = root / bucket / Path(*relative.parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def request_headers(service_key):
    return {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
    }


def list_objects(base_url, service_key, bucket, prefix=""):
    offset = 0

    while True:
        response = requests.post(
            f"{base_url}/storage/v1/object/list/{bucket}",
            headers={**request_headers(service_key), "Content-Type": "application/json"},
            json={"prefix": prefix, "limit": 1000, "offset": offset, "sortBy": {"column": "name", "order": "asc"}},
            timeout=(5, 30),
        )
        response.raise_for_status()
        items = response.json()

        for item in items:
            name = str(item.get("name") or "").strip()
            if not name:
                continue

            object_name = f"{prefix}/{name}".strip("/")
            if item.get("id") or item.get("metadata"):
                yield object_name
            else:
                yield from list_objects(base_url, service_key, bucket, object_name)

        if len(items) < 1000:
            break

        offset += len(items)


def download_object(base_url, service_key, bucket, object_name, target):
    with requests.get(
        f"{base_url}/storage/v1/object/{bucket}/{object_name}",
        headers=request_headers(service_key),
        stream=True,
        timeout=(5, 120),
    ) as response:
        response.raise_for_status()
        with target.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)


def main():
    parser = argparse.ArgumentParser(description="Back up configured Supabase Storage buckets.")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    base_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    buckets = [
        item.strip()
        for item in os.environ.get(
            "BACKUP_STORAGE_BUCKETS",
            "product-images,product-submissions",
        ).split(",")
        if item.strip()
    ]

    if not base_url or not service_key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.")

    output_root = Path(args.output).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    downloaded = 0

    for bucket in buckets:
        for object_name in list_objects(base_url, service_key, bucket):
            target = safe_target(output_root, bucket, object_name)
            download_object(base_url, service_key, bucket, object_name, target)
            downloaded += 1

    print(f"Downloaded {downloaded} storage objects from {len(buckets)} buckets.")


if __name__ == "__main__":
    main()
