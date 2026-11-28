# Fasi di lavoro dopo l'esame (da dicembre 2026)

Questo documento è scritto per **qualunque assistente AI** (o persona) che lavori
su Ermes. Va seguito alla lettera. Se un'istruzione qui non è chiara, o la
realtà del codice non corrisponde a quello che c'è scritto, **fermati e chiedi a
Nicolò**: non indovinare.

Scritto il 18 novembre 2026. Il lavoro inizia **dopo l'esame orale del 26
novembre 2026**. Prima di quella data non si tocca il codice.

Il piano strategico, con il perché di ogni voce, è in
[`PIANO_EVOLUZIONE_E_BENCHMARK.md`](PIANO_EVOLUZIONE_E_BENCHMARK.md) (sezione 4).
Questo file è la versione operativa: cosa fare, in che ordine, come capire che è
finito. I numeri tra parentesi, come **(1.6)**, rimandano alle voci di quel piano.

Le idee prese da altri progetti RAG (RAGFlow, Onyx, Open WebUI, Kotaemon), con
licenze e posizione nel loro codice, sono in
[`CATALOGO_IDEE_COMPETITOR.md`](CATALOGO_IDEE_COMPETITOR.md). Le sigle come
**C-03** rimandano a quel catalogo.

---

## Come usare questo documento

1. Leggi tutta la sezione **Regole sempre valide** prima di qualsiasi lavoro.
2. Guarda la tabella **Stato** e prendi **la prima fase non completata**.
   Non saltare fasi e non lavorare su due fasi insieme.
3. Dentro una fase, fai **un passo alla volta**, nell'ordine scritto.
4. Ogni passo ha la stessa struttura:
   - **Obiettivo**: cosa deve essere vero alla fine.
   - **Leggi prima**: i file da aprire *prima* di scrivere codice.
   - **Cosa fare**: i passi concreti.
   - **Non fare**: errori già visti o scelte già scartate.
   - **Verifica**: i comandi da eseguire e cosa devono dare.
   - **Fatto quando**: la condizione per considerarlo chiuso.
   - **STOP**: i punti in cui devi fermarti e chiedere a Nicolò.
5. A passo finito, aggiorna la tabella **Stato** in questo file, nella stessa PR.

---

## Regole sempre valide

### Git e GitHub
- `main` è protetto: **non si fa mai push su `main`**. Ogni lavoro va su un
  branch nuovo (`feat/...`, `fix/...`, `docs/...`) e diventa una pull request.
- **Non fare mai merge** di una PR senza che Nicolò lo abbia detto in chat.
- I controlli CI obbligatori sono: test, lint, frontend, secrets, compose-smoke.
  Una PR con CI rossa non è finita.
- Una PR = una cosa. Non mescolare refactoring, dipendenze e funzioni nuove.
- Non riscrivere la storia (`push --force`, `rebase` su branch condivisi).

### Comandi di verifica (PowerShell, dalla cartella del progetto)

Test Python, con le stesse variabili della CI:

```powershell
$env:ERMES_API_KEY="test-key-123"; $env:ERMES_BACKUP_ENABLED="0"; .\.venv-ermes\Scripts\python.exe -m pytest tests/ -q
```

Lint e tipi, come in CI:

```powershell
.\.venv-ermes\Scripts\python.exe -m ruff check .
```

```powershell
.\.venv-ermes\Scripts\python.exe -m mypy api/ core/ config/ scripts/ --ignore-missing-imports --explicit-package-bases
```

Frontend (solo se hai toccato `frontend/`):

```powershell
cd frontend; npm run lint; npm run build; npm test
```

### Onestà e numeri
- **Non abbassare mai** le soglie in `tests/test_library_evaluation.py` per far
  passare la CI. Se un numero scende, il codice è peggiorato: si corregge il
  codice, o si chiede.
- **Non cambiare un default** (modalità di ricerca, modello, soglie) senza una
  misura che lo giustifichi, scritta in `docs/RETRIEVAL_EVALUATION.md`.
- Ogni numero scritto nei documenti deve venire da un comando eseguito davvero.
  Se una misura non è stata fatta, scrivi "non misurato".
