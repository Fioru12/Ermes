from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api import app
from api.auth import _require_role, _verify_api_key
from core.connector_scheduler import (
    ConnectorScheduleStore,
    run_schedule_sync,
    sync_due_schedules,
)
from core.connectors.base import DeltaSyncResult, RemoteDocument
from core.library_store import LibraryStore


@pytest.fixture
def temp_sched_store(tmp_path):
    db_path = tmp_path / "test_schedules.db"
    return ConnectorScheduleStore(db_path=db_path)


def test_connector_schedule_store_crud(temp_sched_store):
    # 1. Create schedule
    sched = temp_sched_store.create_schedule(
        name="Sync SharePoint HR",
        connector_type="microsoft_graph",
        config={"tenant_id": "t1", "client_id": "c1", "client_secret": "s1", "drive_id": "d1"},
        target_library_id="lib_hr",
        interval_minutes=30,
    )
    assert sched.id.startswith("sched_")
    assert sched.name == "Sync SharePoint HR"
    assert sched.interval_minutes == 30
    assert sched.enabled is True
    assert sched.last_status == "idle"

    # 2. List schedules
    schedules = temp_sched_store.list_schedules()
    assert len(schedules) == 1
    assert schedules[0].id == sched.id

    schedules_hr = temp_sched_store.list_schedules(target_library_id="lib_hr")
    assert len(schedules_hr) == 1
    assert temp_sched_store.list_schedules(target_library_id="lib_other") == []

    # 3. Get single schedule
    fetched = temp_sched_store.get_schedule(sched.id)
    assert fetched is not None
    assert fetched.name == "Sync SharePoint HR"

    # 4. Update sync result
    temp_sched_store.update_sync_result(
        schedule_id=sched.id,
        status="success",
        items_count=5,
        next_delta_token="delta_token_abc",
    )
    updated = temp_sched_store.get_schedule(sched.id)
    assert updated.last_status == "success"
    assert updated.items_synced == 5
    assert updated.next_delta_token == "delta_token_abc"
    assert updated.last_sync_at is not None
    assert updated.next_sync_at > updated.last_sync_at

    # 5. Delete schedule
    assert temp_sched_store.delete_schedule(sched.id) is True
    assert temp_sched_store.get_schedule(sched.id) is None


class _MemoryStorage:
    def __init__(self):
        self.files = {}

    def save(self, path, content):
        self.files[path] = content

    def delete(self, path):
        self.files.pop(path, None)


@pytest.fixture
def real_store(tmp_path, monkeypatch):
    """LibraryStore vero su SQLite temporaneo: uno store finto nascondeva che
    le cancellazioni cercavano il documento con l'id remoto."""
    monkeypatch.setattr("core.storage_provider.get_storage_provider", _MemoryStorage)
    monkeypatch.setattr("core.connector_ingest._known_usernames", dict)
    store = LibraryStore(tmp_path / "ermes.sqlite3")
    library = store.create_library("Archivio", "", "private", owner_id="owner")
    return store, library["id"]


def _connector(**methods):
    connector = MagicMock()
    connector.source_key.return_value = "test-source"
    connector.listing = None
    for name, value in methods.items():
        getattr(connector, name).return_value = value
    return connector


def test_run_schedule_sync_full(temp_sched_store, real_store):
    store, library_id = real_store
    sched = temp_sched_store.create_schedule(
        name="S3 Backup",
        connector_type="s3_bucket",
        config={"bucket_name": "my-bucket", "region_name": "eu-central-1"},
        target_library_id=library_id,
        interval_minutes=60,
    )

    mock_doc = RemoteDocument(
        id="s3://my-bucket/doc1.txt",
        name="doc1.txt",
        content=b"Contenuto del file",
        media_type="text/plain",
        source_url="https://s3.amazonaws.com/my-bucket/doc1.txt",
        last_modified="2026-09-21T10:00:00Z",
    )

    with (
        patch("core.connector_scheduler.get_schedule_store", return_value=temp_sched_store),
        patch("api.connectors._build_connector", return_value=_connector(fetch_documents=[mock_doc])),
    ):
        result = run_schedule_sync(sched.id, store=store)
        assert result["ok"] is True
        assert result["mode"] == "full"
        assert result["imported"] == 1
        assert [d["filename"] for d in store.list_documents(library_id)] == ["doc1.txt"]

        updated_sched = temp_sched_store.get_schedule(sched.id)
        assert updated_sched.last_status == "success"
        assert updated_sched.items_synced == 1


