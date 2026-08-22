# Pubblicazione su un portfolio Directus via SSH

Leggi questa reference soltanto quando, dopo l'edit, l'utente vuole preparare,
caricare o mettere online una selezione. Il giudizio editoriale viene prima del
trasporto tecnico: una cartella non diventa automaticamente una galleria.

Quando il lavoro parte da una cartella, esegui il controllo tecnico nello stesso
preflight editoriale:

```bash
python3 scripts/pipeline_incrementale.py preflight CARTELLA \
  --profile /percorso/profilo.json --doctor-site
```

Il wrapper controlla inventario, artefatti, proposta, geolocalizzazioni e doctor
prima di generare i deliverable. La procedura e il grafo delle dipendenze sono in
`flusso-incrementale.md`. Questo non sostituisce l'autorizzazione separata del
provisioning né quelle di stage e release.

## Confine operativo

Il provisioning dell'utente tecnico è un prerequisito una tantum, separato dalla
pubblicazione. Richiede un'autorizzazione esplicita propria. Dopo il provisioning,
la pubblicazione ha quattro fasi e due approvazioni:

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
Directus vive invece sul VPS nel percorso `directus.token_file`, confinato sotto
`$HOME/.config/editing-portfolio-publisher/` e leggibile solo dall'utente remoto.
Un binding separato lo associa a profilo, CMS, utente tecnico e policy. Il fork
pubblico non deve conoscere né token né binding reali.

## Provisioning una tantum

Se il token remoto manca, non improvvisare un utente o una policy con uno script
temporaneo. Il provisioning ha due passaggi distinti: preflight locale e apply
autorizzato. Dopo aver installato l'helper, esegui il comando senza `--confirm`:

```bash
node scripts/publish_directus.mjs provision \
  --profile /percorso/profilo.json \
  --admin-env /percorso/remoto/directus/.env \
  --service-email portfolio-publisher@tuodominio.it
```

Questo è un preflight puro: valida opzioni e profilo, costruisce l'identità tecnica,
risolve la matrice esatta `collection/action/fields` e stampa il documento di
autorizzazione con `authorization_hash`. Non apre SSH e non muta né il VPS né
Directus. Mostra all'utente il documento intero, compresi CMS, email, file remoti,
identità, permessi e divieti, e chiedi un'approvazione separata riferita a quello
specifico hash. L'approvazione editoriale della galleria non vale come approvazione
del provisioning.

Solo dopo l'approvazione ripeti gli stessi argomenti, aggiungendo entrambi i
vincoli:

```bash
node scripts/publish_directus.mjs provision \
  --profile /percorso/profilo.json \
  --admin-env /percorso/remoto/directus/.env \
  --service-email portfolio-publisher@tuodominio.it \
  --confirm \
  --authorization-hash HASH_APPROVATO
```

L'apply ricalcola il preflight prima di SSH e si ferma se l'hash non coincide.
Qualsiasi modifica a profilo, CMS, email, percorso amministrativo, mapping o
matrice invalida quindi l'autorizzazione e richiede un nuovo preflight.

### Vincoli dell'identità e dei segreti

- `--service-email` deve avere un dominio DNS reale collegato all'hostname di
  `cms_url`: lo stesso dominio oppure un suo dominio padre sul confine di una
  label. Sono rifiutati indirizzi su IP, localhost, TLD riservati e domini di
  esempio, compresi `example.com`, `example.net`, `example.org` ed `example.edu`.
- Ruolo e policy hanno nomi deterministici namespaced per `profile.id` e CMS. Non
  riusare l'identità tecnica di un altro profilo o di un altro Directus.
- `--admin-env` è un percorso assoluto sul VPS. All'apply deve risolversi in un
  file regolare, non symlink, con permessi esatti `600`. Le credenziali
  amministrative vengono lette soltanto lì e non entrano in argomenti, profilo,
  hash, log, journal o deliverable.
- Il `PUBLIC_URL` dell'ambiente amministrativo è l'ancoraggio di fiducia: il suo
  valore canonico deve coincidere esattamente con `cms_url`, inclusi schema,
  hostname, porta ed eventuale base path. Alias, redirect e corrispondenze per
  suffisso non bastano.
- `directus.token_file` deve risolversi sotto
  `$HOME/.config/editing-portfolio-publisher/` dell'utente SSH. Directory `700`,
  token `600`, file regolari, proprietario corretto e nessun symlink. Il binding
  accanto al token lega il segreto a `profile.id`, CMS canonico, utente tecnico e
  policy; `doctor` lo verifica prima di riusare il token.