- Se uno script di valutazione dice `semantic_search_active: false` o
  `evidence_verification_active: false`, **quella misura non vale** per la
  configurazione che volevi provare. Non pubblicarla come se valesse.
- Nel README e nei documenti niente promesse come "certificato", "zero
  allucinazioni", "livello bancario".

### Sicurezza
- Mai stampare, copiare o committare segreti (`.env`, `.env.monitoring`, chiavi API).
- Un permesso che non si riesce a leggere o tradurre **chiude** il documento,
  non lo apre. Vale per ogni connettore.
- I test usano il codice vero (per esempio un `LibraryStore` su un SQLite
  temporaneo), non finti oggetti al posto del codice che stanno provando.
- Non indebolire controlli esistenti (password "admin" rifiutata su 0.0.0.0, CSP,
  antivirus sugli upload) per far funzionare qualcosa.

### Cose da non toccare
- La tesina, le slide e i file in `Desktop\File Finali`.
- `Ermes.exe` non è nel repository: si ricostruisce con `scripts/build_exe.ps1`.
- Non reintrodurre LlamaIndex, ChromaDB o altri framework RAG:
  `tests/test_legacy_packages_stay_out.py` lo impedisce, e la scelta è
  spiegata in `docs/adr/0003-sqlite-default-postgres-optional.md`.

### Dipendenze nuove
- Ogni pacchetto nuovo va in `requirements.txt` con versione fissata (`==`).
- Dopo averlo aggiunto, rigenera le note di terze parti con
  `scripts/generate_third_party_notices.py` e controlla che la licenza sia
  compatibile con GPL-3.0.
- Se il pacchetto serve solo su Windows, usa il marcatore
  `; sys_platform == "win32"`: la CI gira su Linux.

---

## Stato

| Fase | Contenuto | Stato |
|---|---|---|
| 0 | Misurare ibrida + verifica sulla suite PMI | da fare |
| 1 | Permessi NTFS nel connettore cartelle | in PR (28 novembre 2026): mancano la prova su una condivisione vera (1.4), le fonti con Folder Watcher (1.7) e Confluence |
| 2 | Installer senza prerequisiti | da fare |
| 3 | Utenti pilota e domande vere nel gold set | da fare |
| 4 | Qualità del recupero (reranker, contesto, riformulazioni) | da fare |
| 5 | Email: file `.msg` e connettore IMAP | da fare |
| 6 | Evidenziazione nel PDF e migrazioni dello schema | da fare |
| 7 | Pulizia del codice (lint, controlli prima del commit) | da fare, in parallelo |

Valori ammessi: `da fare`, `in corso (branch ...)`, `in PR (#...)`, `fatto (data)`,
`bloccato (motivo)`.

**Perché quest'ordine.** La fase 0 costa poco e decide se la strada della qualità
funziona. La fase 1 viene prima dell'installer perché senza permessi NTFS non si
può collegare in sicurezza la cartella di rete di un'azienda vera, che è il primo
uso reale previsto. Il piano strategico mette l'installer prima dei permessi: se
Nicolò sceglie quell'ordine, scambia le righe 1 e 2 e prosegui.

---

## Fase 0 — Misurare ibrida + verifica sulla suite PMI (1.1)

**Obiettivo.** Avere il numero che oggi manca: come va la configurazione
"ricerca a vettori + verifica dell'evidenza" sulle 178 domande della suite PMI.
Da questo numero dipende se cambiare il default (passo 0.3) e cosa fare in fase 4.

**Leggi prima.**
- `docs/RETRIEVAL_EVALUATION.md`, sezioni "Rimisura del 25–26 settembre" e
  "Suite PMI".
- `docs/adr/0001-evidence-first-lexical-default.md`.
- `evaluation/run_library_eval.py` (argomenti `--suite`, `--semantic`,
  `--verify`, `--verifier`, `--compare`).

### Passo 0.1 — Preparare i modelli
- Serve Ollama in esecuzione con questi modelli scaricati:
  `embeddinggemma:latest` (embedding) e `qwen3.5:4b` (verificatore).
