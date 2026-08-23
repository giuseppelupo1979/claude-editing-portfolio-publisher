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
18. [Rilascio](#18-rilascio)

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
Directus API: permissions, fields, files, photos, galleries
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

Prima della trasmissione il client riduce il profilo alla forma canonica necessaria
sul VPS, omettendo l’intera sezione `ssh`. Il client e l’helper applicano validatori
distinti: il primo richiede i dati di trasporto, il secondo soltanto la configurazione
runtime di Directus, rebuild e verifica.

### Componenti

| Componente | Dove vive | Responsabilità |
|---|---|---|
| `SKILL.md` | repository e installazione locale | regole editoriali e confini di autorizzazione |
| `verifica_integrita.py` | locale | confronta byte e SHA-256 di ogni file con `references/integrita.json`. È il primo comando di ogni sessione |
| `lib/accenti.py` | locale | riconosce gli apostrofi usati al posto degli accenti. Avvisa nei testi di lavoro, blocca in quelli destinati al sito |
| `pipeline_incrementale.py` | locale | inventario SHA-256, approvazione hashata della pubblicazione e grafo di rigenerazione |
| `genera_payload_pubblicazione.py` | locale | trasforma il blocco `pubblicazione` nel piano validato |
| `publish_directus.mjs` | locale | SSH, SCP, provisioning autorizzato, controlli locali, staging, release e verifica live |
| `remote_directus.mjs` | VPS | provisioning tecnico, schema Directus, duplicati, upload, record, pubblicazione e rebuild |
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
- token e binding sotto `$HOME/.config/editing-portfolio-publisher/`, directory
  `700`, file regolari `600`, nessun symlink;
- comando di rebuild non interattivo e con timeout ragionevole.

### Directus

È richiesto un utente tecnico con ruolo e policy namespaced per profilo e CMS. La
matrice `collection/action/fields` è calcolata dal mapping, mostrata dal preflight
e legata all'approvazione tramite hash. In sintesi comprende:

- `directus_fields`: lettura dello schema;
- `directus_files`: lettura e creazione;
- collezione fotografie: lettura, creazione e aggiornamento;
- collezione gallerie: lettura, creazione e aggiornamento;
- nessun permesso di cancellazione;
- `admin_access=false` e `app_access=false`;
- nessun accesso diretto al database;
- nessun ruolo amministratore generale.

L’utente tecnico non ha alcun permesso su `directus_users`, e questo ha una
conseguenza che vale la pena conoscere prima di scriverci sopra del codice:
Directus risponde a `/users/me` con il solo `id`. Ruolo, stato e marcatore non
sono leggibili da quel token, e vanno verificati con il client amministrativo
durante il provisioning, oppure dedotti da `/permissions/me`, che dice cosa il
token può fare invece di come è etichettato.

Le collezioni e i campi possono avere nomi diversi: vengono tradotti dal profilo
JSON. Non sono ammessi wildcard di collezione. I mapping essenziali non possono
essere `null`; la matrice campo per campo è definita in
`references/pubblicazione-sito.md`.

## 4. Installazione locale

Clona il fork e installa la cartella skill nella directory delle skill del tuo
ambiente:

```bash
git clone https://github.com/giuseppelupo1979/claude-editing-portfolio-publisher.git
cp -R claude-editing-portfolio-publisher/editing-portfolio-publisher \
  ~/.codex/skills/editing-portfolio-publisher
```

In alternativa distribuisci `editing-portfolio-publisher.skill`, che è lo stesso
contenuto in un archivio zip.

Subito dopo l’installazione verifica la copia:

```bash
python3 ~/.codex/skills/editing-portfolio-publisher/scripts/verifica_integrita.py
```

Deve rispondere `Integrita: OK`. È lo stesso comando che la skill esegue in F0 a
ogni sessione: confronta byte e SHA-256 di ogni file, `SKILL.md` compreso, con
`references/integrita.json`.

Il repository può convivere con la skill originale perché il nome interno è
`editing-portfolio-publisher`. **Non tenerle però attive tutte e due**: le
descrizioni si sovrappongono e non è prevedibile quale delle due scatti su una
richiesta di editing. Questa contiene l’altra, quindi se installi questa
disinstalla `editing-portfolio`.

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
    "token_file": "/home/publisher/.config/editing-portfolio-publisher/mio-portfolio/directus-token",
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
| `directus.token_file` | file remoto confinato sotto `$HOME/.config/editing-portfolio-publisher/`; il binding lo lega a profilo, CMS, utente e policy |
| `collections` | nomi reali delle collezioni Directus |
| `fields.photo` | mappa campo canonico → campo Directus delle fotografie |
| `fields.gallery` | mappa campo canonico → campo Directus delle gallerie |
| `rebuild.command` | comando e argomenti eseguiti senza shell interattiva |
| `verification.routes` | URL relativi da controllare dopo la release |
| `expected_text` | testo atteso nell’HTML, con placeholder della galleria |

I mapping essenziali non possono essere omessi né impostati a `null`. Per le foto
sono `image`, `title_it`, `title_en`, `alt_it`, `alt_en`, `lat`, `lng`, `place`,
`sort`, `published` e `gallery`; per le gallerie sono `slug`, `title_it`,
`title_en`, `description_it`, `description_en`, `cover`, `sort` e `published`.
Solo i mapping opzionali dichiarati dallo schema possono essere `null`. Collezioni
e campi sono identificatori applicativi, senza wildcard; le collezioni configurate
non possono usare il prefisso riservato `directus_`. I percorsi locali e remoti
devono essere assoluti e quelli remoti non possono contenere spazi.

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

### Provisioning dell'utente tecnico e del token

È un'operazione una tantum, separata dallo staging e dalla release. Il primo
comando è un preflight locale: non apre SSH e non esegue mutazioni.

```bash
node editing-portfolio-publisher/scripts/publish_directus.mjs provision \
  --profile ~/.config/editing-portfolio-publisher/sites/mio-portfolio.json \
  --admin-env /percorso/remoto/directus/.env \
  --service-email portfolio-publisher@tuodominio.it
```

L'output descrive CMS, email, identità namespaced, percorsi e matrice esatta
`collection/action/fields`, poi produce `authorization_hash`. Fai approvare
separatamente quel documento e applica gli stessi argomenti con l'hash approvato:

```bash
node editing-portfolio-publisher/scripts/publish_directus.mjs provision \
  --profile ~/.config/editing-portfolio-publisher/sites/mio-portfolio.json \
  --admin-env /percorso/remoto/directus/.env \
  --service-email portfolio-publisher@tuodominio.it \
  --confirm \
  --authorization-hash HASH_APPROVATO
```

L'apply ricalcola il documento prima di SSH. Se profilo, email, CMS, mapping,
percorso amministrativo o permessi sono cambiati, l'hash non coincide e serve una
nuova approvazione.

L'email deve usare un dominio DNS reale collegato all'hostname di `cms_url`;
localhost, IP, TLD riservati e domini `example.com`, `example.net`, `example.org`
o `example.edu` sono rifiutati localmente. Il file indicato da `--admin-env`
resta sul VPS: deve essere un file regolare, non symlink, con permessi esatti
`600`, e il suo
`PUBLIC_URL` deve coincidere esattamente con il `cms_url` canonico.

Ruolo e policy sono namespaced deterministicamente per `profile.id` e CMS. La
policy consente solo la matrice riportata dal preflight, senza wildcard di
collezione, `delete`, `admin_access` o `app_access`. Il token e il relativo binding
restano sotto `$HOME/.config/editing-portfolio-publisher/`, con directory `700`,
file `600`, proprietario verificato e nessun symlink. Il binding associa il token
a profilo, CMS, utente tecnico e policy, per impedirne il riuso trasversale.

Ogni creazione o riconciliazione viene annotata in un journal atomico privo di
segreti. Una nuova esecuzione con lo stesso hash riprende in modo idempotente; non
esegue cancellazioni automatiche. Prima di concludere, l'apply verifica policy e
relazioni di accesso, esegue `doctor` e confronta i permessi effettivi restituiti
da `/permissions/me` con la matrice autorizzata. La specifica completa, inclusi i
campi per ogni azione, è in `references/pubblicazione-sito.md`.

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

### Preflight e modalità incrementale

Il percorso normale passa dal wrapper incrementale:

```bash
python3 editing-portfolio-publisher/scripts/pipeline_incrementale.py \
  preflight /percorso/fotografie
```

Se è prevista la pubblicazione, lo stesso preflight controlla anche profilo,
credenziali remote e schema, in sola lettura:

```bash
python3 editing-portfolio-publisher/scripts/pipeline_incrementale.py \
  preflight /percorso/fotografie \
  --profile ~/.config/editing-portfolio-publisher/sites/mio-sito.json \
  --doctor-site
```

La prima `build --confirm` calcola metriche, miniature e griglia una volta. Dopo
che `analisi.json` riunisce titolo, sequenza, testi, luoghi, coordinate, gallerie
e proposta di pubblicazione, `approve` produce un hash unico da far approvare
all'utente. Una seconda `build --confirm` genera soltanto gli elaborati scaduti.
Gli hash sono SHA-256 dei contenuti; `--rehash` forza la rilettura completa.

Il grafo è a campi: un cambio del colophon invalida soltanto il dummy, un cambio
del blocco di pubblicazione soltanto il piano Directus. Una modifica agli originali
invalida ingestione e approvazione editoriale. La procedura completa è in
`references/flusso-incrementale.md`.

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
| `dummy.qa.json` | pagine, sezioni, overflow e sole pagine cambiate da ricontrollare |
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
  -o /percorso/_analisi/dummy.pdf \
  --qa-strict
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
- elenco puntato dell’attrezzatura ricavato da `metriche.json`, raggruppato per
  copertura EXIF, corpi macchina, obiettivi e focali;
- conteggio delle tavole per ogni corpo, ottica e focale presente negli EXIF;
- colophon distinto in sezioni tematiche per progetto, edizione, specifiche
  tecniche, fonti e limiti, senza ripetere l’elenco dell’attrezzatura.

L’attrezzatura non viene dedotta visivamente. Se gli EXIF sono assenti, il PDF
dichiara che il dato non è determinabile.

Il dummy serve a giudicare sequenza, respiro e relazione fra testo e immagini. Le
miniature non sono adatte alla stampa definitiva.

Ogni generazione scrive `dummy.qa.json`. Alla prima revisione si controlla tutto
il PDF; nelle successive si aprono solo le `changed_pdf_pages`, purché
`qa_ok=true`. Il manifest distingue le pagine del file dagli equivalenti fogli
fisici del libro: ogni pagina PDF rappresenta uno spread e vale due pagine fisiche.

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

### Provision

Preflight locale, senza SSH né mutazioni:

```bash
node editing-portfolio-publisher/scripts/publish_directus.mjs provision \
  --profile ~/.config/editing-portfolio-publisher/sites/mio-portfolio.json \
  --admin-env /percorso/remoto/directus/.env \
  --service-email portfolio-publisher@tuodominio.it
```

Stampa il documento e `authorization_hash`. Dopo l'approvazione esplicita di
quello specifico hash, applicazione:

```bash
node editing-portfolio-publisher/scripts/publish_directus.mjs provision \
  --profile ~/.config/editing-portfolio-publisher/sites/mio-portfolio.json \
  --admin-env /percorso/remoto/directus/.env \
  --service-email portfolio-publisher@tuodominio.it \
  --confirm \
  --authorization-hash HASH_APPROVATO
```

Applica la matrice minima, aggiorna il journal recuperabile e conclude con
`doctor`, audit della policy/access e `/permissions/me`.

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
python3 editing-portfolio-publisher/scripts/verifica_integrita.py
python3 -m unittest discover -s tests -p 'test_*.py'
node --test tests/*.test.mjs
./build-skill.sh && git diff --quiet || echo "pacchetto e sorgenti divergono"
```

Gli stessi comandi girano in CI su ogni push, in `.github/workflows/ci.yml`.
L’ultimo è il più importante: fallisce se il pacchetto committato non corrisponde
ai sorgenti committati.

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
- rifiuto dei domini email riservati prima di SSH;
- legame del dominio email con l'hostname CMS;
- preflight senza SSH e apply vincolato a `authorization_hash`;
- verifica del file amministrativo `600`, non symlink, e del `PUBLIC_URL`;
- confinamento e binding del token sotto la configurazione dell'utente remoto;
- presenza di `directus_fields/read` nella matrice di provisioning;
- assenza di `delete`, wildcard, accesso admin o app nella policy tecnica;
- audit esatto di policy/access, `/permissions/me` e ripresa dal journal;
- impronte SHA-256, invalidazione per campo e approvazione editoriale hashata;
- isolamento delle modifiche a colophon e piano di pubblicazione;
- manifest QA del dummy, pagine cambiate e controlli overflow;
- estrazione dell’attrezzatura EXIF dalle sole tavole selezionate;
- scansione anti-segreti del repository;
- precisione geografica: `exact` solo da EXIF o su dichiarazione esplicita;
- ambito dell’approvazione: vincola la pubblicazione, non gli elaborati locali;
- foglio Excel nel grafo delle dipendenze solo quando `openpyxl` può produrlo;
- manifest di integrità completo, e rilevamento di file troncati o modificati;
- potatura della cache, forma di `analisi.json`, redazione dell’output di doctor;
- il token tecnico certifica il proprio id e nient’altro, come fa Directus davvero;
- `/server/health` letto senza pretendere l’incapsulamento in `data`;
- accenti scritti con l’apostrofo: avviso nei testi di lavoro, errore in quelli
  destinati al sito, nomi propri compresi.

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
non vuoto, percorso reale sotto `$HOME/.config/editing-portfolio-publisher/`,
binding a profilo/CMS/utente/policy e permessi della policy Directus.

**Il preflight stampa un nuovo `authorization_hash`.** È cambiato almeno uno fra
profilo, CMS, email, percorso amministrativo, mapping o matrice dei permessi. Non
riutilizzare la vecchia approvazione: sottoponi il nuovo documento all'utente.

**L'apply rifiuta `--admin-env`.** Il percorso remoto deve essere assoluto, file
regolare non symlink, con permessi esatti `600`; il `PUBLIC_URL` contenuto deve
coincidere con `cms_url` dopo la stessa canonicalizzazione.

**Il provisioning si interrompe dopo una mutazione.** Conserva il journal e gli ID
riportati. Riesegui gli stessi argomenti con lo stesso hash per riprendere; non
cancellare record e non ruotare manualmente il token.

**`doctor` restituisce `403` su `/fields/...`.** Alla policy tecnica manca
`directus_fields/read`. Riesegui il provisioning autorizzato: aggiunge soltanto il
permesso mancante e riutilizza il token valido.

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

## 18. Rilascio

Chi modifica la skill esegue, dalla radice del repository:

```bash
./build-skill.sh
```

Lo script fa quattro cose nell’ordine: calcola l’impronta del contenuto e
incrementa la versione **solo se qualcosa è cambiato davvero**, riscrive la riga di
versione dentro `SKILL.md`, rigenera `references/integrita.json` con byte e SHA-256
di ogni file (`SKILL.md` compreso), crea il pacchetto `.skill` e infine rilancia
`verifica_integrita.py` come postcondizione. `VERSIONE` viene scritto solo dopo che
il pacchetto esiste, così un’interruzione a metà non lascia i sorgenti a dichiarare
una versione mai impacchettata.

Il pacchetto è **riproducibile**: viene costruito da una copia con le date dei
file normalizzate, quindi lo stesso contenuto produce sempre gli stessi byte,
anche su un checkout appena fatto dove le date sono tutte nuove. È la proprietà
su cui si appoggia l’ultimo controllo della CI, che rigenera il pacchetto e
fallisce se non coincide con quello committato: senza, il confronto segnalerebbe
una differenza a ogni esecuzione.

Poi si committa **sia** i sorgenti **sia** il pacchetto:

```bash
git add -A && git commit -m "..."
```

Il push resta un’azione separata ed esplicita.

**Passo che si dimentica:** installare o aggiornare la cartella
`editing-portfolio-publisher` nel proprio ambiente skill. Finché non lo fai, le
sessioni continuano a usare la versione precedente, e il repository aggiornato non
serve a niente. Da quando esiste `verifica_integrita.py` te ne accorgi comunque:
F0 confronta la copia installata con il proprio manifest, non con il repository,
quindi una copia vecchia ma coerente passa il controllo. Il modo per accorgersene è
confrontare il numero di versione che la skill dichiara con quello in `VERSIONE`.