def test_run_schedule_sync_delta(temp_sched_store, real_store):
    store, library_id = real_store
    sched = temp_sched_store.create_schedule(
        name="GDrive Delta",
        connector_type="google_drive",
        config={"service_account_json": "{}"},
        target_library_id=library_id,
        interval_minutes=15,
    )
    temp_sched_store.update_sync_result(
        schedule_id=sched.id,
        status="idle",
        next_delta_token="initial_token_123",
    )

    old_doc = RemoteDocument(
        id="gdrive-file-99",
        name="vecchio.txt",
        content=b"Da cancellare",
        media_type="text/plain",
        source_url="https://drive.google.com/file99",
        last_modified="2026-09-20T11:00:00Z",
    )
    new_doc = RemoteDocument(
        id="gdrive-file-2",
        name="file2.txt",
        content=b"Aggiornato",
        media_type="text/plain",
        source_url="https://drive.google.com/file2.txt",
        last_modified="2026-09-21T11:00:00Z",
    )

    first = DeltaSyncResult(
        connector_type="GoogleDriveConnector", updated_documents=[old_doc], next_delta_token="token_v1b"
    )
    second = DeltaSyncResult(
        connector_type="GoogleDriveConnector",
        updated_documents=[new_doc],
        deleted_document_ids=["gdrive-file-99"],
        next_delta_token="token_v2",
    )
    connector = _connector()
    connector.fetch_delta.side_effect = [first, second]

    with (
        patch("core.connector_scheduler.get_schedule_store", return_value=temp_sched_store),
        patch("api.connectors._build_connector", return_value=connector),
    ):
        run_schedule_sync(sched.id, store=store)
        result = run_schedule_sync(sched.id, store=store)
        assert result["ok"] is True
        assert result["mode"] == "delta"
        assert result["imported"] == 1
        assert result["deleted"] == 1
        assert result["next_delta_token"] == "token_v2"

        assert [d["filename"] for d in store.list_documents(library_id)] == ["file2.txt"]
        updated_sched = temp_sched_store.get_schedule(sched.id)
        assert updated_sched.next_delta_token == "token_v2"


def test_sync_due_schedules(temp_sched_store):
    sched = temp_sched_store.create_schedule(
        name="Due Sync",
        connector_type="s3_bucket",
        config={},
        target_library_id="lib1",
        interval_minutes=10,
    )
    mock_store = MagicMock()
    mock_store.content_hash_index.return_value = {}

    with (
        patch("core.connector_scheduler.get_schedule_store", return_value=temp_sched_store),
        patch("core.connector_scheduler.run_schedule_sync", return_value={"ok": True}) as mock_run,
    ):
        # next_sync_at <= now -> triggera sync
        count = sync_due_schedules(mock_store)
        assert count == 1
        mock_run.assert_called_once_with(sched.id, mock_store)


# ── Test API Endpoints ─────────────────────────────────────────────────────────


@pytest.fixture
def client(temp_sched_store):
    app.dependency_overrides[_verify_api_key] = lambda: {"username": "admin", "role": "admin"}
    app.dependency_overrides[_require_role("admin")] = lambda: {"username": "admin", "role": "admin"}
    app.dependency_overrides[_require_role("editor")] = lambda: {"username": "admin", "role": "admin"}
    with patch("core.connector_scheduler.get_schedule_store", return_value=temp_sched_store):
        yield TestClient(app)
    app.dependency_overrides.clear()


def test_api_connector_schedules(client, temp_sched_store):
    from api.libraries import get_library_store

    mock_store = MagicMock()
    mock_store.content_hash_index.return_value = {}
    mock_store.get_library.return_value = {"id": "lib_cloud", "name": "Cloud"}
    app.dependency_overrides[get_library_store] = lambda: mock_store

    try:
        # 1. Create schedule via API
        resp_create = client.post(
            "/api/connectors/schedules",
            json={
                "name": "Sync Confluence Wiki",
                "connector_type": "confluence",
                "config": {"url": "https://company.atlassian.net/wiki", "space_key": "DEV"},
                "target_library_id": "lib_cloud",
                "interval_minutes": 45,
                "enabled": True,
            },
            headers={"Authorization": "Bearer test-key"},
        )
        assert resp_create.status_code == 200
        created = resp_create.json()["schedule"]
        schedule_id = created["id"]
        assert created["name"] == "Sync Confluence Wiki"

        # 2. List schedules
        resp_list = client.get("/api/connectors/schedules", headers={"Authorization": "Bearer test-key"})
        assert resp_list.status_code == 200
        items = resp_list.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == schedule_id

        # 3. Trigger schedule sync
        with patch("core.connector_scheduler.run_schedule_sync", return_value={"ok": True, "imported": 2}):
            resp_trigger = client.post(
                f"/api/connectors/schedules/{schedule_id}/trigger",
                headers={"Authorization": "Bearer test-key"},
            )
            assert resp_trigger.status_code == 200
            assert resp_trigger.json()["ok"] is True

        # 4. Delete schedule
        resp_del = client.delete(
            f"/api/connectors/schedules/{schedule_id}",
            headers={"Authorization": "Bearer test-key"},
        )
        assert resp_del.status_code == 200
        assert resp_del.json()["deleted_id"] == schedule_id
    finally:
        app.dependency_overrides.pop(get_library_store, None)
