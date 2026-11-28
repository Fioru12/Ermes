"""Importazione di un documento arrivato da un connettore, con i permessi dell'origine.

Prima del 28 ottobre 2026 lo stesso ciclo era scritto quattro volte (sync
completa e incrementale dell'API, e le due dello scheduler) e nessuna delle
quattro guardava chi potesse vedere il file sull'origine: un documento che
su SharePoint vedevano in tre diventava visibile a tutta la biblioteca.

Regole dei permessi
-------------------
- ``RemoteDocument.allowed_principals is None``: il connettore non sa (o
  l'origine dice "tutti", come un link aperto all'organizzazione). Il
  documento segue le regole della biblioteca, come un caricamento manuale.
- Altrimenti e' l'elenco di chi lo vede sull'origine (email, ``DOMINIO\\utente``
  o nomi utente). Diventa la allow-list per documento gia' esistente
  (``document_acls``): un nome si abbina a un utente Ermes senza distinguere
  maiuscole, e ``DOMINIO\\utente`` vale ``utente``. Chi non e' ancora un
  utente Ermes resta nell'elenco: e' cosi' che gli utenti SSO, creati al
  primo accesso, ritrovano i loro documenti.
- Elenco vuoto o permessi illeggibili: il documento resta visibile solo al
  proprietario della biblioteca e agli amministratori. Un permesso che non si
  riesce a tradurre chiude, non apre.
- I permessi si scrivono nella stessa transazione del documento: non c'e'
  un istante in cui un file riservato e' aperto a tutta la biblioteca.
- Un file gia' importato (stesso contenuto) riceve comunque i permessi
  attuali: un accesso tolto sull'origine sparisce alla sincronizzazione
  successiva anche se il file non e' cambiato.

File cancellati o modificati all'origine
----------------------------------------
- Ogni documento importato da un connettore e' collegato al suo id remoto
  (tabella ``connector_documents``, per biblioteca e origine). Senza questo
  collegamento le cancellazioni segnalate dai connettori non trovavano il
  documento, e un file modificato diventava un secondo documento accanto alla
  versione vecchia, che restava cercabile.
- Un file modificato sostituisce la versione vecchia: il documento vecchio
  viene tolto, se nessun altro file remoto vi e' collegato.
- Un file cancellato (segnalato dal delta del connettore, o assente da una
  scansione completa che il connettore dichiara completa) toglie il suo
  documento. Con un elenco incompleto (limite di file, errore di rete,
  cartella irraggiungibile) non si toglie niente.
- I caricamenti manuali non sono mai collegati e non vengono mai tolti. Per
  questo un file remoto identico a un documento non collegato non viene
  collegato a quel documento: puo' essere un caricamento manuale. Limite
  noto: i documenti importati dai connettori prima di questo collegamento
  restano non collegati e vanno tolti a mano se spariscono dall'origine.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from core.connectors.base import ListingReport, RemoteDocument
from core.document_parser import extract_source_units
from core.library_store import LibraryNotFoundError, LibraryStore, storage_relative_path

_logger = logging.getLogger(__name__)


def _known_usernames() -> dict[str, str]:
    """Nomi degli account locali, per restituire la grafia esatta di Ermes."""
    try:
        from config import cfg
        from core.governance import list_users

        return {str(u["username"]).lower(): str(u["username"]) for u in list_users(cfg.USERS_FILE) if u.get("username")}
    except Exception as error:  # l'elenco serve solo alla grafia: senza, si usa il nome dell'origine
        _logger.warning("Elenco utenti non leggibile per i permessi dei connettori: %s", error)
        return {}


def resolve_principals(principals: tuple[str, ...] | list[str], known: dict[str, str]) -> list[str]:
    """Traduce i nomi dell'origine in nomi utente Ermes."""
    resolved = set()
    for principal in principals:
        name = str(principal or "").strip()
        if "\\" in name:
            name = name.rsplit("\\", 1)[1]
        if name:
            resolved.add(known.get(name.lower(), name))
    return sorted(resolved)


def source_allow_list(store: LibraryStore, library_id: str, document: RemoteDocument) -> list[str] | None:
    """La allow-list per il documento, None se segue le regole della biblioteca."""
    if document.allowed_principals is None:
        return None
    users = resolve_principals(document.allowed_principals, _known_usernames())
    if users:
        return users
    _logger.warning(
        "Permessi di %s non traducibili: visibile solo al proprietario della biblioteca e agli amministratori",
        document.name,
    )
    owner = str(store.get_library(library_id).get("owner_id", "") or "")
    # Il proprietario vede comunque i documenti della sua biblioteca: basta
    # che l'elenco non sia vuoto, perche' un elenco vuoto toglie il vincolo.
    return [owner or "-"]


