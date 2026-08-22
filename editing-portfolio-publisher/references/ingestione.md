# Ingestione: portare le immagini nello spazio di lavoro

Obiettivo di questa fase: avere in un'unica cartella di lavoro le miniature, le
griglie di provino e le metriche numeriche, senza aver mai giudicato niente.
Nessuna valutazione in F1. Se ti viene un'idea sulla qualità di una foto mentre la
copi, tienila per il passaggio cieco.

## Indice

1. La convenzione di cartella
2. Caso A: immagini caricate in chat
3. Caso B: cartella sul computer dell'utente
4. Lotti e limiti
5. RAW, HEIC e formati difficili
6. Cosa produce prepara_provino.py
7. Riportare gli output sul computer dell'utente
8. Problemi frequenti

## 1. La convenzione di cartella

Proponi all'utente questa struttura sul suo computer, una volta sola, e poi
riusala sempre. Rende ogni sessione futura immediata:

```
Portfolio-Analisi/
└── nome-progetto/
    ├── (le immagini da analizzare, copiate qui dall'utente)
    └── _analisi/          (creata da te, contiene tutti gli output)
        ├── thumbs/
        ├── griglie/
        ├── metriche.csv
        ├── analisi.json
        ├── report.md
        ├── provino.html
        ├── dummy.pdf
        └── tabella.xlsx
```

Il vantaggio: l'utente sceglie cosa analizzare semplicemente copiando i file in
una cartella, che è esattamente quello che chiede di poter fare. Non deve
selezionare nulla in chat.

Se la cartella `nome-progetto` contiene già una `_analisi` con un `analisi.json`,
sei davanti a una revisione, non a una prima analisi: leggila prima di ricominciare
e in chiusura fai il confronto longitudinale (vedi `autodiagnosi.md`).

## 2. Caso A: immagini caricate in chat

Sono già nella cartella degli upload della sessione. Copiale in una cartella di
lavoro nello spazio di lavoro e lancia lo script su quella. Nessun altro passaggio.

Limite pratico: caricare 60 file in chat è scomodo, ed è il motivo per cui il caso
B è la via principale.

## 3. Caso B: cartella sul computer dell'utente

Serve che la cartella sia collegata alla sessione. Sequenza:

1. `mcp__remote-devices__device_list_dir` sul percorso, per l'inventario: nomi,
   dimensioni in byte, date. Da qui sai già quanti file sono e quanto pesano.
2. Se il percorso non è raggiungibile, `mcp__remote-devices__device_request_folder_access`
   con il percorso esatto e una riga di motivazione. Chiedi **una volta sola**, per
   la cartella giusta (la cartella padre `Portfolio-Analisi`, non il singolo
   progetto, così le sessioni successive non devono richiedere niente).
3. `mcp__remote-devices__device_stage_files` per portare i file nello spazio di
   lavoro, a lotti (vedi sotto).
4. Da qui in poi lavori solo nello spazio di lavoro, con bash e con gli script.

Non provare a eseguire gli script sul computer dell'utente: `device_bash` gira in
un ambiente separato dove Pillow e numpy potrebbero non esserci. L'unico uso
sensato di `device_bash` in questa fase è ridurre le immagini **prima** di portarle
qui, quando pesano troppo (punto 4).

## 4. Lotti e limiti

`device_stage_files` accetta al massimo 50 file per chiamata, con un tetto di
banda per chiamata. File da fotocamera moderna pesano fra 8 e 40 MB l'uno, quindi:

- fino a 20 file per chiamata se sono JPEG da fotocamera;
- fino a 10 se sono TIFF o RAW;
- conta i byte dall'inventario del passo 1 e resta sotto i 400 MB per chiamata.

Se il totale è grosso (oltre 2 GB) conviene ridurre prima, sul computer
dell'utente. Verifica cosa c'è a disposizione con una sola chiamata:

```bash
for t in magick convert ffmpeg exiftool python3; do
  command -v $t >/dev/null && echo "$t presente"
done
```

Se c'è ImageMagick, crea copie a lato lungo 2000 px in una sottocartella
`_ridotte`, poi porta quelle. Attenzione: le copie ridotte invalidano ogni
giudizio su nitidezza, rumore e microdettaglio, e invalidano il calcolo della
dimensione massima di stampa. In quel caso leggi le dimensioni originali in pixel
dall'inventario o da exiftool e passale a mano nel report, dichiarando che le
misure di dettaglio non sono state fatte sull'originale.

Se non c'è nessuno strumento, porta gli originali a lotti. È più lento ma è la via
corretta, perché mantiene ogni misura affidabile.

## 5. RAW, HEIC e formati difficili

Lo script gestisce nativamente JPEG, PNG, TIFF, WebP e BMP.

