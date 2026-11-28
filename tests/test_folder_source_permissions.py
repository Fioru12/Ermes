"""Permessi NTFS anche per le cartelle registrate come fonti (passo 1.7 del piano).

Le fonti (core/folder_importer.py, scansionate anche dal Folder Watcher) sono
la seconda strada con cui una cartella di rete entra in Ermes. Fino al 28
novembre 2026 non leggevano i permessi: un file riservato sulla condivisione
arrivava a tutta la biblioteca anche dopo che il connettore cartelle era
stato corretto. Le regole sono le stesse del connettore
(core/connectors/ntfs_permissions.py).
"""

from __future__ import annotations

import pytest

from config import cfg
from core.connectors.ntfs_permissions import ALLOW, AclEntry, NtfsAcl
from core.folder_importer import scan_import_source
from core.library_store import LibraryStore

READ = 0x120089
ALICE = AclEntry("S-1-5-21-1-2-3-1001", "AZIENDA\\alice", ALLOW, READ)
BOB = AclEntry("S-1-5-21-1-2-3-1002", "AZIENDA\\bob", ALLOW, READ)
EVERYONE = AclEntry("S-1-1-0", "Everyone", ALLOW, READ)


def _acl(*entries: AclEntry) -> NtfsAcl:
    return NtfsAcl(entries=tuple(entries))


@pytest.fixture
def fonte(tmp_path, monkeypatch):
    monkeypatch.setattr("core.connector_ingest._known_usernames", lambda: {"alice": "alice", "bob": "bob"})
    monkeypatch.setattr(cfg, "FOLDER_SOURCES_INHERIT_PERMISSIONS", True)
    store = LibraryStore(tmp_path / "ermes.sqlite3")
    library = store.create_library("Amministrazione", "", "private", owner_id="owner")
    for user in ("alice", "bob"):
        store.set_library_member(library["id"], user, "viewer")
    cartella = tmp_path / "nas"
    cartella.mkdir()
    source = store.add_import_source(library["id"], str(cartella), created_by="owner")
    storage = tmp_path / "storage"
    return store, library["id"], cartella, source, str(storage)


def _visibili(store, library_id, utente):
    return {d["filename"] for d in store.list_documents(library_id, {"username": utente, "role": "viewer"})}


def test_a_file_readable_only_by_alice_is_visible_only_to_alice(fonte, monkeypatch):
    store, library_id, cartella, source, storage = fonte
    (cartella / "stipendi.txt").write_text("Stipendi riservati", encoding="utf-8")
    monkeypatch.setattr("core.folder_importer.read_ntfs_acl", lambda path: _acl(ALICE))

    scan_import_source(store, library_id, source, storage)

    assert _visibili(store, library_id, "alice") == {"stipendi.txt"}
    assert _visibili(store, library_id, "bob") == set()


def test_unreadable_permissions_hide_the_file_from_members(fonte, monkeypatch):
    store, library_id, cartella, source, storage = fonte
    (cartella / "verbale.txt").write_text("Verbale", encoding="utf-8")
    monkeypatch.setattr("core.folder_importer.read_ntfs_acl", lambda path: None)

    risultato = scan_import_source(store, library_id, source, storage)

    assert [i["filename"] for i in risultato["imported"]] == ["verbale.txt"]
    assert _visibili(store, library_id, "alice") == set()
    assert _visibili(store, library_id, "bob") == set()
    # Il proprietario della biblioteca lo vede comunque.
    assert _visibili(store, library_id, "owner") == {"verbale.txt"}


def test_a_file_for_everyone_follows_the_library(fonte, monkeypatch):
    store, library_id, cartella, source, storage = fonte
    (cartella / "mensa.txt").write_text("Orari mensa", encoding="utf-8")
    monkeypatch.setattr("core.folder_importer.read_ntfs_acl", lambda path: _acl(EVERYONE))

    scan_import_source(store, library_id, source, storage)

    assert _visibili(store, library_id, "bob") == {"mensa.txt"}


def test_a_permission_removed_at_the_source_disappears_at_the_next_scan(fonte, monkeypatch):
    """Il file non cambia, quindi la seconda scansione lo salta come duplicato:
    i permessi vanno aggiornati comunque."""
    store, library_id, cartella, source, storage = fonte
    (cartella / "progetto.txt").write_text("Progetto", encoding="utf-8")
    acl = {"valore": _acl(ALICE, BOB)}
    monkeypatch.setattr("core.folder_importer.read_ntfs_acl", lambda path: acl["valore"])

    scan_import_source(store, library_id, source, storage)
    assert _visibili(store, library_id, "bob") == {"progetto.txt"}

    acl["valore"] = _acl(ALICE)
    risultato = scan_import_source(store, library_id, source, storage)

    assert risultato["skipped_duplicates"] == ["progetto.txt"]
    assert _visibili(store, library_id, "bob") == set()
    assert _visibili(store, library_id, "alice") == {"progetto.txt"}


def test_inheritance_can_be_turned_off(fonte, monkeypatch):
    store, library_id, cartella, source, storage = fonte
    monkeypatch.setattr(cfg, "FOLDER_SOURCES_INHERIT_PERMISSIONS", False)
    (cartella / "libero.txt").write_text("Libero", encoding="utf-8")
    monkeypatch.setattr("core.folder_importer.read_ntfs_acl", lambda path: None)

    scan_import_source(store, library_id, source, storage)

    assert _visibili(store, library_id, "bob") == {"libero.txt"}


def test_the_default_is_to_inherit_permissions():
    from config.storage import StorageConfig

    assert StorageConfig().FOLDER_SOURCES_INHERIT_PERMISSIONS is True