- Controlla con `ollama list`. Se mancano, **STOP**: chiedi a Nicolò di
  scaricarli (sono download di qualche GB).

### Passo 0.2 — Eseguire le misure
Esegui, in quest'ordine, e salva l'output completo di ognuno:

```powershell
.\.venv-ermes\Scripts\python.exe evaluation/run_library_eval.py --suite pmi
```

```powershell
$env:ERMES_EMBED_MODEL_ID="embeddinggemma:latest"; .\.venv-ermes\Scripts\python.exe evaluation/run_library_eval.py --suite pmi --semantic
```

```powershell
$env:ERMES_EMBED_MODEL_ID="embeddinggemma:latest"; $env:ERMES_EVIDENCE_VERIFIER_MODEL="qwen3.5:4b"; .\.venv-ermes\Scripts\python.exe evaluation/run_library_eval.py --suite pmi --semantic --verify
```

**Verifica.** Nel report:
- `semantic_search_active` deve essere `true` nelle ultime due corse;
- `evidence_verification_active` deve essere `true` nell'ultima;
- se il report segnala chiamate al verificatore fallite o saltate, scrivilo:
  gli errori del verificatore gonfiano il recall (vedi la nota nel documento di
  valutazione).

**Non fare.** Non cambiare prompt, soglie o codice durante questa fase. È una
misura, non un'ottimizzazione.

### Passo 0.3 — Scrivere il risultato e decidere
- Aggiungi in fondo alla sezione "Suite PMI" di `docs/RETRIEVAL_EVALUATION.md`
  una tabella con le tre corse: dirette, parafrasi, astensione, e il dettaglio
  per etichetta (`trap`, `colloquial`, `cross_library`, ecc.).
- Regola di decisione già scritta nel piano (1.1):
  - se l'**astensione arriva a 0.9 o più** e le **dirette non scendono** sotto
    la baseline keyword (0.95), proponi di rendere "vettori + verifica" il
    default delle modalità con modello;
  - altrimenti si lavora sul verificatore (prompt, modello più grande) prima di
    tutto il resto della fase 4.
- **STOP**: qualunque cambio di default va deciso da Nicolò. Tu scrivi i numeri
  e una proposta, non cambi la configurazione.

**Fatto quando.** La tabella è in `docs/RETRIEVAL_EVALUATION.md`, in una PR
`docs/...`, con i tre comandi riportati per poterla rifare.

### Passo 0.4 — Misurare il verificatore da solo (C-01)
Segui la voce **C-01** del catalogo: un insieme di coppie (domanda, passaggio,
sì/no) con trappole costruite apposta, e uno script che misura precisione e
richiamo del verificatore. Serve a scegliere modello e prompt del verificatore
con dati. È una PR separata dal passo 0.3.

---

## Fase 1 — Permessi NTFS nel connettore cartelle (1.6)

**Obiettivo.** Quando Ermes importa file da una cartella di rete Windows, ogni
documento resta visibile **solo a chi lo vede sulla cartella originale**. Oggi
`core/connectors/local_folder.py` non legge nessun permesso: tutti i membri
della biblioteca vedono tutto.

**Leggi prima, in quest'ordine.**
1. `core/connectors/base.py`: il campo `RemoteDocument.allowed_principals` e il
   commento che spiega `None` contro tupla vuota.
2. `core/connector_ingest.py`: tutto il docstring in alto. Le regole sono già
   scritte lì e **valgono anche per NTFS**: tu devi solo riempire
   `allowed_principals`, il resto (scrittura in `document_acls`, nella stessa
   transazione) esiste già.
3. `core/connectors/microsoft_graph.py`: come `inherit_permissions` e
   `graph_permissions_to_principals` traducono i permessi di SharePoint. È il
   modello da imitare.
4. `tests/test_connector_permissions.py`: lo stile dei test da imitare.
5. `core/connectors/local_folder.py`: il file da modificare.

### Passo 1.1 — Decisione prima del codice (STOP)

