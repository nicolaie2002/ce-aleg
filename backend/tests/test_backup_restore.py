from pathlib import Path

import pytest

import restore_supabase_storage as restore_module
from backup_supabase_storage import safe_target


def test_backup_target_rejects_parent_traversal(tmp_path):
    with pytest.raises(ValueError, match="Unsafe"):
        safe_target(tmp_path, "products", "../secret.txt")


def test_storage_restore_dry_run_counts_regular_files(tmp_path):
    (tmp_path / "product-images" / "nested").mkdir(parents=True)
    (tmp_path / "product-images" / "front.jpg").write_bytes(b"front")
    (tmp_path / "product-images" / "nested" / "label.png").write_bytes(b"label")

    result = restore_module.restore_storage(tmp_path)

    assert result == {"objects": 2, "bytes": 10, "applied": False}


def test_storage_restore_requires_explicit_disposable_confirmation(tmp_path, monkeypatch):
    (tmp_path / "product-images").mkdir()
    (tmp_path / "product-images" / "front.jpg").write_bytes(b"front")
    monkeypatch.delenv("RESTORE_CONFIRM_DISPOSABLE_TARGET", raising=False)

    with pytest.raises(RuntimeError, match="confirmation"):
        restore_module.restore_storage(tmp_path, apply=True)


def test_storage_restore_encodes_paths_and_uploads_only_after_confirmation(
    tmp_path, monkeypatch
):
    source = tmp_path / "product images" / "folder" / "față.jpg"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"image")
    calls = []

    class Response:
        def raise_for_status(self):
            return None

    def fake_post(url, **kwargs):
        calls.append((url, kwargs["headers"], kwargs["data"].read()))
        return Response()

    monkeypatch.setenv("RESTORE_CONFIRM_DISPOSABLE_TARGET", "YES_I_UNDERSTAND")
    monkeypatch.setenv("RESTORE_SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("RESTORE_SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
    monkeypatch.setattr(restore_module.requests, "post", fake_post)

    result = restore_module.restore_storage(tmp_path, apply=True)

    assert result["applied"] is True
    assert calls[0][0].endswith("/product%20images/folder/fa%C8%9B%C4%83.jpg")
    assert calls[0][1]["x-upsert"] == "true"
    assert calls[0][2] == b"image"
