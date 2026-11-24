# Catalogo delle idee prese da altri progetti RAG

Scritto il 24 novembre 2026 leggendo **il codice** (non solo la documentazione)
di RAGFlow, Onyx, Open WebUI e Kotaemon, scaricati da GitHub quel giorno.
Ogni voce dice dove si trova l'idea nel loro codice, cosa ha Ermes oggi, se si
può riusare il codice o solo l'idea, e come si misura.

> **Primo giro, non completo.** Sono stati letti solo alcuni temi, con ricerche
> mirate e non file interi. Mancano: AnythingLLM (codice del server non trovato
> nel repository scaricato), Dify, PrivateGPT, i framework (LlamaIndex,
> Haystack); e, anche nei quattro progetti letti, la lettura dei PDF e delle
> tabelle, i sistemi di valutazione, la riscrittura della domanda, i reranker,
> i connettori, l'interfaccia, la sicurezza e l'installazione.

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

| Ordine | Voce | Perché adesso |
|---|---|---|
| 1 | C-01 | Misura che serve a tutte le altre voci sul verificatore |
| 2 | C-06 | Grande effetto visibile, poco lavoro |
| 3 | C-03 | Recupera un esperimento già fatto, togliendo l'obiezione |
| 4 | C-05 | Poco lavoro, aiuta le risposte spezzate |
| 5 | C-04 | Solo con la ricerca semantica accesa |
| 6 | C-07 | Il più importante per il principio di Ermes, ma serve prima una misura della generazione |
| 7 | C-08 | La lacuna più concreta nella lettura dei documenti |
| poi | C-02, C-09, C-12, C-10, C-11 | Secondo le misure e le richieste degli utenti pilota |

## Come aggiornare questo catalogo

- Quando una voce viene fatta, scrivi accanto al titolo `— fatto (data, PR)` o
  `— provato, non applicato (data)` con il numero misurato.
- I progetti cambiano: se un percorso indicato qui non esiste più, scrivi la
  data in cui l'hai notato invece di cancellare la voce.
- Una voce nuova segue lo stesso formato: da dove, l'idea, Ermes oggi, cosa
  fare, riuso, valore e costo, fase.
