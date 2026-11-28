# Catalogo delle idee prese da altri progetti RAG

Scritto il 24 novembre 2026 leggendo **il codice** (non solo la documentazione)
di RAGFlow, Onyx, Open WebUI e Kotaemon, scaricati da GitHub quel giorno.
Ogni voce dice dove si trova l'idea nel loro codice, cosa ha Ermes oggi, se si
può riusare il codice o solo l'idea, e come si misura.

> **Secondo giro, non completo.** Il primo giro (voci C-01…C-12) ha coperto
> verifica, citazioni, fusione, chunking ed evidenziazione. Il secondo (C-13…C-29)
> ha aggiunto lettura dei PDF, robustezza dei file, valutazione, riscrittura
> della domanda, reranker, connettori e organizzazione del codice. Le ricerche
> sono mirate: sono stati letti commenti, impostazioni e funzioni chiave, non i
> progetti interi. Mancano ancora: AnythingLLM (codice del server non trovato
> nel repository scaricato), Dify, PrivateGPT, i framework (LlamaIndex,
> Haystack), e nei quattro progetti letti l'interfaccia, la sicurezza delle API
> e l'installazione.

Chi lavora su Ermes usa questo catalogo **insieme a**
[`FASI_DI_LAVORO.md`](FASI_DI_LAVORO.md): il catalogo dice *cosa* vale la pena
prendere, le fasi dicono *quando* e *come*. Nessuna voce si implementa fuori
dal metodo descritto sotto.

---

## Regole

### Licenze: cosa si può riusare in Ermes (GPL-3.0)

Verificate sul file `LICENSE` di ciascun repository il 24 novembre 2026.

| Progetto | Licenza | Codice riusabile in Ermes? |
|---|---|---|
| RAGFlow | Apache 2.0 | Sì, con avviso di copyright e licenza. Attenzione: dalla versione 1.0 è scritto in **Go**, quindi in pratica si riusa l'idea e si riscrive in Python |
| Onyx | MIT fuori dalle cartelle `ee/` | Sì per il codice MIT, con avviso. **Mai** il codice nelle cartelle `ee/` (Onyx Enterprise License), che comprende tutta la sincronizzazione dei permessi |
| Open WebUI | BSD-3 con una clausola aggiuntiva sul marchio | **Solo idee.** La clausola 4 vieta di togliere il marchio "Open WebUI" oltre i 50 utenti: è una restrizione in più che la GPL-3.0 non ammette |
| Kotaemon | Apache 2.0 | Sì, con avviso di copyright e licenza |
| AnythingLLM | MIT | Sì, ma il codice del server non era nel repository scaricato: **non analizzato** |