**Deciso da Nicolò il 28 novembre 2026: opzione A.** I documenti si chiudono anche nelle cartelle gia' collegate.
Chiedi a Nicolò, **prima di scrivere codice**, come comportarsi quando i permessi
non si possono leggere (Ermes in Docker su Linux, cartella montata via SMB,
errore di lettura). Le due opzioni:
- **A (consigliata, coerente con il resto):** `inherit_permissions` attivo di
  default; se i permessi non si leggono, il documento si chiude (tupla vuota:
  visibile solo al proprietario della biblioteca e agli amministratori), con un
  avviso nel log e nel messaggio di `test_connection`.
- **B:** stesso comportamento, ma con `inherit_permissions` disattivato di
  default per i connettori cartella **già esistenti**, per non chiudere
  all'improvviso documenti che oggi gli utenti vedono.

Scrivi la risposta nel docstring del connettore.

### Passo 1.2 — La funzione di traduzione, pura e testabile
Fatto in `core/connectors/ntfs_permissions.py` (modulo a parte, per tenere leggibile il connettore). La consegna era: scrivi una funzione **senza dipendenze da
Windows** che riceve la descrizione dei permessi già letta e restituisce
`allowed_principals`. Esempio di firma:

```python
def ntfs_entries_to_principals(entries: list[AclEntry] | None) -> tuple[str, ...] | None:
```

dove `AclEntry` è un piccolo dataclass con: nome (`DOMINIO\utente` o nome del
gruppo), SID, tipo (`allow` o `deny`), e se concede la lettura.

Regole di traduzione (implementale tutte, una per una):

| Situazione | Risultato |
|---|---|
| DACL nulla (nessuna restrizione: Windows dà accesso a tutti) | `None` (segue le regole della biblioteca) |
| DACL vuota (nessuno ha accesso) | `()` (chiuso) |
| C'è almeno una voce `deny` | `()` (chiuso: non si valuta un deny in modo sicuro) |
| Una voce `allow` di lettura a un gruppo "tutti": Everyone `S-1-1-0`, Authenticated Users `S-1-5-11`, BUILTIN\Users `S-1-5-32-545`, Domain Users (SID che termina con `-513`) | `None` |
| Voci a SYSTEM `S-1-5-18`, Administrators `S-1-5-32-544`, CREATOR OWNER `S-1-3-0` | ignorate (non sono persone; gli amministratori Ermes vedono comunque tutto) |
| Voci `allow` che **non** concedono lettura | ignorate |
| Altre voci `allow` di lettura (utenti o gruppi) | il loro nome finisce nella tupla |
| Dopo le regole sopra non resta nessun nome | `()` (chiuso) |
| `entries is None` (lettura fallita) | `()` (chiuso) |

Limite noto, da scrivere nel docstring: un gruppo NTFS (per esempio
`AZIENDA\Contabilita`) vale solo se esiste un utente Ermes con lo stesso nome.
L'espansione dei gruppi nei loro membri non fa parte di questa fase.

### Passo 1.3 — Leggere davvero i permessi su Windows
- Usa `pywin32` (`win32security.GetFileSecurity`,
  `DACL_SECURITY_INFORMATION`, `LookupAccountSid`), aggiunto a
  `requirements.txt` **solo per Windows** (vedi "Dipendenze nuove").
- Importalo **dentro** la funzione di lettura, non in cima al file: su Linux il
  modulo non esiste e l'import in cima romperebbe la CI.
- La lettura restituisce la lista di `AclEntry`, oppure `None` se fallisce
  (con un `_logger.warning` che dice quale file e perché).
- In `fetch_documents`, se `inherit_permissions` è attivo, passa il risultato a
  `ntfs_entries_to_principals` e metti l'esito in `allowed_principals`.
- In `test_connection`, se `inherit_permissions` è attivo ma non siamo su
  Windows, restituisci comunque `True` ma con un messaggio che dice chiaramente
  che i documenti resteranno chiusi.

**Non fare.**
- Non usare `icacls` o `Get-Acl` in un sottoprocesso per ogni file: è lento su
  migliaia di file e il parsing del testo dipende dalla lingua di Windows.
- Non leggere solo le voci "esplicite": servono anche quelle ereditate dalle
  cartelle superiori, che sono la maggior parte.
