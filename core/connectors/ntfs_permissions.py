"""Permessi NTFS dei file delle cartelle di rete, tradotti per Ermes.

Un file che sulla condivisione vedono in pochi non deve diventare visibile a
tutta la biblioteca perche' e' arrivato dal connettore cartelle. La lettura
dei permessi (``read_ntfs_acl``) usa pywin32 e funziona solo su Windows; la
traduzione (``ntfs_acl_to_principals``) e' pura e si prova ovunque.

Regole di traduzione, nell'ordine in cui si applicano:

- lettura fallita, o non su Windows: chiuso (tupla vuota). Un permesso che
  non si riesce a leggere chiude, non apre;
- DACL nulla: Windows da' accesso a chiunque, quindi ``None`` (il documento
  segue le regole della biblioteca);
- una voce di tipo diverso da "consenti" o "nega" (voci oggetto, callback,
  condizionali): chiuso, perche' non si sa valutarla;
- almeno una voce "nega": chiuso. Valutare un divieto insieme ai gruppi in
  modo sicuro richiederebbe di conoscere i membri dei gruppi;
- una voce "consenti" che concede la lettura a un gruppo che comprende tutti
  (Everyone, Authenticated Users, BUILTIN\\Users, Domain Users): ``None``;
- voci per SYSTEM, Administrators e CREATOR OWNER: ignorate. Non sono persone,
  e gli amministratori di Ermes vedono comunque tutto;
- voci che non concedono la lettura, o che valgono solo per i figli
  (INHERIT_ONLY): ignorate;
- le altre voci "consenti" con lettura: il loro nome (``DOMINIO\\nome``)
  entra nell'elenco;
- se alla fine l'elenco e' vuoto: chiuso.

Limite noto: un gruppo NTFS (per esempio ``AZIENDA\\Contabilita``) vale solo se
esiste un utente Ermes con lo stesso nome. I gruppi non vengono espansi nei
loro membri.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

_logger = logging.getLogger(__name__)

ALLOW = "allow"
DENY = "deny"
OTHER = "other"

# Gruppi che comprendono tutti gli utenti: un file che leggono loro non ha
# vincoli oltre a quelli della biblioteca.
_EVERYONE_SIDS = frozenset(
    {
        "S-1-1-0",  # Everyone
        "S-1-5-11",  # Authenticated Users
        "S-1-5-32-545",  # BUILTIN\Users
    }
)
# Domain Users: S-1-5-21-<dominio>-513.
_DOMAIN_USERS_SUFFIX = "-513"

# Identita' che non sono persone da abilitare in Ermes.
_IGNORED_SIDS = frozenset(
    {
        "S-1-5-18",  # SYSTEM
        "S-1-5-32-544",  # BUILTIN\Administrators
        "S-1-3-0",  # CREATOR OWNER
    }
)

# Bit che concedono di leggere il contenuto del file.
FILE_READ_DATA = 0x0001
GENERIC_ALL = 0x10000000
GENERIC_READ = 0x80000000
_READ_BITS = FILE_READ_DATA | GENERIC_ALL | GENERIC_READ

# Flag di una voce che vale solo per gli oggetti figli, non per il file.
INHERIT_ONLY_ACE = 0x08


@dataclass(frozen=True)
class AclEntry:
    """Una voce della DACL di un file."""

    sid: str
    name: str
    kind: str  # ALLOW, DENY o OTHER
    access_mask: int
    flags: int = 0


@dataclass(frozen=True)
class NtfsAcl:
    """La DACL di un file. ``null_dacl`` vero vuol dire nessuna restrizione."""

    entries: tuple[AclEntry, ...]
    null_dacl: bool = False


def _is_everyone(sid: str) -> bool:
    return sid in _EVERYONE_SIDS or (sid.startswith("S-1-5-21-") and sid.endswith(_DOMAIN_USERS_SUFFIX))


def ntfs_acl_to_principals(acl: NtfsAcl | None) -> tuple[str, ...] | None:
    """Traduce la DACL di un file in ``allowed_principals`` (vedi le regole in testa)."""
    if acl is None:
        return ()
    if acl.null_dacl:
        return None

    applicable = [entry for entry in acl.entries if not entry.flags & INHERIT_ONLY_ACE]
    if any(entry.kind not in (ALLOW, DENY) for entry in applicable):
        return ()
    if any(entry.kind == DENY for entry in applicable):
        return ()

    readers = [entry for entry in applicable if entry.access_mask & _READ_BITS]
    if any(_is_everyone(entry.sid) for entry in readers):
        return None

    names = sorted({entry.name or entry.sid for entry in readers if entry.sid not in _IGNORED_SIDS})
    return tuple(names)


def read_ntfs_acl(path: Path) -> NtfsAcl | None:
    """Legge la DACL effettiva del file, comprese le voci ereditate.

    Restituisce None se non si riesce: non su Windows, pywin32 assente,
    accesso negato, file sparito. Il chiamante tratta None come "chiuso".
    """
    if sys.platform != "win32":
        return None
    try:
        import ntsecuritycon  # type: ignore[import-not-found]  # noqa: F401  (pywin32, solo Windows)
        import win32security  # type: ignore[import-not-found]
    except ImportError:
        _logger.warning("pywin32 non installato: i permessi NTFS non si possono leggere")
        return None

    try:
        descriptor = win32security.GetFileSecurity(str(path), win32security.DACL_SECURITY_INFORMATION)
        dacl = descriptor.GetSecurityDescriptorDacl()
    except Exception as error:
        _logger.warning("Permessi NTFS di %s non leggibili: %s", path, error)
        return None

    if dacl is None:
        return NtfsAcl(entries=(), null_dacl=True)

    entries: list[AclEntry] = []
    try:
        for index in range(dacl.GetAceCount()):
            ace = dacl.GetAce(index)
            (ace_type, ace_flags), access_mask, sid = ace[0], ace[1], ace[-1]
            if ace_type == win32security.ACCESS_ALLOWED_ACE_TYPE:
                kind = ALLOW
            elif ace_type == win32security.ACCESS_DENIED_ACE_TYPE:
                kind = DENY
            else:
                kind = OTHER
            sid_text = win32security.ConvertSidToStringSid(sid)
            entries.append(AclEntry(sid_text, _account_name(win32security, sid), kind, int(access_mask), int(ace_flags)))
    except Exception as error:
        _logger.warning("Permessi NTFS di %s non interpretabili: %s", path, error)
        return None
    return NtfsAcl(entries=tuple(entries))


def _account_name(win32security, sid) -> str:  # type: ignore[no-untyped-def]
    """``DOMINIO\\nome`` dell'account, o stringa vuota per un SID orfano."""
    try:
        name, domain, _kind = win32security.LookupAccountSid(None, sid)
    except Exception:
        return ""
    return f"{domain}\\{name}" if domain else str(name)