def import_remote_document(
    store: LibraryStore,
    library_id: str,
    document: RemoteDocument,
    hash_index: dict[str, str],
    storage_provider: Any,
    source_key: str | None = None,
) -> str:
    """Importa un documento remoto. Restituisce "imported" o "duplicate".

    `hash_index` (impronta del contenuto -> id del documento) viene aggiornato,
    cosi' lo stesso file presente due volte nella stessa sincronizzazione
    viene importato una volta sola.

    Con `source_key` il documento viene collegato al suo id remoto, e la
    versione precedente dello stesso file remoto, se diversa, viene tolta.
    """
    allow_list = source_allow_list(store, library_id, document)
    linked_before = store.remote_document(library_id, source_key, document.id) if source_key else None
    digest = hashlib.sha256(document.content).hexdigest()
    existing = hash_index.get(digest)
    if existing:
        if allow_list is not None:
            store.set_document_acl(library_id, existing, allow_list)
        if source_key and store.remote_link_count(existing) > 0:
            _link(store, library_id, source_key, document.id, existing, storage_provider)
        return "duplicate"

    units = extract_source_units(document.name, document.content)
    chunks = [(unit.text, unit.locator) for unit in units]
    if not chunks or not chunks[0][0]:
        chunks = [(document.name, "Titolo")]

    stored_rel = storage_relative_path(library_id, f"{digest[:12]}_{document.name}")
    storage_provider.save(stored_rel, document.content)
    created = store.add_document(
        library_id=library_id,
        filename=document.name,
        media_type=document.media_type,
        content=document.content,
        storage_path=stored_rel,
        status="ready",
        chunks=chunks,
        allowed_usernames=allow_list,
    )
    hash_index[digest] = created["id"]
    if source_key:
        if int(created.get("version", 1)) == 1 or linked_before == created["id"]:
            _link(store, library_id, source_key, document.id, created["id"], storage_provider)
        else:
            # add_document unisce per nome: il file remoto e' diventato una
            # nuova versione di un documento che non era suo (un caricamento
            # manuale o un file di un'altra origine con lo stesso nome). Non lo
            # si collega, cosi' una cancellazione all'origine non lo toglie.
            _logger.warning(
                "%s ha lo stesso nome di un documento non importato da questa origine: aggiunto come nuova versione,"
                " non verra' tolto se sparisce dall'origine",
                document.name,
            )
    return "imported"


def _link(
    store: LibraryStore, library_id: str, source_key: str, remote_id: str, document_id: str, storage_provider: Any
) -> None:
    previous = store.link_remote_document(library_id, source_key, remote_id, document_id)
    if previous:
        _delete_if_orphan(store, library_id, previous, storage_provider)


def _delete_if_orphan(store: LibraryStore, library_id: str, document_id: str, storage_provider: Any) -> bool:
    """Toglie il documento se nessun file remoto vi e' piu' collegato."""
    if store.remote_link_count(document_id) > 0:
        return False
    try:
        paths = store.delete_document(library_id, document_id)
    except LibraryNotFoundError:
        return False  # gia' tolto, per esempio a mano
    for path in paths:
        try:
            storage_provider.delete(path)
        except Exception as error:  # il documento non e' piu' cercabile: il file resta solo su disco
            _logger.warning("File originale %s non rimosso: %s", path, error)
    return True


def remove_remote_documents(
    store: LibraryStore, library_id: str, source_key: str, remote_ids: list[str], storage_provider: Any
) -> int:
    """Toglie i documenti dei file cancellati all'origine. Restituisce quanti ne ha tolti."""
    removed = 0
    for remote_id in remote_ids:
        document_id = store.unlink_remote_document(library_id, source_key, remote_id)
        if document_id and _delete_if_orphan(store, library_id, document_id, storage_provider):
            removed += 1
    return removed


def prune_missing_documents(store: LibraryStore, library_id: str, connector: Any, storage_provider: Any) -> int:
    """Dopo una scansione completa, toglie i documenti dei file non piu' presenti.

    Non fa niente se il connettore non dichiara un elenco completo
    (``connector.listing``): un elenco parziale non dice cosa e' stato
    cancellato.
    """
    listing: ListingReport | None = getattr(connector, "listing", None)
    if listing is None or not listing.complete:
        return 0
    source_key = connector.source_key()
    missing = [
        remote_id for remote_id in store.remote_documents(library_id, source_key) if remote_id not in listing.seen_ids
    ]
    return remove_remote_documents(store, library_id, source_key, missing, storage_provider)