Se si riusa codice:
1. controlla la licenza **del file** (l'intestazione), non solo del repository;
2. tieni l'avviso di copyright originale nel file copiato;
3. aggiorna `THIRD_PARTY_NOTICES.md` con `scripts/generate_third_party_notices.py`;
4. scrivi nella PR da quale file e da quale commit viene il codice.

Prodotti chiusi (Glean, Copilot): solo documentazione pubblica. Niente reverse
engineering dei loro programmi.

### Metodo per ogni voce

1. Leggi la voce e il codice indicato del progetto di origine.
2. Leggi il codice di Ermes indicato in "Ermes oggi". Se non corrisponde a
   quello che c'è scritto qui, **fermati e chiedi**: il catalogo può essere
   invecchiato.
3. Misura sulla suite PMI **prima** di cambiare qualcosa
   (`evaluation/run_library_eval.py --suite pmi`, con le stesse opzioni che
   userai dopo).
4. Implementa dietro un'impostazione spenta di default.
5. Misura **dopo**, con lo stesso comando.
6. Scrivi il risultato in `docs/RETRIEVAL_EVALUATION.md`, anche se negativo.
7. Proponi di accenderla di default solo se migliora senza peggiorare
   l'astensione. La decisione è di Nicolò.

---

## Le voci

Valore e costo: **A** alto, **M** medio, **B** basso.

### C-01 · Mettere alla prova il verificatore con passaggi "trappola"

- **Da dove:** RAGFlow, `internal/agentic_rag/decision_judge.go` (commento in
  testa al file).
- **L'idea.** RAGFlow ha un giudice che, come la nostra verifica dell'evidenza,
  decide passaggio per passaggio. Lo hanno valutato su 68 passaggi etichettati
  a mano con precisione e richiamo. Il controllo decisivo: un passaggio che
  **dice esplicitamente che l'informazione manca**. Un giudice buono lo boccia,
  uno che guarda solo la forma lo promuove. Il loro modello piccolo dava lo
  stesso punteggio con e senza quella frase: giudicava la forma, non il
  contenuto.
- **Ermes oggi.** `core/evidence_verifier.py` decide se un passaggio risponde.
  Non esiste un insieme di passaggi etichettati per misurare il verificatore da
  solo, separato dal recupero. Sulla suite PMI le trappole (`trap`) passano 2
  su 21 in modalità keyword.
- **Cosa fare.** Creare `evaluation/verifier_cases.json`: coppie (domanda,
  passaggio, risposta attesa sì/no), con almeno un terzo di trappole costruite
  così: stesso argomento, ma il passaggio non contiene la risposta o dice che
  non c'è. Uno script misura precisione e richiamo del verificatore su queste
  coppie, per ogni modello e prompt.
- **Riuso:** solo l'idea (codice Go).
- **Valore A · Costo B.** È la misura che manca per scegliere modello e prompt
  del verificatore con dati invece che a sensazione.
- **Fase:** 0, subito dopo la misura sulla suite PMI.

### C-02 · Rilevanza o sufficienza: decidere quale domanda fare al verificatore

- **Da dove:** RAGFlow, `decision_judge.go`: chiedono la **rilevanza**, non la
  **sufficienza**, e fanno la stessa domanda con **quattro formulazioni
  diverse**, mediando i punteggi.
- **Ermes oggi.** Il verificatore fa una sola domanda, con una sola
  formulazione. Non è documentato se chieda rilevanza o sufficienza.
- **Cosa fare.** Con i casi di C-01, provare: (a) rilevanza contro sufficienza;
  (b) una formulazione contro la media di tre o quattro. Tenere la variante
  migliore.
- **Riuso:** solo l'idea.
- **Valore M · Costo B** (dopo C-01). Attenzione al costo: quattro formulazioni
  sono quattro chiamate al modello per passaggio.
- **Fase:** 4.

### C-03 · Arricchire il testo indicizzato senza cambiare l'estratto mostrato

- **Da dove:** Open WebUI, `backend/open_webui/retrieval/utils.py`, funzione
  `get_enriched_texts`: per la ricerca a parole aggiungono al testo del
  passaggio nome del file (ripetuto due volte per pesare di più), titolo e
  intestazioni di sezione. L'utente continua a vedere il passaggio originale.
- **Ermes oggi.** L'esperimento del 28 ottobre 2026 (titolo e sezione davanti
  al passaggio) ha dato +2 domande su 127 ma **non è stato applicato** perché
  l'estratto mostrato all'utente avrebbe avuto un prefisso. Questa idea toglie
  proprio quell'obiezione.
- **Cosa fare.** Nell'indice full-text (FTS5 su SQLite, `search_tsv` su
  PostgreSQL) indicizzare "testo + titolo + sezione + nome file", lasciando
  invariato il testo salvato e mostrato. Rimisurare. Poi la stessa cosa per il
  testo che produce l'embedding.
- **Riuso:** solo l'idea (licenza Open WebUI).
- **Valore M · Costo B.**
- **Fase:** 4 (sostituisce il passo 4.2).

### C-04 · Fondere parole e vettori con una formula standard e un peso regolabile

- **Da dove:** Open WebUI (`utils.py`, fusione per rango reciproco con pesi
  `hybrid_bm25_weight`); Onyx (`backend/onyx/configs/chat_configs.py`,
  `HYBRID_ALPHA`: 0 solo parole, 1 solo vettori).
- **Ermes oggi.** In `core/library_store/search.py` il punteggio è una somma:
  punteggio frase + punteggio parole + similarità × 40. Il 40 non è
  documentato né misurato.
- **Cosa fare.** Aggiungere la fusione per rango reciproco (RRF): si ordina per
  parole, si ordina per vettori, e ogni passaggio prende `peso / (60 + posizione)`
  da ciascuna lista. Peso regolabile. Misurare con pesi 0, 0.3, 0.5, 0.7, 1.
- **Riuso:** idea (Open WebUI) o codice MIT di Onyx. La formula è standard e
  breve: conviene riscriverla.
- **Valore M · Costo B.** Da fare solo con la ricerca semantica attiva.
- **Fase:** 4.

### C-05 · Dare al verificatore e al modello anche i passaggi vicini