- Non trattare un errore di lettura come "tutti": un errore chiude.

### Passo 1.4 — Test
In un file nuovo `tests/test_local_folder_permissions.py`:
1. Un test per **ogni riga** della tabella del passo 1.2, chiamando
   `ntfs_entries_to_principals` con voci finte. Girano anche su Linux.
2. Un test che importa un documento con
   `allowed_principals=("AZIENDA\\alice",)` tramite `import_remote_document`
   e verifica che lo veda solo `alice`. Copia la struttura di
   `test_a_file_shared_with_one_person_stays_visible_only_to_them`.
3. Un test che simula la lettura fallita e verifica che il documento sia chiuso.
4. Un test **solo Windows** (`@pytest.mark.skipif(sys.platform != "win32", ...)`)
   che crea un file temporaneo, toglie l'ereditarietà, dà lettura solo
   all'utente corrente e verifica che la lettura reale restituisca quel nome.

**Verifica.** Test, ruff e mypy verdi (vedi "Comandi di verifica").
`tests/test_local_folder_connector.py` deve restare verde senza modifiche, a
parte quelle richieste dalla decisione del passo 1.1.

### Passo 1.5 — Documentazione
- Nel piano strategico, voce 1.6, aggiorna lo **Stato** dicendo cosa è fatto
  per NTFS e cosa no (gruppi non espansi, Docker su Linux chiude tutto).
- Nella guida per l'azienda (`docs/GUIDA_OPERATIVA_AZIENDA.md`), spiega in
  italiano semplice cosa succede ai permessi delle cartelle di rete.
- Voce nel `CHANGELOG.md`.

**Fatto quando.** PR verde con codice, test e documenti. **STOP** prima del
merge: Nicolò deve provarlo su una cartella vera con due utenti Windows diversi.
Scrivi nella PR i passi esatti di questa prova.

### Passo 1.7 — Le fonti con scansione automatica
Trovato il 28 novembre 2026: oltre al connettore cartelle, le cartelle si
possono registrare come **fonti** (`core/folder_importer.py`, scansionate dal
Folder Watcher). Quella strada non legge i permessi NTFS, e la guida per
l'azienda la consigliava. Va portata sulle stesse regole del connettore
(`core/connectors/ntfs_permissions.py`), con i suoi test. PR separata.

### Passo 1.6 — File cancellati all'origine (C-22) — fatto, tranne Confluence
Segui la voce **C-22** del catalogo. In una PR separata, **prima** di quella
dei permessi NTFS:
1. scrivi il test che dimostra il problema (importa due file da una cartella,
   cancellane uno, risincronizza, verifica che non sia più cercabile). Se il
   test passa già, il problema non c'è: scrivilo nel catalogo e fermati;
2. se fallisce, correggi il connettore cartelle, poi WebDAV e S3, ciascuno con
   il suo test. Confluence in una PR a parte.

---

## Fase 2 — Installer senza prerequisiti (1.2)

**Obiettivo.** Un `Ermes-Setup.exe` che si installa su un PC Windows **pulito**,
senza Python, Node.js o Tesseract installati, in meno di 10 minuti, senza mai
aprire un terminale.

**Leggi prima.**
- `scripts/installer/ermes_setup.iss`: oggi dichiara che non include Python.
- `INSTALLA_ERMES.bat`, `SETUP_WIZARD.bat`, `AVVIA_ERMES.bat`,
  `scripts/configure_ai.py`, `scripts/build_exe.ps1`.
- La voce del 23 ottobre 2026 nel `CHANGELOG.md` (revisione di lanciatore e
  installer): racconta problemi già trovati, come l'installer che includeva
  `.env`, `data/` e il virtualenv.

### Passo 2.1 — Inventario (nessun codice)
Scrivi in una nota nella PR cosa serve oggi per installare Ermes da zero:
programmi, versioni, comandi, file creati. Prova davvero ogni passo in
**Windows Sandbox** (una macchina Windows pulita usa e getta) e annota dove si
blocca.

### Passo 2.2 — Includere ciò che manca
- **Python**: la distribuzione "embeddable" ufficiale di Python 3.11 per
  Windows, con le dipendenze di `requirements.txt` preinstallate.