**RAW** (NEF di Nikon, RAF di Fuji, DNG di Ricoh, ARW, CR2, CR3). Lo script tenta
`rawpy`. Se manca, installalo nello spazio di lavoro:

```bash
pip install rawpy --break-system-packages
```

Il RAW viene sviluppato in modo neutro a mezza risoluzione, quindi le misure di
luminosità, contrasto e saturazione sono quelle del file **non sviluppato**: sono
utili per capire i margini di recupero, non per giudicare il colore. Dillo nel
report. Se l'utente ha anche i JPEG o i TIFF sviluppati, chiedi quelli: per
l'editing servono le immagini nella forma in cui verranno viste.

**HEIC / HEIF** (iPhone). Lo script tenta `pillow-heif`:

```bash
pip install pillow-heif --break-system-packages
```

**File saltati.** Lo script non si ferma mai su un file illeggibile: lo elenca in
`saltati.csv` con il motivo. Controlla sempre quel file e riferisci all'utente
quanti e quali file sono rimasti fuori. Un'analisi su 47 file quando la cartella ne
conteneva 52 senza dirlo è un'analisi sbagliata.

**Doppioni JPEG + RAW.** Se trovi coppie con lo stesso nome base e due estensioni
(`DSCF1234.RAF` e `DSCF1234.JPG`), analizza una sola versione, di norma il JPEG, e
dichiaralo. Non trattarle come due immagini: falserebbero i conteggi e i cluster.

## 6. Cosa produce prepara_provino.py

```bash
python3 scripts/prepara_provino.py /percorso/cartella -o /percorso/_analisi
```

Opzioni utili: `--lato-thumb 1400` per miniature più grandi (utile se vuoi
giudicare dettagli), `--per-griglia 9` per griglie meno dense (utile su immagini
molto scure o molto dense).

| Output | Uso |
|---|---|
| `thumbs/P001_nome.jpg` | quello che apri con Read quando devi giudicare davvero |
| `griglie/griglia_01.jpg` | il provino a contatto etichettato, per il passaggio cieco e per la visione d'insieme |
| `metriche.csv` e `metriche.json` | i numeri, uno per immagine |
| `coppie_simili.csv` | le coppie con distanza di hash bassa, cioè le ridondanze candidate |
| `firma.json` | le aggregazioni: focali, aperture, ISO, ore del giorno, orientamenti, chiavi tonali, corpi e ottiche |
| `saltati.csv` | i file non leggibili, con motivo |

**Come guardare, in pratica.** Le griglie prima, sempre, e sono economiche: 12
immagini per file. Poi apri le singole miniature solo per le immagini che stai
davvero valutando (in un edit da 60 file sono in genere 20 o 25). Su un archivio da
oltre 100 file, resta sulle griglie per il triage e apri le miniature solo delle
sopravvissute. Dichiara sempre a che livello hai guardato ogni immagine.

### Le metriche, e come non usarle male

| Campo | Cosa dice | Trappola |
|---|---|---|
| `mp`, `larghezza`, `altezza` | risoluzione reale dell'originale | è l'unico dato legittimo per parlare di dimensione di stampa |
| `clip_neri_pc`, `clip_bianchi_pc` | percentuale di pixel a 0 o a 255 | un po' di nero pieno è struttura, non errore. Sopra il 2 percento sui bianchi, in genere, è informazione perduta |
| `luminanza_media`, `p5`, `p95` | dove sta la massa tonale | serve per la chiave tonale e per verificare la coerenza di una sequenza |
| `contrasto` | deviazione standard della luminanza | basso non è brutto: è piatto, e la piattezza può essere voluta |
| `saturazione_media`, `colorfulness` | quanta materia cromatica | sotto soglia lo script marca l'immagine come probabile bianco e nero |
| `hue_dominante`, `nome_colore` | dominante cromatica | utile per i cluster di colore e per le sequenze, non per giudicare il bilanciamento del bianco |
| `nitidezza` | varianza del laplaciano, normalizzata | **è calcolata sulla miniatura**, quindi confronta immagini fra loro, non misura la qualità assoluta dell'ottica |
| `rumore_proxy` | scarto sulle zone piatte | stima, non misura. Aumenta con la grana voluta esattamente come con il rumore indesiderato |
| `entropia` | densità di informazione | alta significa affollata, non ricca |
| `dhash` | impronta visiva | serve solo per le distanze fra coppie |