- **Da dove:** Onyx, `chat_configs.py`: `CONTEXT_CHUNKS_ABOVE` e
  `CONTEXT_CHUNKS_BELOW` (uno sopra e uno sotto, di default).
- **Ermes oggi.** Non c'è: il verificatore vede solo il passaggio trovato. Una
  risposta spezzata a metà fra due passaggi da 900 caratteri può essere
  bocciata.
- **Cosa fare.** Passare al verificatore (e al modello di risposta) il
  passaggio trovato più il precedente e il successivo dello stesso documento.
  La **citazione** resta sul passaggio trovato.
- **Riuso:** idea.
- **Valore M · Costo B.** Controllare che non peggiori le trappole: più testo
  vuol dire più occasioni di trovare qualcosa di "vicino".
- **Fase:** 4.

### C-06 · Evidenziare la citazione nel PDF cercando il testo, senza salvare coordinate

- **Da dove:** Kotaemon, `libs/ktem/ktem/utils/render.py`: il collegamento al
  PDF porta pagina e testo da cercare (`data-page`, `data-search`,
  `data-phrase`); il visualizzatore PDF.js cerca quel testo nella pagina e lo
  evidenzia (`libs/ktem/ktem/assets/js/pdf_viewer.js`).
- **Ermes oggi.** Il PDF si apre alla pagina citata
  (`frontend/src/components/chat/ChatArea.tsx`). Il piano (passo 6.1) prevede di
  salvare la posizione del testo durante l'importazione.
- **Cosa fare.** Prima provare la strada di Kotaemon: passare al visualizzatore
  l'inizio del passaggio citato e usare la ricerca del visualizzatore. Salvare
  coordinate solo se la ricerca fallisce troppo spesso (testo con a capo,
  sillabazione, OCR).
- **Riuso:** codice Apache 2.0 possibile, ma il frontend di Ermes è React:
  conviene riscrivere seguendo l'idea.
- **Valore A · Costo B.** Molto visibile per l'utente, poco codice.
- **Fase:** 6 (sostituisce l'approccio del passo 6.1).

### C-07 · Citazioni testuali verificate parola per parola

- **Da dove:** RAGFlow, `internal/agentic_rag/citations.go`: ogni riga della
  risposta indica da quale passaggio viene, e un revisore controlla
  **carattere per carattere** che la citazione esista nel passaggio. Kotaemon,
  `libs/kotaemon/kotaemon/indices/qa/citation.py`: il modello deve restituire
  le prove come **citazioni dirette** dal contesto.
- **Ermes oggi.** Con un modello, la risposta deve usare marcatori `[n]` che
  puntano a passaggi esistenti; un marcatore fuori intervallo porta
  all'astensione (ADR 0001). Non si controlla che la frase sia davvero
  sostenuta dal passaggio indicato.
- **Cosa fare.** Chiedere al modello, per ogni affermazione, anche una breve
  citazione testuale del passaggio. Controllare in Python che quella citazione
  compaia nel passaggio (dopo aver normalizzato spazi e maiuscole). Se non
  compare, togliere l'affermazione o astenersi.
- **Riuso:** idea.
- **Valore A · Costo M.** Rafforza il principio centrale di Ermes ed è un
  argomento forte verso chi valuta il prodotto.
- **Fase:** 4. Serve una misura della generazione, che oggi non c'è: va
  costruita insieme.

### C-08 · Tabelle e documenti strutturati divisi in modo dedicato

- **Da dove:** RAGFlow, `internal/parser/chunk/` e `internal/deepdoc/parser/pdf`
  (layout e tabelle); Onyx, `backend/onyx/indexing/chunking/tabular_section_chunker`.
- **Ermes oggi.** Le tabelle di Word e HTML sono lette con le intestazioni. Le
  tabelle nei **PDF** diventano testo piatto (pypdf). Un'unica regola di
  divisione per tutti i documenti (900 caratteri, 140 di sovrapposizione).
- **Cosa fare.** Prima la lacuna più concreta: estrarre le tabelle dei PDF
  riga per riga con le intestazioni, come già si fa per Word. Valutare una
  libreria con licenza compatibile, misurando su PDF con tabelle aggiunti alla
  suite PMI.
- **Riuso:** idea; per la libreria, verificare la licenza prima.
- **Valore A · Costo M.**
- **Fase:** 5 o 6, dopo email.

### C-09 · Nascondere o promuovere un documento dall'amministratore

- **Da dove:** Onyx, `backend/onyx/db/feedback.py`: `boost` e "hide" per
  documento.
- **Ermes oggi.** Non c'è. Esistono le date di revisione e lo storico versioni.
- **Cosa fare.** Un'opzione per documento: "non usare nelle risposte" (per
  procedure superate ma da conservare) e, forse, "preferire". La prima è la più
  utile per una PMI ed è semplice da misurare (il documento nascosto non esce
  mai).