- **Frontend**: già compilato (`npm run build`), così Node.js non serve.
- **Tesseract**: incluso con il pacchetto della lingua italiana, oppure, se è
  troppo grande, l'installer lo dice chiaramente e l'OCR resta spento. **STOP**:
  chiedi a Nicolò quale delle due.
- **Ollama e i modelli: non vanno inclusi** (sono diversi GB). Il setup continua
  a offrire la scelta esplicita già esistente: solo estratti, Ollama, API
  pubblica.

**Non fare.**
- Non includere mai `.env`, `.env.monitoring`, `data/`, `.venv-ermes/`, log o
  backup nel pacchetto. Aggiungi un controllo nello script di build che fallisce
  se ci sono.
- Non chiedere privilegi di amministratore se non servono.

### Passo 2.3 — Prova su PC pulito
- In Windows Sandbox: installa, avvia, crea una biblioteca, carica un PDF, fai
  una domanda. Cronometra.
- Disinstalla e verifica che i dati dell'utente non vengano cancellati senza
  chiederlo.

**Fatto quando.** Prova riuscita in meno di 10 minuti, con i passi e il tempo
scritti nella PR. L'aggiornamento in un clic (1.3) è un passo successivo, in
una PR separata.

---

## Fase 3 — Utenti pilota e domande vere nel gold set (1.5)

**Obiettivo.** Le domande che gli utenti veri fanno, e a cui Ermes risponde male,
diventano casi di test.

Questa fase è **soprattutto lavoro umano**: trovare 2-3 uffici pilota e
osservarli per due settimane. L'assistente AI aiuta solo nella parte tecnica.

**Già esiste (non rifarlo).** `GET /api/analytics/gold-set-candidates`
(`api/analytics.py`): esporta le domande senza risposta o con pollice giù, nel
formato di `evaluation/pmi_gold_set.json`, senza testo dei documenti.

### Passo 3.1 — Revisione dei candidati
- Scarica i candidati. Per ognuno, **una persona che conosce i documenti**
  decide se la risposta c'era (`direct` o `paraphrase`, con sezione attesa) o
  no (`abstention`).
- L'assistente AI **non decide da solo** la risposta attesa: prepara la tabella,
  la persona compila.
- I casi approvati vanno in un gold set separato da quello sintetico (per
  esempio `evaluation/pilot_gold_set.json`), mai mescolati: così si sa quali
  numeri vengono da domande vere.

**Non fare.** Non mettere mai nel repository testo dei documenti dell'azienda
pilota, nomi di persone o dati personali. Le domande vanno ripulite prima.

**Fatto quando.** Il gold set pilota ha almeno 30 domande riviste e lo script di
valutazione lo sa leggere.

---

## Fase 4 — Qualità del recupero (2.6, 2.5, riformulazioni)

**Regola di questa fase.** Una prova alla volta. Ogni prova si misura sulla
suite PMI **prima e dopo**, con lo stesso comando, e si applica al prodotto solo
se migliora senza peggiorare l'astensione. Se non migliora, si scrive il
risultato in `docs/RETRIEVAL_EVALUATION.md` e **non** si applica: anche un
"non funziona" misurato è un risultato.

### Passo 4.1 — Reranker multilingue (2.6)
- **Leggi prima** `core/reranker.py` (usa `sentence_transformers.CrossEncoder`
  con il modello in `ERMES_RERANKER_MODEL`) e la sezione "Gate CI" del
  documento di valutazione: il reranker attuale, inglese, peggiorava le
  parafrasi.
- Prova un modello multilingue, per esempio `BAAI/bge-reranker-v2-m3`,
  impostando `ERMES_RERANKER_MODEL` e `ERMES_RERANKER_ENABLED=1`.
- `evaluation/run_library_eval.py --suite pmi --compare` misura già le
  configurazioni con e senza reranker: usa quello, con `ERMES_RERANKER_MODEL`
  impostato sul modello da provare. Leggi `run_comparison` per sapere quali
  righe produce prima di interpretarle.
- Misura con e senza reranker, nella configurazione keyword e in quella con
  verifica.
