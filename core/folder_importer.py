"""Importazione documenti da cartelle registrate (Modello A).

Filosofia: i diritti sulle cartelle li ha l'account con cui gira Ermes, NON
gli utenti. Qui non vengono mai salvate credenziali: solo il percorso. La
scansione importa i file supportati (.txt/.pdf/.docx/.md/.xlsx/.pptx/.csv/.rtf),
salta i duplicati per
hash del contenuto e registra gli errori senza interrompere il batch.

Permessi: ogni file porta con se' chi lo puo' leggere sulla condivisione
(permessi NTFS), con le stesse regole del connettore cartelle
(core/connectors/ntfs_permissions.py). Permessi illeggibili chiudono il
documento. Un file gia' importato e non cambiato riceve comunque i permessi
attuali. Si spegne con ERMES_FOLDER_SOURCES_INHERIT_PERMISSIONS=0.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from core.connectors.ntfs_permissions import ntfs_acl_to_principals, read_ntfs_acl
from core.library_store import storage_relative_path

SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf", ".docx", ".xlsx", ".pptx", ".csv", ".rtf", ".eml"}

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

MAX_IMPORT_FILE_BYTES = 50 * 1024 * 1024  # allineato a un limite prudenziale


def scan_import_source(
    store,
    library_id: str,
    source: dict,
    storage_dir: str,
) -> dict:
    """Scan one registered folder and import new documents.

    Returns counts so the API can report exactly what happened. A file that
    cannot be read is counted as failed, never fatal for the rest of the batch.

    `storage_dir` was accepted but never used: this called store.add_document
    with a storage_path pointing under Ermes' own storage tree, but never
    actually copied the file's bytes there — add_document only records
    metadata, it does not write to disk (the upload endpoint in
    api/libraries.py writes the file itself before calling add_document).
    Every scan "succeeded" (imported: [...]), and every one of those imports
    then failed ingestion with "Originale non disponibile", because the row
    pointed at a file that was never created. Found by actually running the
    feature through the browser, not by reading the code.
    """
    root = Path(source["path"])
    result = {"path": source["path"], "imported": [], "skipped_duplicates": [], "skipped_unsupported": [], "failed": []}
    if not root.exists() or not root.is_dir():
        result["failed"].append({"file": str(root), "error": "Cartella non raggiungibile dall'account del server"})
        return result

    from config import cfg
    from core.connector_ingest import principals_allow_list

    inherit = bool(getattr(cfg, "FOLDER_SOURCES_INHERIT_PERMISSIONS", True))
    hash_to_document = store.content_hash_index(library_id)
    known_hashes = set(hash_to_document)
    all_files = sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: str(p).lower())
    files = []
    for candidate in all_files:
        if candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(candidate)
        else:
            result["skipped_unsupported"].append(candidate.name)
    for file_path in files:
        try:
            if file_path.stat().st_size > MAX_IMPORT_FILE_BYTES:
                result["failed"].append({"file": file_path.name, "error": "File troppo grande"})
                continue
            content = file_path.read_bytes()
            if not content:
                result["failed"].append({"file": file_path.name, "error": "File vuoto"})
                continue

            from core.antivirus import AntivirusScanError, scan_document

            try:
                scan_res = scan_document(content, filename=file_path.name, actor="folder_importer")
                if not scan_res.is_clean:
                    virus = scan_res.virus_name or "minaccia rilevata"
                    result["failed"].append({"file": file_path.name, "error": f"File malevolo bloccato ({virus})"})
                    continue
            except AntivirusScanError as scan_err:
                result["failed"].append(
                    {"file": file_path.name, "error": f"Servizio antivirus non disponibile: {scan_err}"}
                )
                continue

            allow_list = (
                principals_allow_list(
                    store, library_id, ntfs_acl_to_principals(read_ntfs_acl(file_path)), file_path.name
                )
                if inherit
                else None
            )
            digest = hashlib.sha256(content).hexdigest()
            if digest in known_hashes:
                # Il file non e' cambiato, i permessi forse si': un accesso
                # tolto sulla condivisione deve sparire anche qui.
                existing = hash_to_document.get(digest)
                if allow_list is not None and existing:
                    store.set_document_acl(library_id, existing, allow_list)
                result["skipped_duplicates"].append(file_path.name)
                continue
            extension = file_path.suffix.lower()
            stored_filename = f"{digest[:12]}_{file_path.name}"
            destination = Path(storage_dir) / library_id / stored_filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            document = store.add_document(
                library_id=library_id,
                filename=file_path.name,
                media_type=MEDIA_TYPES[extension],
                content=content,
                storage_path=storage_relative_path(library_id, stored_filename),
                status="queued",
                chunks=[],
                allowed_usernames=allow_list,
            )
            job = store.start_ingestion_job(library_id, file_path.name, document_id=document["id"])
            known_hashes.add(digest)
            hash_to_document[digest] = document["id"]
            result["imported"].append({"filename": file_path.name, "document_id": document["id"], "job_id": job["id"]})
        except Exception as error:  # un file corrotto non ferma la scansione
            result["failed"].append({"file": file_path.name, "error": str(error)})
    store.touch_import_source(library_id, source["id"])
    return result