- **Riuso:** idea (verificare che `feedback.py` sia fuori da `ee/` prima di
  guardarne il codice: lo è, ma il controllo va rifatto).
- **Valore M · Costo B.**
- **Fase:** dopo la 3, se gli utenti pilota lo chiedono.

### C-10 · Riassunto del documento e del passaggio nell'indice (contextual RAG)

- **Da dove:** Onyx, `backend/onyx/configs/app_configs.py`:
  `ENABLE_CONTEXTUAL_RAG`, `USE_DOCUMENT_SUMMARY`, `USE_CHUNK_SUMMARY`.
- **Ermes oggi.** Non c'è. È la seconda metà della voce 2.5 del piano
  ("prefisso generato dal modello, solo se la misura lo giustifica").
- **Cosa fare.** Solo dopo C-03: se l'arricchimento gratuito non basta, provare
  un riassunto generato dal modello in fase di importazione.
- **Riuso:** idea o codice MIT.
- **Valore M · Costo A.** Costa una chiamata al modello per passaggio in
  importazione: su migliaia di passaggi, ore di calcolo.
- **Fase:** 4, in fondo.

### C-11 · Più grandezze di passaggio insieme (multipass)

- **Da dove:** Onyx, `app_configs.py`: `ENABLE_MULTIPASS_INDEXING`,
  `MINI_CHUNK_SIZE`, `LARGE_CHUNK_RATIO`.
- **L'idea.** Indicizzare lo stesso testo in pezzi piccoli (precisi) e grandi
  (con contesto).
- **Ermes oggi.** Una sola grandezza.
- **Valore M · Costo A.** Moltiplica l'indice e gli embedding. Da considerare
  solo se C-05 non basta.
- **Fase:** non pianificata.

### C-12 · Messaggio di astensione configurabile per biblioteca

- **Da dove:** RAGFlow, `internal/agent/component/universe_a_wrappers.go`:
  parametro `empty_response`.
- **Ermes oggi.** L'astensione c'è ed è il principio centrale; il testo non è
  personalizzabile per biblioteca (da verificare in `core/evidence_assistant.py`).
- **Cosa fare.** Un campo per biblioteca, per esempio "Non ho trovato la
  risposta nei documenti HR: scrivi a hr@...".
- **Riuso:** idea.
- **Valore B · Costo B.** Utile agli utenti pilota.
- **Fase:** 3.

---

## Secondo giro (24 novembre 2026)

### Lettura dei documenti

#### C-13 · Pulire i PDF: intestazioni e piè di pagina, indici, parole spezzate

- **Da dove:** RAGFlow, `internal/deepdoc/parser/pdf/layout/`:
  `toc_header_footer.go` (toglie le pagine d'indice e le righe ripetute in
  testa e in fondo alle pagine), `dehyphen.go` (riunisce "pro- cedura" in
  "procedura" solo se dopo il trattino c'è uno spazio, così "socio-sanitario"
  resta intatto), `combined_column.go` (riconosce i testi su due colonne e
  distingue le colonne vere dalle celle di una tabella).
- **Ermes oggi.** `core/document_parser.py` legge i PDF con pypdf pagina per
  pagina. Non risulta nessuna pulizia di intestazioni, piè di pagina, indici o
  parole spezzate. Un piè di pagina come "Procedura P-07 rev. 3 — pagina 4 di
  12" finisce in ogni passaggio e crea corrispondenze false.
- **Cosa fare.** Tre funzioni piccole, ognuna con il suo test: (1) togliere le
  righe identiche (a meno dei numeri) che compaiono in testa o in fondo a più
  della metà delle pagine; (2) riunire le parole spezzate a fine riga con la
  regola di RAGFlow; (3) saltare le pagine d'indice. Le due colonne vengono
  dopo, se servono.
- **Misura.** Aggiungere alla suite PMI due PDF con intestazioni, piè di
  pagina e parole spezzate. Per il parser, usare file di riferimento con
  l'uscita attesa (RAGFlow fa così: `internal/deepdoc/native/golden.go`).
