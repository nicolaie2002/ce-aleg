"""Deterministic local latency gate for representative Ce aleg API reads."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

# Set the isolated environment before importing the Flask application. Values
# from backend/.env cannot override these process variables.
os.environ.update(
    {
        "APP_ENV": "test",
        "DATABASE_URL": "sqlite:///:memory:",
        "AUTH_SECRET": "benchmark-only-auth-secret-with-at-least-32-characters",
        "EXTERNAL_CATALOG_ENABLED": "false",
        "OPEN_PRICES_ENABLED": "false",
        "ENABLE_OPENAI_VISION": "false",
        "SUPABASE_STORAGE_ENABLED": "false",
        "GLOBAL_RATE_LIMIT": "1000000",
        "AUTH_RATE_LIMIT": "1000000",
    }
)

import app as app_module  # noqa: E402
from database import db  # noqa: E402
from models import Product  # noqa: E402


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * ratio) - 1))
    return ordered[index]


def seed_catalog(size: int = 250) -> None:
    products = [
        Product(
            name=f"Produs benchmark {index:04d}",
            store=("Lidl", "Kaufland", "Carrefour", "Mega Image")[index % 4],
            category=("Lactate", "Mezeluri", "Bauturi", "Dulciuri")[index % 4],
            barcode=f"594{index:010d}",
            score=5.0 + (index % 45) / 10,
            calories=60 + index % 300,
            protein=index % 20,
            sugar=index % 30,
            fat=index % 25,
            ingredients="ingrediente de test, apa, proteine",
        )
        for index in range(size)
    ]
    db.session.add_all(products)
    db.session.commit()


def measure(client, path: str, iterations: int) -> dict[str, float | int | str]:
    warmup = client.get(path)
    if warmup.status_code != 200:
        raise RuntimeError(f"Warm-up failed for {path}: HTTP {warmup.status_code}")

    samples = []
    for _ in range(iterations):
        started = time.perf_counter()
        response = client.get(path)
        elapsed_ms = (time.perf_counter() - started) * 1000
        if response.status_code != 200:
            raise RuntimeError(f"Benchmark failed for {path}: HTTP {response.status_code}")
        samples.append(elapsed_ms)

    return {
        "path": path,
        "requests": iterations,
        "p50Ms": round(percentile(samples, 0.50), 3),
        "p95Ms": round(percentile(samples, 0.95), 3),
        "maxMs": round(max(samples), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--threshold-ms", type=float, default=500.0)
    arguments = parser.parse_args()
    iterations = max(20, arguments.iterations)

    app_module.GLOBAL_RATE_LIMIT = max(1_000_000, iterations * 10)
    app_module.PUBLIC_CATALOG_STATS_CACHE.update({"expires_at": 0, "data": None})

    with app_module.app.app_context():
        db.drop_all()
        db.create_all()
        seed_catalog()

        client = app_module.app.test_client()
        results = [
            measure(client, "/health", iterations),
            measure(client, "/products?limit=50", iterations),
            measure(client, "/catalog/romania/stats", iterations),
        ]

    report = {
        "environment": "isolated-sqlite-memory",
        "thresholdMs": arguments.threshold_ms,
        "results": results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    slow = [item for item in results if item["p95Ms"] > arguments.threshold_ms]
    if slow:
        print("Latency gate failed for: " + ", ".join(item["path"] for item in slow))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
