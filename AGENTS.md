# Istruzioni per assistenti AI

Prima di lavorare su Ermes leggi [`docs/FASI_DI_LAVORO.md`](docs/FASI_DI_LAVORO.md):
contiene le regole sempre valide (Git, test, onestà dei numeri, sicurezza) e le
fasi di lavoro in ordine, con i passi, le verifiche e i punti in cui fermarsi a
chiedere.

In breve:
- mai push o merge su `main`: branch nuovo e pull request;
- mai abbassare le soglie di `tests/test_library_evaluation.py`;
- mai cambiare un default senza una misura scritta in `docs/RETRIEVAL_EVALUATION.md`;
- un permesso che non si legge chiude il documento, non lo apre;
- se il codice non corrisponde a quello che dicono i documenti, fermati e chiedi.