- Annota anche il tempo per domanda: un reranker su CPU può essere lento.

### Passo 4.2 — Titolo e sezione nell'indice, non nell'estratto (2.5, C-03)
- In modalità keyword è già stato misurato: +2 domande su 127, non applicato
  perché l'estratto mostrato avrebbe avuto un prefisso (vedi "Esperimento:
  titolo e sezione" nel documento di valutazione).
- Segui la voce **C-03** del catalogo: il titolo e la sezione vanno solo nel
  testo indicizzato, l'estratto mostrato resta quello originale. Misura in
  modalità keyword e poi con la ricerca a vettori.

### Passo 4.2-bis — Altre voci del catalogo
Nell'ordine indicato in fondo al catalogo: **C-05** (passaggi vicini),
**C-04** (fusione parole e vettori), **C-07** (citazioni testuali verificate),
**C-02** (domanda al verificatore). Una voce per PR, ognuna misurata prima e
dopo.

### Passo 4.3 — Riformulazione della domanda
- **Leggi prima** due moduli che esistono già:
  - `core/hyde.py`: genera un testo ipotetico dalla domanda;
  - `core/query_expander.py`: espande la domanda con sinonimi (test in
    `tests/test_query_expander.py`).
  Prima di scrivere qualcosa di nuovo, scopri per ciascuno se è usato nel
  percorso di ricerca, con quale impostazione si accende, e se è mai stato
  misurato sulla suite PMI. Scrivi cosa trovi nella PR.
- Qualunque riformulazione va provata **sempre insieme alla verifica
  dell'evidenza**: da sola aumenta le citazioni sbagliate.

**Non fare.**
- Non aggiungere un filtro lessicale (spaCy o simili) prima del verificatore:
  è già stato scartato perché danneggia le parafrasi.
- Non aggiungere knowledge graph (GraphRAG, LightRAG): rimandati nel piano.

---

## Fase 5 — Email: file `.msg` e connettore IMAP (1.4)

**Obiettivo.** Le email di Outlook salvate (`.msg`) si leggono come le `.eml`,
e una casella si può collegare in sola lettura.

