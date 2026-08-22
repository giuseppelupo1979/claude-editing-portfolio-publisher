# Pubblicazione su un portfolio Directus via SSH

Leggi questa reference soltanto quando, dopo l'edit, l'utente vuole preparare,
caricare o mettere online una selezione. Il giudizio editoriale viene prima del
trasporto tecnico: una cartella non diventa automaticamente una galleria.

## Confine operativo

La pubblicazione ha quattro fasi e due approvazioni:

1. `doctor`, sola lettura: controlla profilo JSON, chiave SSH, helper remoto,
   token remoto e schema Directus;
2. `plan`, sola lettura: confronta la proposta con gallerie, foto e file esistenti;
3. `stage`, prima mutazione: richiede una proposta approvata e crea solo bozze;
4. `release`, messa online: richiede una seconda conferma, pubblica, ricostruisce
   il sito e verifica gli URL.

Un consenso all'analisi non autorizza `stage`. Un consenso allo staging non
autorizza `release`. L'utente deve chiedere chiaramente la messa online.

## Profilo privato

Il profilo vive fuori dal repository, di norma in:

```text
~/.config/editing-portfolio-publisher/sites/<nome>.json
```

Crealo partendo da `site-profile.example.json` e imposta permessi `600`. Il JSON
può contenere host, porta, utente SSH, percorsi, collezioni e nomi dei campi. Non
può contenere password, token, chiavi private o il contenuto di file sensibili.

`ssh.identity_file` indica il percorso assoluto della chiave privata. Il token
Directus vive invece sul VPS nel percorso `directus.token_file`, leggibile solo
dall'utente remoto. Il fork pubblico non deve conoscere il token.

Prima di ogni uso esegui:

```bash
node scripts/publish_directus.mjs doctor --profile /percorso/profilo.json
```

## Helper remoto

La pubblicazione usa due processi distinti:

- il client locale apre SSH, trasferisce piano e fotografie, richiama l'helper e
  verifica il sito pubblico;
- `scripts/remote_directus.mjs`, installato sul VPS, legge il token locale e usa
  esclusivamente le API Directus `/files`, `/items/photos` e
  `/items/galleries`.

Non accedere direttamente al database. Il token deve appartenere a un utente
tecnico senza permessi di cancellazione e con accesso limitato alle collezioni e
ai file necessari.

## Decisione galleria

Ogni nucleo editoriale ha una sola galleria di destinazione. Tutte le foto della
sequenza puntano allo stesso ID galleria. Usa una galleria esistente se rafforzano
un nucleo già leggibile; creane una nuova soltanto se almeno 8-12 immagini
condividono una tesi autonoma.

Una nuova galleria richiede slug stabile, titolo e descrizione nelle lingue del
sito, cover, ordine, stato bozza e un motivo per cui una galleria esistente non
basta. Due o tre fotografie non giustificano una nuova galleria, salvo richiesta
esplicita e stato di bozza.

## Contratto `publication-plan.json`

Il piano viene generato dal blocco `pubblicazione` di `analisi.json` con
`genera_payload_pubblicazione.py`. Contiene:

- `profile_id` e `source_dir`;
- una galleria con `action` uguale a `create` o `existing`;
- fotografie ordinate con file, titoli, alt text, luogo e coordinate certe;
- il blocco `approval`, inizialmente con `approved=false`.

Il contratto corrente usa `plan_version=2`; la geolocalizzazione obbligatoria è la
differenza rispetto alla versione 1.

Non lasciare segnaposto aperti prima di `stage`. Camera, data e coordinate vengono
dagli EXIF quando esistono, mai dalla memoria.

## Geolocalizzazione e Mappa

La pagina Mappa richiede `lat` e `lng` su ogni record `photos`; `place` è
l'etichetta leggibile mostrata nel popup. Il generatore risolve i valori in questo
ordine:

1. metadati espliciti della fotografia nel blocco `pubblicazione`;
2. valori già confermati nell'elemento corrispondente di `immagini`;
3. coordinate GPS estratte in `metriche.json`;
4. reverse geocoding delle coordinate GPS per ottenere `place`;
5. `pubblicazione.location_defaults`, soltanto con `confirmed_by_user=true`.

Il reverse geocoding è automatico solo quando produce un luogo non ambiguo. Salva
`location_source="reverse-geocoded"`; in caso contrario chiedi conferma.

Se tutta la serie è stata scattata nello stesso luogo e non ha GPS, chiedi
all'utente una conferma unica. Registra un punto cittadino o di quartiere come
`precision="approximate"`; usa `exact` solo per coordinate EXIF o fornite come
posizione effettiva. Se una foto ha un luogo diverso, valorizzala singolarmente.

Se `place`, `lat` o `lng` restano mancanti, `genera_payload_pubblicazione.py` deve
fallire e indicare i file incompleti. Non aggirare il controllo modificando a mano
il piano: anche il validatore di `stage` rifiuta coordinate assenti.

## Duplicati e idempotenza

`plan` confronta slug, nomi file, titoli e, quando il modello dati lo permette,
SHA-256. Se trova un possibile duplicato si ferma prima dell'upload.

`stage` crea prima la galleria in bozza, poi carica un file alla volta e salva nel
manifest l'ID Directus subito dopo ogni operazione. Una nuova esecuzione riprende
dal manifest. Non creare una seconda galleria e non ricaricare file già registrati.

Il manifest può contenere percorsi, hash e ID Directus. Non deve contenere token,
header HTTP, output completi di SSH o contenuti della chiave privata.

## Staging

Dopo l'approvazione editoriale:

```bash
node scripts/publish_directus.mjs stage \
  --profile /percorso/profilo.json \
  --plan /percorso/publication-plan.json \
  --confirm
```

Lo staging imposta `published=false` su galleria e fotografie. Non esegue rebuild.
Se un dato importante è incerto, fermati qui e sottoponi le bozze all'utente.

## Release e verifica

Dopo la conferma esplicita di messa online:

```bash
node scripts/publish_directus.mjs release \
  --profile /percorso/profilo.json \
  --manifest /percorso/publication-manifest.json \
  --confirm
```

La release pubblica prima le foto e poi la galleria, esegue il comando di rebuild
configurato e verifica tutte le route dichiarate nel profilo. Riporta conteggi e
URL. Se fallisce dopo una mutazione, non cancellare e non correggere alla cieca:
salva lo stato parziale nel manifest e riferisci gli ID creati.

## Testi e campi

I nomi canonici del piano vengono tradotti nei campi reali tramite
`directus.fields.photo` e `directus.fields.gallery`. Un valore `null` nella mappa
disabilita quel campo.

Titoli e descrizioni possono avere un registro editoriale. Gli alt text no:
descrivono cosa si vede, non attribuiscono emozioni e includono il luogo solo se
certo. `featured=true` si usa per la cover o per immagini che reggono davvero in
home; `portrait=true` solo quando il volto o la persona sono il soggetto leggibile.