Lo schema JSON può verificare forma, identificatori e presenza del segmento
`.config/editing-portfolio-publisher`, ma non conosce `$HOME`, proprietario,
permessi o `realpath`: questi vincoli restano controlli runtime obbligatori.

### Matrice autorizzata

La matrice viene risolta sui nomi Directus reali e inclusa nel documento hashato.
`mapped(...)` significa il nome configurato in `directus.fields`; un mapping
opzionale a `null` viene omesso. Gli undici mapping fotografici essenziali e gli
otto mapping galleria essenziali non possono essere `null`.

| Collezione | Azione | Campi autorizzati |
|---|---|---|
| fotografie configurata | `read` | `id` e tutti i mapping foto non `null` |
| fotografie configurata | `create` | tutti i mapping foto non `null`; validazione e preset impongono `published=false` |
| fotografie configurata | `update` | `mapped(published)` |
| gallerie configurata | `read` | `id` e tutti i mapping galleria non `null` |
| gallerie configurata | `create` | tutti i mapping galleria non `null`; validazione e preset impongono `published=false` |
| gallerie configurata | `update` | `mapped(cover,published)` |
| `directus_files` | `read` | `id`, `filename_download`, `filesize` |
| `directus_files` | `create` | whitelist `DIRECTUS_FILE_CREATE_FIELDS` riportata sotto |
| `directus_fields` | `read` | `collection`, `field`, con filtro `_in` sulle sole due collezioni applicative configurate |

`DIRECTUS_FILE_CREATE_FIELDS` è una lista chiusa di 28 campi: `charset`, `created_on`,
`description`, `duration`, `embed`, `filename_disk`, `filename_download`,
`filesize`, `focal_point_divider`, `focal_point_x`, `focal_point_y`, `folder`,
`height`, `id`, `location`, `metadata`, `modified_by`, `modified_on`, `storage`,
`storage_divider`, `tags`, `title`, `tus_data`, `tus_id`, `type`, `uploaded_by`,
`uploaded_on`, `width`. Il preflight la mostra per esteso e l'hash la copre.

Non sono ammessi wildcard di collezione, azioni `delete`, regole di campo più
ampie del documento approvato, `admin_access` o `app_access`. I mapping opzionali
compaiono solo se valorizzati nel profilo; non autorizzarli per convenienza quando
sono `null`.

### Audit, journal e postcondizione

Prima delle mutazioni l'apply verifica per nome e ID tutte le identità omonime,
policy e relazioni di accesso già presenti. Deve esistere una sola catena attesa
utente, ruolo, policy; policy con accesso amministrativo o app, relazioni extra,
permessi wildcard, `delete`, filtri/preset inattesi o campi più larghi causano uno
stop. La riconciliazione non deve mascherare una policy sovrapermissiva.

Ogni mutazione viene registrata in un journal atomico e recuperabile, privo di
segreti: `authorization_hash`, ID creati o riusati, operazioni eseguite e
postcondizioni. In caso di interruzione non cancellare automaticamente record né
ruotare alla cieca il token. Riavvia con lo stesso hash per riprendere in modo
idempotente, oppure usa il journal per una riconciliazione manuale verificabile.

Il token viene scritto prima in un file temporaneo `600`, verificato contro
l'identità tecnica e rinominato atomicamente; subito dopo viene scritto il binding.
L'apply termina con `doctor` e con un audit di `/permissions/me`: livelli di
accesso e campi richiesti devono coincidere con la matrice, qualsiasi `delete`
effettivo causa uno stop e gli accessi extra non distruttivi vengono riportati per
l'audit. L'audit amministrativo del provisioning garantisce inoltre che il ruolo
gestito non abbia altre policy. Non dichiarare completato il provisioning se
journal, binding, audit o postcondizione falliscono.

Prima di ogni uso esegui:

```bash
node scripts/publish_directus.mjs doctor --profile /percorso/profilo.json
```

## Helper remoto

La pubblicazione usa due processi distinti:

- il client locale apre SSH, trasferisce piano e fotografie, richiama l'helper e
  verifica il sito pubblico;
- `scripts/remote_directus.mjs`, installato sul VPS, legge il token locale e usa
  le API Directus `/server/health`, `/permissions/me`, `/fields/{collection}`,
  `/files`, `/items/photos` e `/items/galleries`. Il comando di provisioning usa
  inoltre gli endpoint amministrativi solo durante il bootstrap autorizzato.

Il payload inviato all’helper contiene soltanto il profilo canonico necessario sul
VPS, senza la sezione `ssh`. Il client valida il profilo locale completo; l’helper
usa il validatore remoto dedicato e non deve richiedere host, utente o chiave SSH.

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
