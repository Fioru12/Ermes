"""Permessi NTFS delle cartelle di rete (fase 1 del piano, voce 1.6 del piano strategico).

Un test per ogni regola di traduzione (core/connectors/ntfs_permissions.py),
che girano ovunque; poi il percorso completo con il connettore cartelle e lo
store vero; infine, solo su Windows, la lettura dei permessi di un file vero.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from core.connector_ingest import import_remote_document
from core.connectors.local_folder import LocalFolderConnector
from core.connectors.ntfs_permissions import (
    ALLOW,
    DENY,
    INHERIT_ONLY_ACE,
    OTHER,
    AclEntry,
    NtfsAcl,
    ntfs_acl_to_principals,
    read_ntfs_acl,
)
from core.library_store import LibraryStore

READ = 0x120089  # FILE_GENERIC_READ
WRITE_ONLY = 0x0002  # FILE_WRITE_DATA
FULL = 0x1F01FF  # FILE_ALL_ACCESS

ALICE = AclEntry("S-1-5-21-1-2-3-1001", "AZIENDA\\alice", ALLOW, READ)
BOB = AclEntry("S-1-5-21-1-2-3-1002", "AZIENDA\\bob", ALLOW, FULL)
SYSTEM = AclEntry("S-1-5-18", "NT AUTHORITY\\SYSTEM", ALLOW, FULL)
ADMINS = AclEntry("S-1-5-32-544", "BUILTIN\\Administrators", ALLOW, FULL)


def _acl(*entries: AclEntry) -> NtfsAcl:
    return NtfsAcl(entries=tuple(entries))


# --- Regole di traduzione -------------------------------------------------


def test_unreadable_permissions_close_the_document():
    assert ntfs_acl_to_principals(None) == ()


def test_a_null_dacl_follows_the_library_rules():
    assert ntfs_acl_to_principals(NtfsAcl(entries=(), null_dacl=True)) is None


def test_an_empty_dacl_closes_the_document():
    assert ntfs_acl_to_principals(_acl()) == ()


def test_a_deny_entry_closes_the_document():
    deny = AclEntry("S-1-5-21-1-2-3-1002", "AZIENDA\\bob", DENY, READ)
    assert ntfs_acl_to_principals(_acl(ALICE, deny)) == ()


def test_an_unknown_entry_type_closes_the_document():
    strana = AclEntry("S-1-5-21-1-2-3-1003", "AZIENDA\\carla", OTHER, READ)
    assert ntfs_acl_to_principals(_acl(ALICE, strana)) == ()


@pytest.mark.parametrize(
    "sid",
    ["S-1-1-0", "S-1-5-11", "S-1-5-32-545", "S-1-5-21-111-222-333-513"],
    ids=["Everyone", "Authenticated Users", "BUILTIN Users", "Domain Users"],
)
def test_read_for_everyone_follows_the_library_rules(sid):
    tutti = AclEntry(sid, "gruppo", ALLOW, READ)
    assert ntfs_acl_to_principals(_acl(ALICE, tutti)) is None


def test_system_administrators_and_creator_owner_are_ignored():
    owner = AclEntry("S-1-3-0", "CREATOR OWNER", ALLOW, FULL)
    assert ntfs_acl_to_principals(_acl(SYSTEM, ADMINS, owner, ALICE)) == ("AZIENDA\\alice",)


def test_entries_without_read_are_ignored():
    solo_scrittura = AclEntry("S-1-5-21-1-2-3-1002", "AZIENDA\\bob", ALLOW, WRITE_ONLY)
    assert ntfs_acl_to_principals(_acl(ALICE, solo_scrittura)) == ("AZIENDA\\alice",)


def test_everyone_without_read_does_not_open_the_document():
    tutti_scrittura = AclEntry("S-1-1-0", "Everyone", ALLOW, WRITE_ONLY)
    assert ntfs_acl_to_principals(_acl(ALICE, tutti_scrittura)) == ("AZIENDA\\alice",)


def test_inherit_only_entries_do_not_apply_to_the_file():
    solo_figli = AclEntry("S-1-1-0", "Everyone", ALLOW, READ, INHERIT_ONLY_ACE)
    assert ntfs_acl_to_principals(_acl(ALICE, solo_figli)) == ("AZIENDA\\alice",)


def test_inherit_only_deny_does_not_close_the_file():
    nega_figli = AclEntry("S-1-5-21-1-2-3-1002", "AZIENDA\\bob", DENY, READ, INHERIT_ONLY_ACE)
    assert ntfs_acl_to_principals(_acl(ALICE, nega_figli)) == ("AZIENDA\\alice",)


def test_readers_become_the_allow_list():
    assert ntfs_acl_to_principals(_acl(SYSTEM, ALICE, BOB)) == ("AZIENDA\\alice", "AZIENDA\\bob")


def test_only_non_people_left_closes_the_document():
    assert ntfs_acl_to_principals(_acl(SYSTEM, ADMINS)) == ()


def test_an_orphan_sid_keeps_its_sid_as_name():
    orfano = AclEntry("S-1-5-21-9-9-9-4242", "", ALLOW, READ)
    assert ntfs_acl_to_principals(_acl(orfano)) == ("S-1-5-21-9-9-9-4242",)


# --- Percorso completo: connettore e store veri ---------------------------


class _Storage:
    def save(self, path, content):
        pass

    def delete(self, path):
        pass


@pytest.fixture
def biblioteca(tmp_path, monkeypatch):
    monkeypatch.setattr("core.connector_ingest._known_usernames", lambda: {"alice": "alice", "bob": "bob"})
    store = LibraryStore(tmp_path / "ermes.sqlite3")
    library = store.create_library("Amministrazione", "", "private", owner_id="owner")
    for user in ("alice", "bob"):
        store.set_library_member(library["id"], user, "viewer")
    cartella = tmp_path / "nas"
    cartella.mkdir()
    return store, library["id"], cartella


def _visibili(store, library_id, utente):
    return {d["filename"] for d in store.list_documents(library_id, {"username": utente, "role": "viewer"})}


def _importa(store, library_id, connector):
    for documento in connector.fetch_documents():
        import_remote_document(store, library_id, documento, {}, _Storage(), connector.source_key())


def test_a_file_readable_only_by_alice_is_visible_only_to_alice(biblioteca, monkeypatch):
    store, library_id, cartella = biblioteca
    (cartella / "stipendi.txt").write_text("Stipendi riservati", encoding="utf-8")
    monkeypatch.setattr("core.connectors.local_folder.read_ntfs_acl", lambda path: _acl(SYSTEM, ALICE))

    _importa(store, library_id, LocalFolderConnector({"folder_path": str(cartella)}))

    assert _visibili(store, library_id, "alice") == {"stipendi.txt"}
    assert _visibili(store, library_id, "bob") == set()


def test_unreadable_permissions_hide_the_file_from_members(biblioteca, monkeypatch):
    store, library_id, cartella = biblioteca
    (cartella / "verbale.txt").write_text("Verbale", encoding="utf-8")
    monkeypatch.setattr("core.connectors.local_folder.read_ntfs_acl", lambda path: None)

    _importa(store, library_id, LocalFolderConnector({"folder_path": str(cartella)}))

    assert _visibili(store, library_id, "alice") == set()
    assert _visibili(store, library_id, "bob") == set()


def test_a_file_for_everyone_follows_the_library(biblioteca, monkeypatch):
    store, library_id, cartella = biblioteca
    (cartella / "mensa.txt").write_text("Orari mensa", encoding="utf-8")
    tutti = AclEntry("S-1-1-0", "Everyone", ALLOW, READ)
    monkeypatch.setattr("core.connectors.local_folder.read_ntfs_acl", lambda path: _acl(tutti))

    _importa(store, library_id, LocalFolderConnector({"folder_path": str(cartella)}))

    assert _visibili(store, library_id, "alice") == {"mensa.txt"}
    assert _visibili(store, library_id, "bob") == {"mensa.txt"}


def test_a_permission_removed_at_the_source_disappears_at_the_next_sync(biblioteca, monkeypatch):
    store, library_id, cartella = biblioteca
    (cartella / "progetto.txt").write_text("Progetto", encoding="utf-8")
    acl = {"valore": _acl(ALICE, BOB)}
    monkeypatch.setattr("core.connectors.local_folder.read_ntfs_acl", lambda path: acl["valore"])
    connector = LocalFolderConnector({"folder_path": str(cartella)})

    _importa(store, library_id, connector)
    assert _visibili(store, library_id, "bob") == {"progetto.txt"}

    acl["valore"] = _acl(ALICE)
    for documento in connector.fetch_documents():
        import_remote_document(
            store, library_id, documento, store.content_hash_index(library_id), _Storage(), connector.source_key()
        )

    assert _visibili(store, library_id, "bob") == set()
    assert _visibili(store, library_id, "alice") == {"progetto.txt"}


def test_inherit_permissions_can_be_turned_off(biblioteca, monkeypatch):
    store, library_id, cartella = biblioteca
    (cartella / "libero.txt").write_text("Libero", encoding="utf-8")
    monkeypatch.setattr("core.connectors.local_folder.read_ntfs_acl", lambda path: None)

    _importa(store, library_id, LocalFolderConnector({"folder_path": str(cartella), "inherit_permissions": False}))

    assert _visibili(store, library_id, "bob") == {"libero.txt"}


def test_test_connection_warns_when_permissions_cannot_be_read(tmp_path, monkeypatch):
    monkeypatch.setattr("core.connectors.local_folder.ntfs_permissions_readable", lambda: False)
    ok, messaggio = LocalFolderConnector({"folder_path": str(tmp_path)}).test_connection()
    assert ok
    assert "chiusi" in messaggio


# --- Solo Windows: un file vero -------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="permessi NTFS solo su Windows")
def test_reading_the_real_permissions_of_a_file(tmp_path):
    file = tmp_path / "riservato.txt"
    file.write_text("Riservato", encoding="utf-8")
    utente = os.environ.get("USERNAME", "")
    # Toglie l'ereditarieta' e lascia la lettura al solo utente corrente.
    subprocess.run(
        ["icacls", str(file), "/inheritance:r", "/grant:r", f"{utente}:(R)"],
        check=True,
        capture_output=True,
    )

    acl = read_ntfs_acl(file)

    assert acl is not None
    principals = ntfs_acl_to_principals(acl)
    assert principals is not None
    assert len(principals) == 1
    assert principals[0].lower().endswith("\\" + utente.lower())
