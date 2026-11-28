"""
core/connectors/local_folder.py
Local Shared Folder / NAS Network Drive Connector for Ermes Knowledge.
Scans local directories or mounted SMB/NFS network drives for supported documents.

Permessi: con ``inherit_permissions`` (attivo di default) ogni file porta con
se' chi lo puo' leggere sulla condivisione (permessi NTFS, vedi
core/connectors/ntfs_permissions.py). Se i permessi non si leggono — Ermes
non su Windows, pywin32 assente, accesso negato — il documento resta chiuso:
visibile solo al proprietario della biblioteca e agli amministratori. Vale
anche per le cartelle collegate prima di questa funzione (decisione del 28
novembre 2026). ``inherit_permissions: false`` lo spegne: i documenti seguono
le regole della biblioteca.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import sys
from pathlib import Path
from typing import Any

from core.connectors.base import BaseConnector, ListingReport, RemoteDocument
from core.connectors.ntfs_permissions import ntfs_acl_to_principals, read_ntfs_acl

_logger = logging.getLogger(__name__)


def ntfs_permissions_readable() -> bool:
    """Vero se su questa macchina si possono leggere i permessi NTFS."""
    if sys.platform != "win32":
        return False
    try:
        import win32security  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        return False
    return True

MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".csv": "text/csv",
    ".rtf": "application/rtf",
    ".eml": "message/rfc822",
}

SUPPORTED_EXTENSIONS = set(MEDIA_TYPES.keys())


class LocalFolderConnector(BaseConnector):
    """
    Connettore per scansione ed estrazione da cartelle locali o mount NAS (SMB/NFS).
    """

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.folder_path = Path(config.get("folder_path", "")).expanduser().resolve()
        self.max_files = int(config.get("max_files", 200))
        self.recursive = bool(config.get("recursive", True))
        self.allowed_extensions = set(config.get("extensions", list(SUPPORTED_EXTENSIONS)))
        self.inherit_permissions = bool(config.get("inherit_permissions", True))

    def source_key(self) -> str:
        return f"local_folder:{self.folder_path}"

    def test_connection(self) -> tuple[bool, str]:
        if not str(self.folder_path):
            return False, "Percorso cartella non specificato"

        if not self.folder_path.exists():
            return False, f"Il percorso non esiste: {self.folder_path}"

        if not self.folder_path.is_dir():
            return False, f"Il percorso non è una directory: {self.folder_path}"

        if not os.access(self.folder_path, os.R_OK):
            return False, f"Permesso di lettura negato per: {self.folder_path}"

        if self.inherit_permissions and not ntfs_permissions_readable():
            return True, (
                f"Cartella raggiungibile e leggibile ({self.folder_path}), ma i permessi NTFS non si possono leggere"
                " su questa installazione: i documenti resteranno chiusi (visibili solo al proprietario della"
                " biblioteca e agli amministratori). Ermes deve girare su Windows per ereditarli."
            )
        return True, f"Cartella raggiungibile e leggibile ({self.folder_path})"

    def fetch_documents(self) -> list[RemoteDocument]:
        self.listing = None
        ok, msg = self.test_connection()
        if not ok:
            _logger.warning("LocalFolderConnector test_connection fallito: %s", msg)
            return []

        documents: list[RemoteDocument] = []
        seen: set[str] = set()
        complete = True
        walker = self.folder_path.rglob("*") if self.recursive else self.folder_path.glob("*")

        try:
            for file_path in walker:
                if not file_path.is_file():
                    continue

                ext = file_path.suffix.lower()
                if ext not in self.allowed_extensions:
                    continue

                if len(documents) >= self.max_files:
                    _logger.info("Raggiunto il limite massimo di %d file", self.max_files)
                    complete = False
                    break

                rel_path = str(file_path.relative_to(self.folder_path))
                doc_id = f"local_folder:{rel_path}"
                seen.add(doc_id)
                document = self._read_file(file_path, ext, rel_path, doc_id)
                if document is not None:
                    documents.append(document)
        except OSError as error:
            # Una sottocartella illeggibile o la condivisione che si stacca a
            # meta' scansione: l'elenco non e' completo.
            _logger.warning("Scansione di %s interrotta: %s", self.folder_path, error)
            complete = False

        self.listing = ListingReport(seen_ids=frozenset(seen), complete=complete)
        return documents

    def _read_file(self, file_path: Path, ext: str, rel_path: str, doc_id: str) -> RemoteDocument | None:
        try:
            stat = file_path.stat()
            content = file_path.read_bytes()
            media_type = MEDIA_TYPES.get(ext)
            if not media_type:
                guessed, _ = mimetypes.guess_type(file_path.name)
                media_type = guessed or "application/octet-stream"

            principals = ntfs_acl_to_principals(read_ntfs_acl(file_path)) if self.inherit_permissions else None
            return RemoteDocument(
                id=doc_id,
                name=file_path.name,
                content=content,
                media_type=media_type,
                source_url=f"file://{file_path}",
                last_modified=str(int(stat.st_mtime)),
                metadata={
                    "relative_path": rel_path,
                    "absolute_path": str(file_path),
                    "file_size": stat.st_size,
                    "extension": ext,
                },
                allowed_principals=principals,
            )
        except Exception as e:
            _logger.error("Errore durante la lettura del file %s: %s", file_path, e)
            return None