**Leggi prima.** `core/document_parser.py`: come vengono letti oggi i file
`.eml`, compresi gli allegati (nome del file e oggetto messi prima del testo
dell'allegato, correzione del 28 ottobre 2026).

### Passo 5.1 — File `.msg`
- Stesso risultato delle `.eml`: mittente, data e oggetto come riferimento della
  citazione; allegati come testo collegato.
- Aggiungi `.msg` a `MEDIA_TYPES` in `core/connectors/local_folder.py` e ai tipi
  accettati dall'upload.
- Aggiungi domande con etichetta `email` alla suite PMI, con un `.msg` di prova
  **inventato** in `evaluation/pmi_corpus/`.

### Passo 5.2 — Connettore IMAP (PR separata)
- Prima di scrivere codice leggi il connettore IMAP di Onyx (voce **C-25** del
  catalogo): è MIT e si può riusare con avviso di copyright.
- Solo lettura: il connettore non deve mai segnare messaggi come letti, spostarli
  o cancellarli.
- Le credenziali seguono le stesse regole degli altri connettori (mai nei log).
- **STOP** prima di iniziare: chiedi a Nicolò quali caselle e quali permessi
  (chi vede quali email in Ermes). È una decisione di privacy, non tecnica.

---

## Fase 6 — Evidenziazione nel PDF e migrazioni dello schema

### Passo 6.1 — Evidenziare il passaggio citato (2.1)
- Oggi il visualizzatore apre il PDF alla pagina giusta
  (`frontend/src/components/chat/ChatArea.tsx`, vista "PDF Pag. N"), ma non
  evidenzia il passaggio.
- Prima prova la strada della voce **C-06** del catalogo, come fa Kotaemon:
  passare al visualizzatore l'inizio del passaggio citato e farglielo cercare
  nella pagina. Solo se la ricerca fallisce troppo spesso, salvare la posizione
  del testo durante l'importazione.
- Per le pagine lette con OCR la posizione potrebbe non esserci: in quel caso si
  apre la pagina senza evidenziare, senza errori.

### Passo 6.2 — Migrazioni numerate dello schema
- Oggi `core/library_store/schema.py` aggiunge colonne con `ALTER TABLE` "se
  mancano", senza una tabella che dica quale versione dello schema c'è.
  PostgreSQL ha la sua versione in `core/postgres_backend.py`.
- Obiettivo: una tabella `schema_migrations` e migrazioni numerate, uguali per
  SQLite e PostgreSQL.
- **Vincolo obbligatorio:** un database creato con una versione vecchia di Ermes
  deve aggiornarsi da solo, senza perdere dati. Prima di qualsiasi modifica, fai
  un test che parte da un database creato con lo schema attuale e verifica che,
  dopo la migrazione, documenti, permessi e versioni ci siano ancora.
- `tests/test_postgres_parity.py` deve restare verde.

### Passo 6.3 — Lettura dei file più robusta (C-15, C-16)
- **C-15:** lettura dei PDF in un processo separato con tempo massimo.
- **C-16:** prima il test con un DOCX che dichiara dimensioni false; se passa i
  controlli attuali, limitare i byte effettivamente letti.
- Una PR per voce. Possono anche essere anticipate: non dipendono da altre fasi.

---

## Fase 7 — Pulizia del codice (in parallelo, piccole PR)

Questa fase non blocca le altre: si fa a pezzi, quando c'è tempo, una PR per
passo. Non mescolarla con PR di funzioni nuove.

### Passo 7.1 — Regole di lint in più (C-26)
Segui la voce **C-26** del catalogo, nell'ordine indicato lì: prima DTZ e B904,
poi la complessità a 20 con le tre funzioni attuali elencate come eccezioni,
poi la semplificazione di una funzione per PR. **Non** cambiare il
comportamento del codice in queste PR: i test devono restare identici.

### Passo 7.2 — Controlli prima del commit (C-27)
Un `.pre-commit-config.yaml` documentato in `DEVELOPER.md`, facoltativo.

### Passo 7.3 — Stile dei commenti (C-28)
**STOP:** solo se Nicolò lo decide.

---

## Appendice A — Mappa dei file più importanti

| Cosa | Dove |
|---|---|
| Configurazione (modelli, ricerca, soglie) | `config/rag.py`, `config/integrations.py`, `.env.example` |
| Lettura dei documenti, OCR, divisione in pezzi | `core/document_parser.py`, `core/ocr.py` |
| Ricerca (parole, vettori, permessi) | `core/library_store/search.py` |
| Embedding | `core/library_embeddings.py` |
| Verifica dell'evidenza | `core/evidence_verifier.py` |
| Risposta e astensione | `core/evidence_assistant.py` |
| Reranker | `core/reranker.py` |
| Connettori | `core/connectors/` |
| Importazione dai connettori, con permessi | `core/connector_ingest.py` |
| Schema del database | `core/library_store/schema.py`, `core/postgres_backend.py` |
| Valutazione | `evaluation/run_library_eval.py`, `evaluation/scale_check.py` |
| Soglie che bloccano la CI | `tests/test_library_evaluation.py` |
| Decisioni di architettura | `docs/adr/` |
| Risultati delle misure | `docs/RETRIEVAL_EVALUATION.md` |

## Appendice B — Glossario minimo

- **Biblioteca**: un insieme di documenti con i suoi membri e le sue regole.
- **Passaggio** (chunk): un pezzo di documento, circa 900 caratteri.
- **Astensione**: Ermes risponde "non ho trovato evidenza" invece di inventare.
- **Verifica dell'evidenza**: un modello controlla se il passaggio trovato
  risponde davvero alla domanda.
- **Gold set**: l'elenco di domande con la risposta attesa, usato per misurare.
- **Diretta / parafrasi / astensione**: domanda con le stesse parole del testo /
  con parole diverse / senza risposta nei documenti.
- **ACL / DACL**: l'elenco dei permessi di un file su Windows.
- **`allowed_principals`**: chi può vedere un documento secondo la fonte
  originale. `None` = regole della biblioteca; tupla vuota = chiuso.
