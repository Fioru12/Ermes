"""
core/connectors/base.py
Base abstractions for Enterprise Cloud Connectors in Ermes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class RemoteDocument:
    id: str
    name: str
    content: bytes
    media_type: str
    source_url: str
    last_modified: str
    metadata: dict[str, Any] = field(default_factory=dict)
    # Chi vede il file sull'origine (email, DOMINIO\\utente, nome utente).
    # None: il connettore non lo sa, o l'origine dice "tutti" — il documento
    # segue le regole della biblioteca. Vuoto: nessuno e' traducibile, il
    # documento resta al proprietario e agli amministratori. Vedi
    # core/connector_ingest.py.
    allowed_principals: tuple[str, ...] | None = None


@dataclass(frozen=True)
class ListingReport:
    """Cosa ha visto l'ultima scansione completa (`fetch_documents`).

    Serve a togliere da Ermes i file spariti dall'origine. `seen_ids` contiene
    l'id di ogni file che rispetta i filtri del connettore, anche se il suo
    download e' fallito: un file illeggibile non e' un file cancellato.
    `complete` e' vero solo se l'origine e' stata elencata tutta, senza errori
    e senza superare `max_files`. Con un elenco incompleto non si cancella
    niente.
    """

    seen_ids: frozenset[str]
    complete: bool


@dataclass(frozen=True)
class SyncResult:
    connector_type: str
    total_found: int
    synced_count: int
    errors: list[str] = field(default_factory=list)
    synced_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True)
class DeltaSyncResult:
    connector_type: str
    updated_documents: list[RemoteDocument]
    deleted_document_ids: list[str] = field(default_factory=list)
    next_delta_token: str | None = None
    errors: list[str] = field(default_factory=list)
    synced_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class BaseConnector(ABC):
    """Abstract base class for all enterprise content connectors."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        # Impostato da fetch_documents nei connettori che sanno dire se hanno
        # elencato tutta l'origine. None: il connettore non lo sa, e i file
        # spariti dall'origine non vengono tolti dopo una scansione completa.
        self.listing: ListingReport | None = None

    def source_key(self) -> str:
        """Identifica l'origine (quale cartella, quale bucket) dentro una biblioteca.

        Due origini dello stesso tipo nella stessa biblioteca devono avere
        chiavi diverse, altrimenti la scansione dell'una toglierebbe i file
        dell'altra. Il valore predefinito va bene per i connettori i cui id
        sono unici a livello globale (Google Drive, Microsoft 365). Non deve
        contenere credenziali.
        """
        return self.__class__.__name__

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Verify authentication and reachability to the remote source."""
        pass

    @abstractmethod
    def fetch_documents(self) -> list[RemoteDocument]:
        """Fetch updated documents from the remote source."""
        pass

    def fetch_delta(self, delta_token: str | None = None) -> DeltaSyncResult:
        """Fetch incremental changes (new/updated documents and deleted document ids) since delta_token.

        Connectors without native cursor/delta token APIs fall back to full scan.
        """
        try:
            docs = self.fetch_documents()
            return DeltaSyncResult(
                connector_type=self.__class__.__name__,
                updated_documents=docs,
                deleted_document_ids=[],
                next_delta_token=None,
            )
        except Exception as e:
            return DeltaSyncResult(
                connector_type=self.__class__.__name__,
                updated_documents=[],
                deleted_document_ids=[],
                next_delta_token=delta_token,
                errors=[str(e)],
            )
