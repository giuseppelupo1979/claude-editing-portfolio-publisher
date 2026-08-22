# editing-portfolio-publisher

Fork autonomo di
[`editing-portfolio`](https://github.com/giuseppelupo1979/claude-editing-portfolio-fotografico)
che unisce due lavori distinti:

1. analisi ed editing di una cartella di fotografie;
2. preparazione, staging e pubblicazione della selezione su un portfolio Directus
   raggiungibile tramite SSH.

La skill originale resta il riferimento editoriale. Questo fork aggiunge una
pipeline di pubblicazione configurabile senza incorporare credenziali, indirizzi
privati o dettagli obbligatori di uno specifico sito.

La regola centrale è semplice: **prima si decide cosa merita di essere pubblicato,
poi si costruiscono i dati CMS, infine si modifica il sito solo dopo due conferme**.

## Indice

1. [Cosa fa](#1-cosa-fa)
2. [Architettura](#2-architettura)
3. [Requisiti](#3-requisiti)
4. [Installazione locale](#4-installazione-locale)
5. [Struttura del profilo JSON SSH](#5-struttura-del-profilo-json-ssh)
6. [Preparazione del VPS e di Directus](#6-preparazione-del-vps-e-di-directus)
7. [Workflow di analisi](#7-workflow-di-analisi)
8. [Deliverable](#8-deliverable)
9. [Dummy PDF](#9-dummy-pdf)
10. [Blocco pubblicazione in analisi.json](#10-blocco-pubblicazione-in-analisijson)
11. [Publication plan](#11-publication-plan)
12. [Comandi di pubblicazione](#12-comandi-di-pubblicazione)
13. [Stati, idempotenza e recupero](#13-stati-idempotenza-e-recupero)
14. [Sicurezza e file da non pubblicare](#14-sicurezza-e-file-da-non-pubblicare)
15. [Test e validazione](#15-test-e-validazione)
16. [Aggiornamenti dall’upstream](#16-aggiornamenti-dallupstream)
17. [Problemi frequenti](#17-problemi-frequenti)

## 1. Cosa fa

L’analisi fotografica comprende:

- ingestione di JPEG, TIFF, PNG e, con dipendenze opzionali, RAW e HEIC;
- miniature orientate correttamente e griglie di provino;
- passaggio cieco prima di leggere EXIF e metriche;
- misure di esposizione, contrasto, colore, nitidezza, rumore e similarità;
- valutazione di ogni immagine sui sei assi editoriali;
- fil rouge, cluster, ridondanze, lacune e firma d’autore;
- selezione principale, alternativa radicale e scarto difeso;
- titolo, introduzione, statement, descrizioni e didascalie;
- sequenza a spread e proposta di copertina;
- provino HTML, tabelle, testi e dummy PDF completo;
- proposta di pubblicazione su galleria nuova o esistente;
- staging in Directus e pubblicazione del sito tramite rebuild.

La pubblicazione non è automatica. La skill può proporla durante l’analisi, ma non
può caricare file senza approvazione e non può mettere online le bozze senza una
seconda conferma esplicita.

## 2. Architettura

```text
Cartella fotografie
        │
        ▼
analisi.json + metriche.json + publication-plan.json
        │
        │  ssh/scp con chiave locale
        ▼
VPS: job temporaneo + remote_directus.mjs
        │
        │  token letto solo sul VPS
        ▼
Directus API: files, photos, galleries
        │
        ▼
rebuild del sito statico
        │
        ▼
verifica URL pubblici
```

Il client locale non legge mai il token Directus. Conosce soltanto i parametri SSH
e il percorso remoto del file token. L’helper sul VPS usa le API Directus e salva
un manifest dopo ogni creazione.

### Componenti

| Componente | Dove vive | Responsabilità |
|---|---|---|
| `SKILL.md` | repository e installazione locale | regole editoriali e confini di autorizzazione |
| `genera_payload_pubblicazione.py` | locale | trasforma il blocco `pubblicazione` nel piano validato |
| `publish_directus.mjs` | locale | SSH, SCP, controlli locali, staging, release e verifica live |
| `remote_directus.mjs` | VPS | schema Directus, duplicati, upload, record, pubblicazione e rebuild |
| profilo JSON | solo computer dell’utente | host, porta, chiave, schema e comandi |
| token Directus | solo VPS | autenticazione API con permessi minimi |
| `publication-manifest.json` | locale e VPS | ID, hash e stato di ogni operazione |

## 3. Requisiti

### Computer locale

- macOS o Linux;
- Python 3.8 o superiore;
- Node.js 20 o superiore, consigliato Node.js 22;
- `ssh` e `scp` OpenSSH;
- una chiave SSH funzionante verso il VPS;
- accesso in scrittura alla cartella delle fotografie.

Dipendenze Python:

```bash
pip install pillow numpy openpyxl
pip install rawpy pillow-heif
```

`rawpy` e `pillow-heif` sono opzionali. `openpyxl` serve solo per `tabella.xlsx`.

### VPS

- Node.js 20 o superiore;
- utente SSH senza login tramite password, preferibilmente dedicato;
- accesso HTTPS al CMS Directus;
- spazio temporaneo sufficiente per le fotografie;
- helper remoto installato dalla skill;
- file token Directus con permessi `600`;
- comando di rebuild non interattivo e con timeout ragionevole.

### Directus

È richiesto un utente tecnico o una policy dedicata con:

- lettura dello schema delle collezioni interessate;
- lettura, creazione e aggiornamento dei file;
- lettura, creazione e aggiornamento di fotografie e gallerie;
- nessun permesso di cancellazione;
- nessun accesso diretto al database;
- nessun ruolo amministratore generale.

Le collezioni e i campi possono avere nomi diversi: vengono tradotti dal profilo
JSON. Sono obbligatori i concetti di immagine, titolo, alt text, ordinamento, stato
pubblicato e relazione con la galleria.

## 4. Installazione locale

Clona il fork e installa la cartella skill:

```bash
git clone https://github.com/giuseppelupo1979/claude-editing-portfolio-publisher.git
cp -R claude-editing-portfolio-publisher/editing-portfolio-publisher \
  ~/.codex/skills/editing-portfolio-publisher
```

Per rigenerare il pacchetto e l’inventario:

```bash
./build-skill.sh
```

Il repository può convivere con la skill originale perché il nome interno è
`editing-portfolio-publisher`.

## 5. Struttura del profilo JSON SSH

Il profilo reale deve vivere fuori dal repository, per esempio:

```text
~/.config/editing-portfolio-publisher/sites/mio-portfolio.json
```

Imposta permessi restrittivi:

```bash
chmod 600 ~/.config/editing-portfolio-publisher/sites/mio-portfolio.json
```

Struttura completa:

```json
{
  "profile_version": 1,
  "id": "mio-portfolio",
  "provider": "directus-over-ssh",
  "cms_url": "https://cms.example.com",
  "site_url": "https://portfolio.example.com",
  "ssh": {
    "host": "portfolio.example.com",
    "port": 22,
    "user": "publisher",
    "identity_file": "/Users/nome/.ssh/portfolio_publisher_ed25519",
    "remote_workdir": "/home/publisher/.local/share/editing-portfolio-publisher",
    "remote_helper": "/home/publisher/.local/share/editing-portfolio-publisher/remote_directus.mjs"
  },
  "directus": {
    "token_file": "/home/publisher/.config/editing-portfolio-publisher/directus-token",
    "collections": {
      "photos": "photos",
      "galleries": "galleries"
    },
    "fields": {
      "photo": {
        "image": "image",
        "title_it": "title_it",
        "title_en": "title_en",
        "alt_it": "alt_it",
        "alt_en": "alt_en",
        "lat": "lat",
        "lng": "lng",
        "place": "place",
        "camera": "camera",
        "taken_at": "taken_at",
        "sort": "sort",
        "featured": "featured",
        "published": "published",
        "gallery": "gallery",
        "street": "street",
        "portrait": "portrait",
        "source_hash": null
      },
      "gallery": {
        "slug": "slug",
        "title_it": "title_it",
        "title_en": "title_en",
        "description_it": "description_it",
        "description_en": "description_en",
        "cover": "cover",
        "sort": "sort",
        "published": "published",
        "filter_flag": "filter_flag"
      }
    }
  },
  "rebuild": {
    "command": ["bash", "/home/publisher/portfolio-rebuild.sh"]
  },
  "verification": {
    "routes": [
      "/portfolio/{slug}/",
      "/en/portfolio/{slug}/"
    ],
    "expected_text": "{title_it}"
  }
}
```

### Significato dei campi

| Campo | Significato |
|---|---|
| `profile_version` | versione del contratto, attualmente `1` |
| `id` | nome stabile richiamato dal piano di pubblicazione |
| `cms_url` | endpoint HTTPS pubblico o interno di Directus |
| `site_url` | origine del sito da verificare dopo il rebuild |
| `ssh.host` | hostname o IP del VPS |
| `ssh.port` | porta SSH |
| `ssh.user` | utente remoto |
| `ssh.identity_file` | percorso assoluto della chiave privata, non il suo contenuto |
| `ssh.remote_workdir` | cartella dei job e dell’helper sul VPS |
| `ssh.remote_helper` | percorso assoluto dello script remoto |
| `directus.token_file` | file remoto che contiene solo il token API |
| `collections` | nomi reali delle collezioni Directus |
| `fields.photo` | mappa campo canonico → campo Directus delle fotografie |
| `fields.gallery` | mappa campo canonico → campo Directus delle gallerie |
| `rebuild.command` | comando e argomenti eseguiti senza shell interattiva |
| `verification.routes` | URL relativi da controllare dopo la release |
| `expected_text` | testo atteso nell’HTML, con placeholder della galleria |

Un campo opzionale non presente nel CMS può essere impostato a `null`. I percorsi
locali e remoti devono essere assoluti e senza spazi.

### Cosa non deve stare nel JSON

- password SSH;
- contenuto della chiave privata;
- passphrase della chiave;
- token Directus;
- credenziali amministratore Directus;
- URL webhook contenenti segreti;
- password sudo.

Il profilo indica **dove** si trovano chiave e token, non li incorpora.

## 6. Preparazione del VPS e di Directus

### Chiave SSH

Usa una chiave dedicata e imposta `chmod 600` sul file privato. L’autenticazione
deve funzionare in modalità non interattiva e con `BatchMode=yes`.

È preferibile limitare la chiave all’utente che può leggere il token, gestire la
cartella di lavoro ed eseguire il rebuild, senza privilegi generali di root.

### Token Directus

1. Crea un utente tecnico Directus.
2. Assegna solo i permessi elencati nei requisiti.
3. Genera un token statico dedicato.
4. Sul VPS crea il file indicato da `directus.token_file`.
5. Scrivi il token senza lasciarlo nella cronologia della shell.
6. Imposta proprietario corretto e permessi `600`.

L’helper rifiuta un token file leggibile da gruppo o altri utenti.

### Installazione dell’helper remoto

Operazione una tantum:

```bash
node editing-portfolio-publisher/scripts/publish_directus.mjs install-remote \
  --profile ~/.config/editing-portfolio-publisher/sites/mio-portfolio.json \
  --confirm
```

Questo comando crea la cartella remota e copia soltanto:

- `remote_directus.mjs`;
- `lib/publisher-core.mjs`.

Non trasferisce token, password o chiavi.

## 7. Workflow di analisi

La pipeline editoriale resta quella dell’upstream:

1. controllo di integrità della skill;
2. ingestione e misure;
3. passaggio cieco sulle sole griglie;
4. lettura singola di tutte le immagini;
5. lettura del corpus, cluster e ridondanze;
6. selezione con numero fissato prima;
7. titolo, testi, sequenza e copertina;
8. generazione e verifica dei deliverable;
9. proposta di pubblicazione, quando richiesta.

Una nuova galleria non viene creata per ogni fotografia. Una serie editoriale ha
una sola galleria e tutte le fotografie selezionate puntano allo stesso ID.

## 8. Deliverable

Nella cartella `_analisi` vengono prodotti:

| File | Contenuto |
|---|---|
| `analisi.json` | contratto editoriale completo e sorgente degli altri output |
| `metriche.json/.csv` | misure per immagine ed EXIF |
| `firma.json` | aggregazioni su attrezzatura, focali, orari e orientamenti |
| `coppie_simili.csv` | ridondanze candidate |
| `passaggio_cieco.md` | prima impressione registrata prima delle metriche |
| `report.md` | lettura critica del corpus |
| `testi.md` | titoli, introduzione, statement, descrizioni e didascalie |
| `tabella.csv/.xlsx` | punteggi per libro, mostra, web e concorso |
| `provino.html` | provino interattivo autonomo con immagini incorporate |
| `dummy.pdf` | anteprima completa del libro basata sulla sequenza proposta |
| `publication-plan.json` | piano CMS approvabile, senza credenziali |
| `publication-manifest.json` | ID e hash prodotti dallo staging |

`dummy.pdf` viene generato per `insieme`, `photo-editor`, `galleria` e
`pubblicazione-sito` quando esiste un edit ordinato. Non viene inventato nelle
modalità `triage`, `crescita` o in una richiesta che non prevede sequenza.

## 9. Dummy PDF

Comando:

```bash
python3 editing-portfolio-publisher/scripts/genera_dummy_pdf.py \
  /percorso/_analisi/analisi.json \
  --metriche /percorso/_analisi/metriche.json \
  -o /percorso/_analisi/dummy.pdf
```

Il dummy contiene:

- quarta di copertina e copertina con immagine scelta;
- titolo, sottotitolo e autore;
- frontespizio;
- introduzione prima o dopo le tavole secondo `introduzione_posizione`;
- spread nell’ordine dichiarato, incluse pagine bianche e pagine multiple;
- didascalie sotto le immagini;
- statement e nota dell’autore;
- indice delle tavole;
- scheda completa di ogni fotografia con file, titolo, descrizione e didascalia;
- elenco dell’attrezzatura ricavato da `metriche.json`;
- corpi, ottiche, focali reali ed equivalenti presenti negli EXIF;
- copertura EXIF, cioè quante tavole possiedono dati leggibili;
- colophon con formato, data del dummy e avvertenza sulle miniature.

L’attrezzatura non viene dedotta visivamente. Se gli EXIF sono assenti, il PDF
dichiara che il dato non è determinabile.

Il dummy serve a giudicare sequenza, respiro e relazione fra testo e immagini. Le
miniature non sono adatte alla stampa definitiva.

## 10. Blocco pubblicazione in analisi.json

Prima di generare il piano, l’agente aggiunge ad `analisi.json`:

```json
{
  "pubblicazione": {
    "source_dir": "/percorso/assoluto/alle/foto",
    "location_defaults": {
      "place": "Napoli, Italia",
      "lat": 40.8518,
      "lng": 14.2681,
      "precision": "approximate",
      "confirmed_by_user": true
    },
    "gallery": {
      "action": "create",
      "existing_id": null,
      "slug": "nome-serie",
      "title_it": "Titolo italiano",
      "title_en": "English title",
      "description_it": "Descrizione editoriale della serie.",
      "description_en": "Editorial description of the series.",
      "cover_file": "foto-cover.jpg",
      "sort": null,
      "filter_flag": null
    },
    "photos": [
      {
        "id": "P003",
        "order": 1,
        "title_it": "Titolo",
        "title_en": "Title",
        "alt_it": "Descrizione accessibile di ciò che si vede.",
        "alt_en": "Accessible description of what is visible.",
        "camera": "Corpo e ottica da EXIF",
        "taken_at": "2026-01-15",
        "featured": true,
        "street": false,
        "portrait": false
      }
    ]
  }
}
```

`id` collega la proposta alla fotografia già presente in `immagini`. Il nome file,
la descrizione di lavoro e la didascalia vengono recuperati da lì quando non sono
ripetuti nel blocco.

`lat` e `lng` vengono prima cercati negli EXIF di `metriche.json`. I valori della
singola foto hanno precedenza sul default di progetto. `location_defaults` è utile
per una serie interamente scattata nello stesso luogo, ma viene usato soltanto
quando `confirmed_by_user` è `true`. Imposta `precision` a `approximate` per il
centro di una città o un punto rappresentativo, e a `exact` solo quando la
posizione è effettiva.

Quando gli EXIF contengono GPS ma non un nome leggibile, l'agente tenta il reverse
geocoding e registra `reverse-geocoded` come origine. Un risultato ambiguo non viene
accettato automaticamente: richiede conferma dell'utente.

Nel `publication-plan.json` risultante vengono aggiunti automaticamente
`location_source` e `location_precision`, così rimane verificabile se il punto
proviene da EXIF, da dati espliciti o dal default confermato della serie.

Se mancano `place`, `lat` o `lng`, la generazione si ferma e indica le fotografie
incomplete. In quel momento l'agente deve chiedere all'utente il luogo, oppure la
conferma che un unico punto approssimativo sia valido per tutta la serie. Questo
controllo impedisce di pubblicare fotografie che non comparirebbero nella Mappa.

## 11. Publication plan

Il piano usa `plan_version=2`. La versione 2 rende obbligatori `place`, `lat`,
`lng`, `location_source` e `location_precision` per ogni fotografia.

Generazione:

```bash
python3 editing-portfolio-publisher/scripts/genera_payload_pubblicazione.py \
  /percorso/_analisi/analisi.json \
  --profile-id mio-portfolio \
  --source-dir /percorso/alle/foto \
  --metriche /percorso/_analisi/metriche.json \
  -o /percorso/_analisi/publication-plan.json
```

Il piano nasce con:

```json
"approval": {
  "approved": false,
  "approved_at": null,
  "approved_by": null
}
```

Dopo l’approvazione editoriale si aggiornano questi campi. `stage` rifiuta un piano
non approvato anche se viene passato `--confirm`.

Il piano non contiene token, password o dati SSH. Contiene solo contenuti e
metadati destinati al CMS.

## 12. Comandi di pubblicazione

### Doctor

```bash
node editing-portfolio-publisher/scripts/publish_directus.mjs doctor \
  --profile ~/.config/editing-portfolio-publisher/sites/mio-portfolio.json
```

Controlla chiave SSH, helper remoto, permessi del token, salute Directus e campi
obbligatori. Non crea record e non carica fotografie.

### Plan

```bash
node editing-portfolio-publisher/scripts/publish_directus.mjs plan \
  --profile ~/.config/editing-portfolio-publisher/sites/mio-portfolio.json \
  --plan /percorso/_analisi/publication-plan.json
```

Calcola SHA-256 locali e cerca duplicati per slug, nome file, titolo e hash quando
il CMS possiede un campo `source_hash`. Non muta Directus.

### Stage

```bash
node editing-portfolio-publisher/scripts/publish_directus.mjs stage \
  --profile ~/.config/editing-portfolio-publisher/sites/mio-portfolio.json \
  --plan /percorso/_analisi/publication-plan.json \
  --confirm
```

Trasferisce piano e immagini in un job remoto, crea la galleria in bozza, carica i
file e crea le fotografie con `published=false`. Non esegue il rebuild.

### Release

```bash
node editing-portfolio-publisher/scripts/publish_directus.mjs release \
  --profile ~/.config/editing-portfolio-publisher/sites/mio-portfolio.json \
  --manifest /percorso/_analisi/publication-manifest.json \
  --confirm
```

Imposta le fotografie come pubblicate, pubblica la nuova galleria, esegue il
rebuild e verifica le route configurate.

## 13. Stati, idempotenza e recupero

Il manifest attraversa questi stati:

```text
staging → staged → release_partial → released
```

Dopo ogni upload e ogni creazione vengono salvati:

- SHA-256 del file sorgente;
- ID del file Directus;
- ID del record fotografico;
- ID della galleria;
- timestamp di staging e release;
- risultato sintetico del rebuild.

Se la connessione cade, una nuova esecuzione legge il manifest remoto e riprende
dall’ultimo ID salvato. Non effettua cancellazioni automatiche. Se il manifest è
perso ma Directus contiene già file omonimi, `plan` blocca l’operazione invece di
duplicarli.

## 14. Sicurezza e file da non pubblicare

Il repository pubblico non deve contenere:

- profili JSON reali;
- chiavi `*.pem`, `id_rsa`, `id_ed25519` o equivalenti;
- file `.env`;
- esportazioni di password;
- token Directus;
- manifest di produzione, quando rivelano struttura interna non desiderata;
- documentazione infrastrutturale privata.

Prima di ogni pubblicazione del repository esegui il test anti-segreti incluso.
I log applicano redazione ricorsiva alle chiavi che contengono `token`, `secret`,
`password`, `authorization` o `private_key`.

La cartella infrastrutturale di un VPS non deve essere copiata dentro questo fork.

## 15. Test e validazione

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
node --test tests/*.test.mjs
python3 /percorso/skill-creator/scripts/quick_validate.py \
  editing-portfolio-publisher
./build-skill.sh
```

I test coprono:

- validazione del profilo SSH;
- rifiuto di password e token incorporati;
- redazione dei log;
- mapping dei campi Directus;
- validazione del piano;
- generazione del payload;
- conversione delle coordinate GPS EXIF;
- blocco dei piani senza luogo e coordinate;
- uso dei default geografici solo dopo conferma dell'utente;
- stabilità dell’ID di ripresa al cambiare dei metadati di approvazione;
- estrazione dell’attrezzatura EXIF dalle sole tavole selezionate;
- scansione anti-segreti del repository.

I test locali non contattano il sito reale e non modificano Directus.

## 16. Aggiornamenti dall’upstream

Il repository originale resta configurato come remote `upstream`:

```bash
git fetch upstream
git merge upstream/main
```

Dopo il merge:

1. risolvi eventuali conflitti mantenendo il nome del fork;
2. riesegui tutti i test;
3. rigenera pacchetto e inventario;
4. verifica che i file di pubblicazione siano ancora referenziati da `SKILL.md`.

## 17. Problemi frequenti

**`doctor` segnala chiave troppo aperta.** Imposta `chmod 600` o `chmod 400` sulla
chiave privata.

**Il token remoto viene rifiutato.** Controlla proprietario, permessi `600`, valore
non vuoto e permessi della policy Directus.

**Lo schema non coincide.** Correggi la mappa `directus.fields`; non rinominare i
campi del CMS alla cieca.

**`plan` trova duplicati.** Apri Directus e confronta slug, titolo, file e hash. Non
forzare lo staging finché il conflitto non è spiegato.

**Il rebuild fallisce dopo la pubblicazione.** Il manifest resta
`release_partial`. Non cancellare record; correggi il rebuild e riesegui `release`.

**La pagina risponde 200 ma il controllo testo fallisce.** Verifica
`verification.expected_text`, lingua della route e cache del sito.

**Il dummy non mostra l’attrezzatura.** Controlla che `metriche.json` sia accanto ad
`analisi.json`, che i nomi file coincidano e che gli export conservino gli EXIF.

## Licenza e crediti

MIT, vedi `LICENSE`.

Il lavoro editoriale deriva da `editing-portfolio`. Il modulo SSH/Directus e il
dummy esteso appartengono a questo fork.