- **Riuso:** solo l'idea (codice Go).
- **Valore M · Costo B.**

#### C-14 · Usare i segnalibri del PDF come nomi di sezione

- **Da dove:** RAGFlow, `toc_header_footer.go`: legge la struttura dei
  segnalibri (outline) del PDF per riconoscere le sezioni.
- **Ermes oggi.** Per i PDF la citazione indica solo "Pagina N"; per Word
  indica la sezione.
- **Cosa fare.** Se il PDF ha segnalibri (pypdf li legge con `outline`),
  citare "Sezione X, pagina N". Utile anche a C-03, che arricchisce l'indice
  con il nome della sezione.
- **Riuso:** idea.
- **Valore M · Costo B.**

#### C-15 · Leggere i PDF in un processo separato con un tempo massimo

- **Da dove:** Onyx, `backend/onyx/file_processing/pdfium_text.py` e
  `PDF_TEXT_EXTRACTION_TIMEOUT_SECONDS` in `configs/app_configs.py`: ogni PDF
  si legge in un processo figlio, che viene chiuso se supera il tempo. Il
  motivo, scritto da loro: un PDF malformato può bloccare o far cadere il
  lettore.
- **Ermes oggi.** pypdf gira nello stesso processo, senza tempo massimo. Un
  PDF costruito male (per errore o apposta) può bloccare l'importazione.
- **Cosa fare.** Estrarre il testo in un processo separato con tempo massimo
  configurabile; se scade, il documento va in errore con un messaggio chiaro e
  l'importazione degli altri continua.
- **Riuso:** idea, o codice MIT di Onyx.
- **Valore M · Costo B.** È robustezza e sicurezza insieme.

#### C-16 · Limiti degli archivi basati sui byte letti, non su quelli dichiarati

- **Da dove:** Onyx, `backend/onyx/file_processing/zip_limits.py`: controlla
  i byte **effettivamente** decompressi mentre li legge, accetta solo i metodi
  di compressione STORED e DEFLATED (perché BZIP2 e LZMA in Python non hanno un
  limite in uscita) e limita anche la lettura della directory dell'archivio.
- **Ermes oggi.** `core/document_parser.py` (circa riga 525) somma le
  dimensioni **dichiarate** nell'archivio (DOCX, XLSX e PPTX sono archivi zip)
  e controlla il rapporto di compressione (`MAX_OFFICE_COMPRESSION_RATIO`). Le
  dimensioni dichiarate si possono falsificare.
- **Cosa fare.** Prima un test: un file DOCX costruito con dimensioni
  dichiarate false. Se passa il controllo attuale, aggiungere il limite sui
  byte letti e il controllo sul metodo di compressione.
- **Riuso:** codice MIT di Onyx, con avviso.
- **Valore M · Costo B.** Sicurezza.

#### C-17 · Un motore di estrazione esterno, opzionale

- **Da dove:** Open WebUI, `backend/open_webui/retrieval/loaders/main.py`:
  si può delegare l'estrazione a un servizio esterno (Tika, Docling, Marker,
  MinerU, Mistral OCR, Azure Document Intelligence, PaddleOCR). Kotaemon,
  `libs/kotaemon/kotaemon/loaders/docling_loader.py`: usa Docling per tabelle
  e figure, e un modello visivo opzionale per descrivere le figure.
- **Ermes oggi.** Tutta l'estrazione è interna (pypdf, OCR con Tesseract).
- **Cosa fare.** Un'impostazione "motore di estrazione esterno" con l'indirizzo
  di un servizio (per esempio Docling in un container). Ermes resta leggero di
  default, e chi ha bisogno di tabelle nei PDF accende il servizio. È una
  strada alternativa a C-08: va confrontata con quella sugli stessi PDF.
- **Riuso:** idea. La licenza del servizio esterno va verificata, ma girando
  come servizio separato non entra nel codice di Ermes.
- **Valore A · Costo M.**

### Recupero, verifica e valutazione

#### C-18 · Un verificatore che decide anche quanto contesto serve

- **Da dove:** Onyx, `backend/onyx/secondary_llm_flows/document_filter.py`
  (`classify_section_relevance`) e `ContextExpansionType` in
  `context/search/models.py`: per ogni passaggio il modello risponde con
  "non pertinente", "solo questo passaggio", "anche i vicini" o "documento
  intero".
