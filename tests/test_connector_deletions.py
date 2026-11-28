"""File cancellati o modificati all'origine (voce C-22 del catalogo, passo 1.6).

Un documento arrivato da un connettore deve sparire da Ermes quando sparisce
dall'origine, e la versione vecchia di un file modificato non deve restare
cercabile accanto a quella nuova. Altrimenti un file riservato cancellato da
una cartella di rete continua a uscire nelle risposte.

I test usano il codice vero: LibraryStore su SQLite temporaneo, il
connettore cartelle su una cartella temporanea e la sincronizzazione dello
scheduler. Solo lo storage dei file originali e' in memoria.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.connector_scheduler import ConnectorScheduleStore, run_schedule_sync
from core.connectors.base import BaseConnector, DeltaSyncResult, RemoteDocument
from core.library_store import LibraryStore


class _MemoryStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def save(self, path: str, content: bytes) -> None:
        self.files[path] = content

    def delete(self, path: str) -> None:
        self.files.pop(path, None)


@pytest.fixture
def ambiente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    storage = _MemoryStorage()
    monkeypatch.setattr("core.storage_provider.get_storage_provider", lambda: storage)
    monkeypatch.setattr("core.connector_ingest._known_usernames", dict)
    sched_store = ConnectorScheduleStore(db_path=tmp_path / "schedules.db")
    monkeypatch.setattr("core.connector_scheduler.get_schedule_store", lambda: sched_store)
    store = LibraryStore(tmp_path / "ermes.sqlite3")
    library = store.create_library("Ufficio", "", "private", owner_id="owner")
    cartella = tmp_path / "nas"
    cartella.mkdir()
    return store, library["id"], cartella, sched_store, storage


def _nomi(store: LibraryStore, library_id: str) -> set[str]:
    return {d["filename"] for d in store.list_documents(library_id)}


def _testi(store: LibraryStore, library_id: str) -> str:
    """Il testo cercabile della biblioteca: quello dei passaggi indicizzati."""
    with store._connection() as connection:
        righe = connection.execute(
            "SELECT c.text FROM document_chunks c JOIN documents d ON d.id = c.document_id WHERE d.library_id = ?",
            (library_id,),
        ).fetchall()
    return " ".join(riga["text"] for riga in righe)


def _sincronizza_cartella(sched_store, library_id: str, cartella: Path, store: LibraryStore) -> dict:
    schedule = sched_store.create_schedule(
        name="NAS",
        connector_type="local_folder",
        config={"folder_path": str(cartella)},
        target_library_id=library_id,
    )
    return run_schedule_sync(schedule.id, store=store)


def test_a_file_deleted_from_the_folder_disappears_from_ermes(ambiente):
    store, library_id, cartella, sched_store, storage = ambiente
    (cartella / "pubblico.txt").write_text("Orari della mensa aziendale.", encoding="utf-8")
    (cartella / "riservato.txt").write_text("Stipendi della direzione.", encoding="utf-8")

    schedule = sched_store.create_schedule(
        name="NAS", connector_type="local_folder", config={"folder_path": str(cartella)}, target_library_id=library_id
    )
    run_schedule_sync(schedule.id, store=store)
    assert _nomi(store, library_id) == {"pubblico.txt", "riservato.txt"}

    (cartella / "riservato.txt").unlink()
    risultato = run_schedule_sync(schedule.id, store=store)

    assert _nomi(store, library_id) == {"pubblico.txt"}
    assert risultato["deleted"] == 1
    assert not any("riservato" in path for path in storage.files)


def test_a_modified_file_replaces_the_old_version(ambiente):
    store, library_id, cartella, sched_store, _storage = ambiente
    file = cartella / "procedura.txt"
    file.write_text("Le ferie si chiedono con 10 giorni di anticipo.", encoding="utf-8")

    schedule = sched_store.create_schedule(
        name="NAS", connector_type="local_folder", config={"folder_path": str(cartella)}, target_library_id=library_id
    )
    run_schedule_sync(schedule.id, store=store)

    file.write_text("Le ferie si chiedono con 20 giorni di anticipo.", encoding="utf-8")
    run_schedule_sync(schedule.id, store=store)

    documenti = store.list_documents(library_id)
    assert len(documenti) == 1
    assert "20 giorni" in _testi(store, library_id)
    assert "10 giorni" not in _testi(store, library_id)


def test_nothing_is_deleted_when_the_listing_is_incomplete(ambiente):
    """Oltre max_files l'elenco e' parziale: i file non visti non sono spariti."""
    store, library_id, cartella, sched_store, _storage = ambiente
    for nome in ("a.txt", "b.txt", "c.txt"):
        (cartella / nome).write_text(f"Contenuto {nome}", encoding="utf-8")

    completo = sched_store.create_schedule(
        name="NAS", connector_type="local_folder", config={"folder_path": str(cartella)}, target_library_id=library_id
    )
    run_schedule_sync(completo.id, store=store)
    assert len(_nomi(store, library_id)) == 3

    parziale = sched_store.create_schedule(
        name="NAS limitato",
        connector_type="local_folder",
        config={"folder_path": str(cartella), "max_files": 1},
        target_library_id=library_id,
    )
    risultato = run_schedule_sync(parziale.id, store=store)

    assert len(_nomi(store, library_id)) == 3
    assert risultato["deleted"] == 0


def test_nothing_is_deleted_when_the_folder_is_unreachable(ambiente):
    """Una cartella di rete staccata non vuol dire che i file sono stati cancellati."""
    store, library_id, cartella, sched_store, _storage = ambiente
    (cartella / "regolamento.txt").write_text("Regolamento interno.", encoding="utf-8")
    schedule = sched_store.create_schedule(
        name="NAS", connector_type="local_folder", config={"folder_path": str(cartella)}, target_library_id=library_id
    )
    run_schedule_sync(schedule.id, store=store)

    (cartella / "regolamento.txt").unlink()
    cartella.rmdir()
    run_schedule_sync(schedule.id, store=store)

    assert _nomi(store, library_id) == {"regolamento.txt"}


def test_a_manual_upload_with_the_same_name_is_never_deleted(ambiente):
    store, library_id, cartella, sched_store, _storage = ambiente
    store.add_document(
        library_id=library_id,
        filename="contratto.txt",
        media_type="text/plain",
        content=b"Caricato a mano",
        storage_path="manuale/contratto.txt",
        status="ready",
        chunks=[("Caricato a mano", "Pagina 1")],
    )
    (cartella / "contratto.txt").write_text("Dalla cartella", encoding="utf-8")
    schedule = sched_store.create_schedule(
        name="NAS", connector_type="local_folder", config={"folder_path": str(cartella)}, target_library_id=library_id
    )
    run_schedule_sync(schedule.id, store=store)
    (cartella / "contratto.txt").unlink()
    run_schedule_sync(schedule.id, store=store)

    # Il file della cartella e' diventato una nuova versione del documento
    # caricato a mano (add_document unisce per nome): il documento resta.
    assert _nomi(store, library_id) == {"contratto.txt"}


def test_two_folders_in_the_same_library_do_not_delete_each_other(ambiente, tmp_path: Path):
    store, library_id, cartella, sched_store, _storage = ambiente
    seconda = tmp_path / "nas2"
    seconda.mkdir()
    (cartella / "uno.txt").write_text("Primo archivio", encoding="utf-8")
    (seconda / "due.txt").write_text("Secondo archivio", encoding="utf-8")

    _sincronizza_cartella(sched_store, library_id, cartella, store)
    _sincronizza_cartella(sched_store, library_id, seconda, store)
    _sincronizza_cartella(sched_store, library_id, cartella, store)

    assert _nomi(store, library_id) == {"uno.txt", "due.txt"}


class _DriveFinto(BaseConnector):
    """Un connettore con delta nativo: segnala le cancellazioni con il suo id."""

    def __init__(self, config):
        super().__init__(config)
        self.risposte: list[DeltaSyncResult] = config["risposte"]

    def test_connection(self):
        return True, "ok"

    def fetch_documents(self):
        return []

    def fetch_delta(self, delta_token=None):
        return self.risposte.pop(0)


def test_a_deletion_reported_by_a_delta_connector_removes_the_document(ambiente, monkeypatch):
    store, library_id, _cartella, sched_store, _storage = ambiente
    documento = RemoteDocument(
        id="drive-file-42",
        name="budget.txt",
        content=b"Budget riservato 2027",
        media_type="text/plain",
        source_url="https://drive.example/42",
        last_modified="",
    )
    risposte = [
        DeltaSyncResult(connector_type="drive", updated_documents=[documento], next_delta_token="t2"),
        DeltaSyncResult(
            connector_type="drive", updated_documents=[], deleted_document_ids=["drive-file-42"], next_delta_token="t3"
        ),
    ]
    monkeypatch.setattr("api.connectors._build_connector", lambda tipo, config: _DriveFinto({"risposte": risposte}))
    schedule = sched_store.create_schedule(
        name="Drive", connector_type="google_drive", config={}, target_library_id=library_id
    )
    sched_store.update_sync_result(schedule.id, "success", 0, next_delta_token="t1", error_message=None)

    run_schedule_sync(schedule.id, store=store)
    assert _nomi(store, library_id) == {"budget.txt"}

    run_schedule_sync(schedule.id, store=store)
    assert _nomi(store, library_id) == set()


def test_the_api_full_sync_removes_files_deleted_from_the_folder(ambiente, monkeypatch):
    from fastapi.testclient import TestClient

    from api import app
    from api.libraries import get_library_store
    from config import cfg

    store, library_id, cartella, _sched_store, _storage = ambiente
    monkeypatch.setattr(cfg, "API_KEY", "admin-key")
    monkeypatch.setattr("api.connectors.get_storage_provider", lambda: _storage)
    app.dependency_overrides[get_library_store] = lambda: store
    (cartella / "resta.txt").write_text("Resta nella cartella", encoding="utf-8")
    (cartella / "sparisce.txt").write_text("Verra' cancellato", encoding="utf-8")
    payload = {"type": "local_folder", "config": {"folder_path": str(cartella)}, "target_library_id": library_id}
    headers = {"Authorization": "Bearer admin-key"}
    try:
        client = TestClient(app)
        assert client.post("/api/connectors/sync", json=payload, headers=headers).status_code == 200
        assert _nomi(store, library_id) == {"resta.txt", "sparisce.txt"}

        (cartella / "sparisce.txt").unlink()
        risposta = client.post("/api/connectors/sync", json=payload, headers=headers)

        assert risposta.status_code == 200
        assert risposta.json()["deleted_count"] == 1
        assert _nomi(store, library_id) == {"resta.txt"}
    finally:
        app.dependency_overrides.pop(get_library_store, None)
