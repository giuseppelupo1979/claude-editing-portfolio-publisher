# Checklist di consegna

Leggi questo file in F6, prima di consegnare, e passa le voci una per una. Sta qui
e non in `SKILL.md` per una ragione precisa: `SKILL.md` viene letto per intero
all'inizio di ogni sessione, questa lista serve alla fine, e trenta voci di
controllo occupano contesto per tutto il lavoro senza servire finche' non c'e'
qualcosa da consegnare.

Le voci che riguardano una modalita' che non hai usato si saltano, ma vanno saltate
consapevolmente: se non c'e' pubblicazione, le righe sul provisioning non si
applicano; se non c'e' sequenza, quelle sulla copertina nemmeno.

## Le cinque non negoziabili

Queste stanno anche in `SKILL.md`, perche' se salti una di queste il lavoro e'
sbagliato e non incompleto:

1. La modalita' e' dichiarata e il suo format lock e' rispettato.
2. Il passaggio cieco e' stato fatto **prima** delle metriche, ed e' riportato.
3. Ogni numero citato esiste in `metriche.json`, con l'etichetta `[MISURATO]`.
4. Ogni immagine sottoposta ha la sua descrizione, scarti compresi; ogni immagine
   dell'edit ha anche la sua didascalia, e nessuna didascalia contiene un giudizio.
5. I deliverable sono in chat **e** sul disco dell'utente, e l'hai verificato.

## La lista completa

- La modalità è dichiarata, e il format lock di quella modalità è rispettato.
- Il passaggio cieco è stato fatto **prima** delle metriche, ed è riportato.
- Hai dichiarato cosa hai guardato: solo griglie, o anche miniature, e quali.
- Ogni numero citato esiste in `metriche.json`, con la sua etichetta `[MISURATO]`.
- Il numero di immagini dell'edit era fissato prima della selezione.
- Le coppie ridondanti segnalate dallo script sono state tutte risolte, con motivo.
- C'è il kill your darling, c'è l'edit alternativo, c'è lo scarto difeso.
- I bias sono passati in rassegna uno per uno, non genericamente.
- I difetti ricorrenti hanno una frequenza numerica, non un aggettivo.
- Ogni cluster e ogni galleria hanno un nome che non compare nella lista nera di
  `references/didascalie.md`.
- Se c'è pubblicazione: proposta approvata prima di `stage`, seconda conferma prima
  di `release`, profilo esterno, controllo duplicati e manifest senza segreti.
- Se è servito il provisioning: preflight senza SSH consegnato all'utente,
  autorizzazione separata legata a `authorization_hash`, apply con lo stesso hash,
  journal recuperabile e postcondizioni `doctor` più `/permissions/me` superate.
- Se è servito il provisioning: dominio email collegato al CMS, admin env `600`
  non symlink con `PUBLIC_URL` esatto, token confinato e vincolato, identità
  namespaced e matrice campo per campo senza wildcard, `delete`, admin o app.
- Se c'è pubblicazione: ogni foto ha `place`, `lat` e `lng`; la provenienza è
  dichiarata e qualsiasi default geografico risulta confermato dall'utente.
- **Nessun giudizio nelle didascalie.** La descrizione di lavoro contiene la tua
  valutazione ed è per l'autore; la didascalia va stampata sotto la fotografia e il
  lettore non deve trovarci dentro il tuo verdetto. Se una didascalia contiene "la
  decisione è", "ottiene", "manca", "debole", è finita nel posto sbagliato.
- **Ogni immagine sottoposta ha la sua descrizione**, scarti compresi, e la
  descrizione compare accanto alla miniatura in tutti i punti in cui parli di quella
  immagine: provino, sequenza, cluster, scarti, report, `testi.md`.
- Ogni immagine dell'edit ha anche la sua didascalia editoriale, tutte nello stesso
  registro, e il registro è dichiarato in `progetto.registro_didascalie`.
- Ci sono i tre titoli candidati, l'introduzione (250 a 500 parole) e lo statement
  (60 a 120), e sono tre testi distinti che non si ripetono a vicenda.
- `genera_testi.py` è stato eseguito, gli avvisi sono stati risolti o motivati, e i
  segnaposto aperti sono stati elencati all'utente.
- Nessun fatto inventato nei testi: luoghi, nomi, ricordi e motivazioni che non puoi
  provare sono segnaposto, e l'introduzione è consegnata come bozza da riscrivere.
- Nessun autore citato ricade nelle sue condizioni di non applicabilità.
- `analisi.json` è valido e gli script hanno girato senza errori.
- I deliverable sono stati consegnati **in chat con SendUserFile e scritti sul disco
  dell'utente** in `<cartella delle immagini>/_analisi`, e hai verificato con
  `device_list_dir` che ci sono davvero, elencandoli con il percorso. Se non hai
  potuto scrivere sul disco, l'hai detto in una riga spiegando perché.
- `analisi.json` è fra i file scritti sul disco, non solo in chat.
- Se c'è una sequenza: la copertina è proposta con motivazione e almeno due
  alternative, il ritmo ha la sua legenda e il suo `ritmo_perche`, e ci sono da due a
  tre alternative scartate con stringa e motivo.
- Ogni pagina con più di una immagine regge le cinque condizioni di
  `references/sequenza.md`, sezione 11.
- Se la modalità produce un edit ordinato, `dummy.pdf` esiste e contiene copertina,
  titolo, testi, spread, didascalie, descrizioni, attrezzatura EXIF e colophon.
- L'attrezzatura è presentata come elenco puntato, raggruppato almeno per copertura
  EXIF, corpi, obiettivi e focali; il colophon è distinto in sezioni tematiche e non
  duplica l'elenco dell'attrezzatura.
- L'elenco dell'attrezzatura usa solo `metriche.json`; dati assenti sono dichiarati
  non determinabili e non completati per deduzione.
- Nessun trattino lungo nel testo.