Le due che cambiano più spesso una decisione editoriale: `clip_bianchi_pc` (una
foto con le alte luci bruciate non va in stampa grande) e `dhash` (le ridondanze
che l'occhio non vede perché ha guardato quelle foto cento volte).

## 7. Riportare gli output sul computer dell'utente

Due consegne, sempre entrambe, mai una sola.

**In chat**, con `SendUserFile`: funziona da ogni dispositivo, anche dal telefono, e
serve perché l'utente veda subito il risultato.

**Sul disco**, con `mcp__remote-devices__device_commit_files`, dentro
`<cartella delle immagini>/_analisi/`. Questa è la consegna che l'utente considera
la consegna vera: ha indicato una cartella di fotografie, e si aspetta di trovare il
lavoro accanto alle fotografie. Non chiedere il permesso e non rimandarla a una
proposta finale del tipo "se vuoi te li scrivo anche sul Mac": farlo e dirlo è
corretto, offrirlo e non farlo è una consegna mancata.

### La trappola dei file uuid

`device_commit_files` accetta solo un `fileUuid` restituito da una precedente
chiamata a `SendUserFile`. Non esiste un modo di scrivere sul disco un file che non
sia prima passato per la chat. Quindi, se committi trenta file uno per uno, produci
trenta schede in conversazione e la rendi illeggibile.

**La soluzione, sempre questa.** Due gruppi:

1. **Sciolti**, perché l'utente li apre uno per uno: `report.md`, `provino.html`,
   `tabella.xlsx` (o `.csv`), `analisi.json`, e `dummy.pdf` se esiste. Sono da 4 a 5
   file, quindi da 4 a 5 schede: accettabile, ed è esattamente quello che vuole vedere.
2. **In un archivio**, tutto il resto del materiale di lavoro: `thumbs/`, `griglie/`,
   `metriche.csv` e `.json`, `coppie_simili.csv`, `firma.json`, `saltati.csv`,
   `passaggio_cieco.md`, `tabella.csv`. Comprimi la cartella `_analisi` intera in un
   solo file, per esempio `analisi-completa.zip`, mandalo con una sola SendUserFile e
   committi quello. Una scheda invece di trenta.

Sequenza concreta:

```bash
cd <spazio di lavoro> && zip -qr analisi-completa.zip _analisi
```

poi `SendUserFile` sui file sciolti (una sola chiamata con la lista) e su
`analisi-completa.zip`, e infine una sola `device_commit_files` con tutte le voci,
ciascuna col suo `devicePath` sotto `_analisi/`.

Controlla il limite di 20 MB per file: se lo zip lo supera, escludi `thumbs/` e
committi quelle solo su richiesta, dicendolo.

### Verifica e chiusura

Dopo il commit fai una `device_list_dir` su `_analisi` e conferma all'utente
l'elenco dei file scritti, con il percorso. Se una voce risulta in `rejected`,
riferiscilo invece di dare la consegna per fatta.

**Se nessun dispositivo è collegato**, o `device_commit_files` fallisce: consegna in
chat, dillo esplicitamente in una riga (i file non sono sul disco, ecco perché) e
spiega che basta collegare la cartella perché tu li scriva. Non lasciare che l'utente
scopra da solo che la cartella è vuota.

### Dove esattamente

Il valore predefinito di `prepara_provino.py` è già `<cartella immagini>/_analisi`,
quindi la struttura giusta esiste dal primo comando: committi rispettando quella.

Se la cartella delle immagini è una cartella di lavoro dell'utente e non una cartella
per progetto (per esempio il Desktop, o una cartella condivisa), scrivi comunque in
`_analisi` lì dentro, e solo dopo, in chiusura, proponi la convenzione
`Portfolio-Analisi/<nome-progetto>/` della sezione 1 come riordino per le sessioni
future. Prima consegni dove l'utente si aspetta, poi proponi il posto migliore.

Nota su `analisi.json`: è il file che rende possibile il confronto longitudinale
della prossima sessione. Se finisce solo nello spazio di lavoro della sessione,
sparisce con la sessione. Va sempre fra i file sciolti, sempre committato.

## 8. Problemi frequenti

**Le miniature sono ruotate male.** Lo script applica l'orientamento EXIF. Se una
immagine risulta comunque girata, il file ha un EXIF incoerente: correggi a mano e
segnalalo, non giudicare la composizione di una foto ruotata.

**Tutti i file hanno la stessa data e ora.** Sono passati da un software che ha
riscritto i metadati. In quel caso la ricostruzione temporale del progetto non è
determinabile: dillo e non inventare una cronologia.

**Nessun EXIF.** Capita con export da Lightroom con i metadati rimossi, con
screenshot e con immagini scaricate. `firma.json` sarà povero: la parte di firma
d'autore basata su focali e aperture non si può fare, e la parte basata sui numeri
visivi (chiave tonale, orientamento, densità, colore) sì. Fai quella e dichiara
l'altra come non determinabile.

**La cartella contiene anche non immagini** (PDF, testi, provini già fatti). Lo
script li ignora e li elenca in `saltati.csv`. Se contiene una sottocartella con
altre foto, lo script non entra: chiedi all'utente se includerla.