- **Ermes oggi.** Il verificatore risponde sì o no.
- **Cosa fare.** Dopo C-05 e C-01: estendere la risposta del verificatore a
  queste quattro scelte e passare al modello il contesto deciso. La citazione
  resta sul passaggio trovato.
- **Riuso:** idea.
- **Valore M · Costo M.**

#### C-19 · Quale reranker provare per primo

- **Da dove:** nei quattro progetti i modelli di reranking più citati nel
  codice e nelle configurazioni sono `BAAI/bge-reranker-v2-m3` e
  `jina-reranker-v2-base-multilingual`, entrambi multilingue.
- **Ermes oggi.** `cross-encoder/ms-marco-MiniLM-L-6-v2`, inglese, spento
  perché peggiorava le parafrasi.
- **Cosa fare.** Conferma la scelta del passo 4.1 di `FASI_DI_LAVORO.md`:
  provare per primo `BAAI/bge-reranker-v2-m3`. Verificare la licenza del
  modello prima di renderlo predefinito.
- **Valore M · Costo B.**

#### C-20 · Filtri ricavati dalla domanda: date e fonti

- **Da dove:** Onyx, `secondary_llm_flows/time_filter.py` (ricava un
  intervallo di date dalla domanda: "nell'ultimo mese", "dal 2025") e
  `source_filter.py` (sceglie in quali fonti cercare).
- **Ermes oggi.** La biblioteca la sceglie l'utente; non ci sono filtri per data.
- **Cosa fare.** Per ora niente: da valutare se gli utenti pilota fanno
  domande con date. Se sì, partire dalle date.
- **Riuso:** idea o codice MIT.
- **Valore B · Costo M.**

#### C-21 · Misurare la risposta, non solo il recupero

- **Da dove:** Onyx, `backend/onyx/evals/` (insieme di domande con risposta
  attesa, modalità solo locale con `--local-only`); RAGFlow,
  `internal/agentic_rag/citation_paradigm_compare_test.go` (confronta due modi
  di produrre citazioni).
- **Ermes oggi.** `docs/RETRIEVAL_EVALUATION.md` lo dice: la valutazione misura
  solo il recupero, non la risposta del modello.
- **Cosa fare.** Un insieme di domande con risposta attesa e citazioni attese,
  e uno script che controlla: la risposta cita passaggi giusti? Ogni frase è
  sostenuta da una citazione (vedi C-07)? Si astiene quando deve? Tutto in
  locale, senza servizi esterni.
- **Riuso:** idea.
- **Valore A · Costo M.** È il prerequisito di C-07.

### Connettori

#### C-22 · Togliere da Ermes i file cancellati all'origine

- **Da dove:** Onyx, `backend/onyx/connectors/interfaces.py`: oltre al
  caricamento completo e a quello incrementale, un connettore può restituire
  **solo l'elenco degli identificativi** presenti all'origine
  (`SlimConnector`, `retrieve_all_slim_docs`). Costa poco, e serve a togliere
  da Onyx tutto quello che all'origine non c'è più.
- **Ermes oggi.** Dal codice risulta che solo Google Drive e Microsoft 365
  segnalano i file cancellati (`deleted_document_ids`). Il connettore cartelle
  (`core/connectors/local_folder.py`), WebDAV e S3 usano il comportamento di
  base di `core/connectors/base.py`, che restituisce sempre un elenco vuoto, e
  Confluence restituisce un elenco vuoto esplicito. **Conseguenza da
  verificare con un test:** un file cancellato dalla cartella di rete resta
  cercabile in Ermes, anche se era riservato.
- **Cosa fare.** Prima il test che lo dimostra (importa due file, cancellane
  uno all'origine, risincronizza, cerca). Se il problema c'è: a ogni
  sincronizzazione completa, confrontare gli identificativi trovati con quelli
  già importati da quel connettore e togliere quelli spariti.
- **Riuso:** idea.
- **Valore A · Costo B.** Riguarda la riservatezza quanto i permessi NTFS:
  va fatto nella fase 1.

#### C-23 · Aggiornare i permessi senza riscaricare i file

- **Da dove:** Onyx, `SlimConnectorWithPermSync` in `interfaces.py`: elenco
  di identificativi **con i permessi**, senza il contenuto. L'implementazione
  per ogni fonte è nelle cartelle `ee/` (vietate); l'idea no.
- **Ermes oggi.** `core/connector_ingest.py` aggiorna i permessi anche dei file
  già importati, ma per riconoscerli serve scaricarne il contenuto e calcolarne
  l'impronta.
- **Cosa fare.** Per le cartelle di rete, dopo la fase 1: rileggere i permessi
  NTFS (operazione veloce) senza rileggere i file non modificati (stessa data
  di modifica e dimensione).
- **Riuso:** idea.
- **Valore M · Costo M.**

#### C-24 · Riprendere una sincronizzazione interrotta e rispettare i limiti delle API

- **Da dove:** Onyx, `interfaces.py`: `CheckpointedConnector` (riprende da
  dove si era fermato) e `SourceApiLimiter` (rallenta quando la fonte risponde
  "troppe richieste").
- **Ermes oggi.** Non risulta né l'uno né l'altro.
- **Cosa fare.** Solo se gli utenti pilota hanno archivi grandi o fonti con
  limiti stretti.
- **Riuso:** idea o codice MIT.
- **Valore B · Costo M.**

#### C-25 · Leggere il connettore IMAP di Onyx prima di scrivere il nostro

- **Da dove:** Onyx, `backend/onyx/connectors/imap/` (fuori dalle cartelle
  `ee/`, quindi MIT).
- **Ermes oggi.** Nessun connettore email (passo 5.2 di `FASI_DI_LAVORO.md`).
- **Cosa fare.** Prima di scrivere il connettore, leggere il loro: gestione
  delle cartelle, date, allegati, errori di connessione. Riusare il codice è
  permesso, con avviso di copyright; ricordare che il nostro deve restare in
  sola lettura.
- **Valore M · Costo B** (riduce il costo del passo 5.2).

### Organizzazione e pulizia del codice

#### C-26 · Regole di lint più ampie, introdotte "a cricchetto"

- **Da dove:** Onyx, `pyproject.toml`, sezione `[tool.ruff.lint]`: oltre alle
  regole di base usano B (errori comuni), S (sicurezza), C901 (complessità),
  DTZ (date senza fuso orario), PERF, LOG. Per la complessità usano un
  "cricchetto": soglia a 20, le funzioni che già la superano sono elencate a
  parte, e la soglia si abbassa man mano che vengono semplificate.
- **Ermes oggi.** `pyproject.toml` usa E, F, I, N, W, UP, SIM. Misurato il 24
  novembre 2026 lanciando ruff con le regole in più di Onyx su `api`, `core`,
  `config`, `scripts`:
  - **3 funzioni** sopra complessità 20: `call_llm` (24, `core/ai/utils.py`),
    `extract_source_units` (25, `core/document_parser.py`),
    `search_with_profile` (24, `core/library_store/search.py`); 38 sopra 10;
  - 17 `datetime.now()` senza fuso orario; 14 eccezioni rilanciate senza
    `from`; 16 log con f-string;
  - 290 segnalazioni B008 sono i `Depends(...)` di FastAPI: falsi allarmi, che
    Onyx esclude per nome;
  - 3 segnalazioni B023 in `core/pii_filter.py`, controllate a mano: falsi
    allarmi (la funzione è usata subito, dentro lo stesso giro del ciclo).
- **Cosa fare.** Una PR per famiglia di regole: prima DTZ e B904 (pochi casi,
  correzioni meccaniche), poi C901 a 20 con le tre funzioni elencate come
  eccezioni, poi la loro semplificazione una alla volta. B008 escluso per
  `fastapi.Depends` e simili, come fa Onyx.
- **Riuso:** configurazione (MIT).
- **Valore M · Costo B.**

#### C-27 · Controlli prima del commit

- **Da dove:** Onyx, `.pre-commit-config.yaml`: file troppo grandi, YAML
  valido, segreti (ripsecrets), workflow GitHub (actionlint), script shell
  (shellcheck).
- **Ermes oggi.** Nessun controllo prima del commit: gli errori si scoprono
  in CI, minuti dopo.
- **Cosa fare.** Un `.pre-commit-config.yaml` con ruff, file grandi, YAML,
  segreti e actionlint. Facoltativo per chi contribuisce, ma documentato.
- **Valore B · Costo B.**

#### C-28 · Commenti che descrivono il presente, storia nel CHANGELOG

- **Da dove:** RAGFlow, `AGENTS.md`: i commenti devono descrivere il
  comportamento attuale, non la storia delle migrazioni; preferire la
  cancellazione del codice vecchio a strati di compatibilità; togliere test
  morti e codice commentato.
- **Ermes oggi.** Molti commenti iniziano con la storia ("Fino al 18 settembre
  2026 ...": per esempio `config/integrations.py`, `core/connector_ingest.py`,
  `core/ocr.py`). Spiegano bene il perché, ma crescono e invecchiano.
- **Cosa fare.** **STOP: decide Nicolò.** Proposta: nel codice tenere il perché
  in una o due frasi al presente; spostare il racconto nel CHANGELOG o in un
  ADR, con un riferimento.
- **Valore B · Costo M.**

#### C-29 · Test sull'implementazione vera

- **Da dove:** RAGFlow, `AGENTS.md`: i test di integrazione devono usare il
  codice vero, senza sostituire con finti oggetti il codice che stanno provando.
- **Ermes oggi.** Già in linea: per esempio `tests/test_connector_permissions.py`
  usa un vero `LibraryStore` su un database SQLite temporaneo.
- **Cosa fare.** Niente di nuovo; aggiungere la regola alle "Regole sempre
  valide" di `FASI_DI_LAVORO.md` perché resti così.

---

## Cosa **non** prendere, e perché

| Idea | Chi la usa | Perché no, per ora |
|---|---|---|
| Recupero "agentico" in più passaggi, con strumenti e ragionamento | RAGFlow (`internal/agentic_rag/`), Onyx Deep Research | Costoso e difficile da verificare; il piano rimanda gli agenti |
| Grafo della conoscenza (GraphRAG) | RAGFlow, Kotaemon, Onyx (`kg/`) | Rimandato nel piano; da valutare solo per domande su più documenti |
| Penalizzare i documenti vecchi (`DOC_TIME_DECAY`) | Onyx | In una PMI un regolamento del 2019 può essere ancora quello valido. Ermes ha già versioni e date di revisione, che sono un segnale migliore |
| Codice di sincronizzazione dei permessi | Onyx (`backend/ee/onyx/external_permissions/`) | Licenza Enterprise: vietato copiarlo |

**Nota utile per il posizionamento.** Nell'elenco dei connettori con permessi
di Onyx (`backend/ee/onyx/external_permissions/`) non c'è nessuna cartella di
rete Windows o SMB, e la ricerca di "smb" o "ntfs" nei suoi connettori non dà
risultati. I permessi NTFS della fase 1 sarebbero quindi una cosa che
nemmeno Onyx a pagamento fa.

---

## Ordine consigliato

| Ordine | Voce | Fase | Perché adesso |
|---|---|---|---|
| 1 | C-22 | 1 | Possibile problema di riservatezza: file cancellati che restano cercabili. Prima il test |
| 2 | C-01 | 0 | Misura che serve a tutte le altre voci sul verificatore |
| 3 | C-15, C-16 | 2 | Robustezza e sicurezza della lettura dei file, poco lavoro |
| 4 | C-06 | 6 | Grande effetto visibile, poco lavoro |
| 5 | C-13, C-14 | 4 | PDF più puliti e citazioni con la sezione, poco lavoro |
| 6 | C-03 | 4 | Recupera un esperimento già fatto, togliendo l'obiezione |
| 7 | C-05, C-19 | 4 | Poco lavoro; reranker da provare già indicato |
| 8 | C-04 | 4 | Solo con la ricerca semantica accesa |
| 9 | C-21, poi C-07 | 4 | Il principio di Ermes: prima la misura della risposta, poi le citazioni verificate |
| 10 | C-08 o C-17 | 5–6 | Tabelle nei PDF: confrontare le due strade |
| 11 | C-25 | 5 | Prima del connettore IMAP |
| sempre | C-26, C-27 | 7 | Piccole PR di pulizia, quando c'è tempo |
| poi | C-02, C-09, C-12, C-18, C-23, C-10, C-11, C-20, C-24 | — | Secondo le misure e le richieste degli utenti pilota |
| decide Nicolò | C-28 | 7 | Cambia lo stile dei commenti di tutto il progetto |

## Come aggiornare questo catalogo

- Quando una voce viene fatta, scrivi accanto al titolo `— fatto (data, PR)` o
  `— provato, non applicato (data)` con il numero misurato.
- I progetti cambiano: se un percorso indicato qui non esiste più, scrivi la
  data in cui l'hai notato invece di cancellare la voce.
- Una voce nuova segue lo stesso formato: da dove, l'idea, Ermes oggi, cosa
  fare, riuso, valore e costo, fase.
