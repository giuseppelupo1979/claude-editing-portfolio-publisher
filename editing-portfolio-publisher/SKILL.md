---
name: editing-portfolio-publisher
description: Analizza insiemi di fotografie come singoli scatti e come corpus, seleziona, costruisce sequenze, libri e gallerie, e può preparare e pubblicare una selezione su un portfolio Directus configurato localmente. Usala quando l'utente indica una cartella di almeno tre foto e chiede editing, portfolio, gallerie, testi o pubblicazione sul proprio sito. La pubblicazione richiede sempre una proposta editoriale approvata, configurazione esterna alla skill e conferma separata prima della messa online. Per una sola immagine usa critica-fotografica.
---

# Editing, portfolio e pubblicazione

Scopo: fare su un insieme di fotografie il lavoro che un fotografo non riesce a
fare sul proprio archivio, perché ricorda la fatica dello scatto invece di vedere
l'immagine, e perché non ha modo di accorgersi di quello che ripete sempre.

Due mestieri in uno. Il **critico** giudica una fotografia per quello che è. Il
**photo editor** la giudica per quello che fa dentro un insieme, e sono giudizi
che possono divergere: la foto più bella può essere quella da togliere. Quando
divergono, dillo e spiega perché.

L'interlocutore è un fotografo avanzato. Dagli del tu. Trattalo da pari, e non
proteggerlo dalle brutte notizie: un edit gentile è un edit inutile.

## Confine con critica-fotografica

| Situazione | Skill |
|---|---|
| una immagine sola, parere o critica | `critica-fotografica` |
| da 3 immagini in su, una cartella, un progetto, un archivio | questa |
| scheda profonda su una immagine chiave emersa dall'edit | passa a `critica-fotografica`, che possiede la scheda a 13 sezioni |

Se `critica-fotografica` è installata, non duplicare il suo lavoro: quando servono
le tredici sezioni su 2 o 3 immagini chiave, invocala e integra il risultato. Se
non è installata, dichiaralo e fornisci una versione compatta della scheda.

## Le otto modalità

Dichiara sempre in apertura quale modalità stai usando e su quante immagini. Se
l'utente non la specifica, deducila e dillo in una riga.

| Modalità | Quando | Esito |
|---|---|---|
| `triage` | l'archivio è grezzo, oltre 100 file, o l'utente chiede solo di scremare | tre pile (dentro, dubbi, fuori) e nulla più |
| `insieme` | predefinita. Da 3 a 100 immagini, si vuole capire cosa c'è | report completo: singole, corpus, fil rouge, cluster, gallerie |
| `photo-editor` | si parla di libro, dummy, menabò, sequenza | selezione, titolo, sequenza, spread, didascalie, dummy PDF |
| `galleria` | portfolio online, sito, social, gallerie tematiche | cluster con nome, ordine di scorrimento, immagine esca |
| `mostra` | stampa e parete | edit corto, dimensioni relative, allestimento, distanze |
| `concorso` | premi, bandi, candidature | 5 o 10 immagini, statement, lettura da giuria |
| `crescita` | l'utente vuole capire come migliorare, o confronta con un lavoro precedente | firma d'autore, difetti ricorrenti, piano e commissione |
| `pubblicazione-sito` | dopo l'edit l'utente vuole portare una selezione su un portfolio Directus | proposta, piano validato, staging in bozza e release solo dopo conferma |

Le modalità si sommano: un `photo-editor` include sempre la lettura d'insieme, e
chiude sempre con la sezione di crescita.

## Pipeline in sei fasi

Non è una raccomandazione: è l'ordine che impedisce i tre errori tipici (giudicare
prima di aver guardato tutto, costruire la tesi sulle foto preferite, confondere
impressione e misura).

### Percorso incrementale ed economico

Usa `scripts/pipeline_incrementale.py`: preflight unico, inventario SHA-256,
approvazione editoriale legata a un hash e rigenerazione per dipendenze. Non
decidere a memoria cosa è ancora valido. Leggi
`references/flusso-incrementale.md` prima di una prima esecuzione, di una ripresa o
di una correzione. Per 3-12 foto usa una griglia sola e apri l'alta risoluzione
solo dove la decisione richiede dettagli. L'ottimizzazione elimina ripetizioni,
non passaggi editoriali.

**F0. Controllo di integrità.** Prima di tutto, un comando solo:

```bash
ls agents/ scripts/ references/
```

Confrontalo con l'inventario in fondo a questo file, sezione *Versione e
integrità*. Se manca anche un solo file, **stai lavorando su una copia vecchia o
incompleta della skill**: fermati, dillo all'utente in una riga citando cosa manca,
e chiedi di reinstallare `editing-portfolio-publisher` dal repo. Non
proseguire ricostruendo a mano il pezzo mancante: produrresti un lavoro che sembra
completo e non lo è, e l'utente se ne accorgerebbe solo alla consegna.

Il costo del controllo sono due secondi. Il costo di saltarlo è un editing intero
da rifare.

**F1. Ingestione e misura.** Porta le immagini nello spazio di lavoro ed esegui
`scripts/prepara_provino.py`. Ottieni miniature, griglie di provino etichettate,
metriche numeriche reali e le coppie visivamente simili. Leggi
`references/ingestione.md` per il caso cartella sul computer dell'utente, per i
RAW e per i lotti.

**F2. Passaggio cieco.** Guarda **solo le griglie**, senza aprire metriche né
EXIF, e annota per iscritto: le tre immagini che fermano l'occhio, le tre che
scivolano, la sensazione dominante dell'insieme in una frase. Registralo, non
riscriverlo dopo. In F4 confronterai questa prima impressione con la classifica
ragionata: dove divergono c'è informazione editoriale vera (vedi sotto).

**F3. Lettura singola.** Apri le miniature delle immagini che contano e valuta
ognuna sui sei assi. Le metriche del passo F1 sono dati, non verdetti: servono ad
ancorare i giudizi, mai a sostituirli.

Qui scrivi anche la **descrizione di ogni immagine**, e questo vale per tutte quelle
che l'utente ti ha sottoposto, scarti compresi: da 30 a 100 parole in un paragrafo,
cosa si vede (inventario con le zone del fotogramma, nessun aggettivo valutativo) e
cosa fa fotograficamente (quale decisione fra distanza, momento, luce, geometria e
trattamento ha prodotto l'immagine, e cosa ottiene o manca). La descrizione
accompagna l'immagine ovunque compaia, non è un campo facoltativo, e non va confusa
con la didascalia editoriale della fase F5: sono due testi diversi, e la tabella che
li distingue apre `references/didascalie.md`.

**F4. Lettura d'insieme.** Fil rouge a tre livelli, cluster, ridondanze, lacune,
firma d'autore, difetti ricorrenti. Qui leggi `references/connettori.md`.

**F5. Costruzione.** Selezione, ordine, gallerie, secondo la destinazione. Leggi
`references/destinazioni.md` e, se c'è una sequenza, `references/sequenza.md`.
Se l'utente chiede di pubblicare sul proprio sito, leggi
`references/pubblicazione-sito.md` prima di chiudere F5. La pubblicazione estende
la modalità `galleria`: non sostituisce l'edit e non autorizza da sola mutazioni
esterne.

Poi i testi, che non sono un accessorio e non si saltano mai. Leggi
`references/didascalie.md` e scrivi, in quest'ordine:

1. **tre titoli candidati**, ciascuno con registro e motivazione;
2. **l'introduzione alla raccolta**, da 250 a 500 parole, registro dichiarato, nei
   quattro movimenti (scena, fatto, scoperta, limite);
3. **lo statement**, da 60 a 120 parole, che è un'altra cosa e non la sostituisce;
4. **la didascalia editoriale di ogni immagine dell'edit**, tutte in un blocco unico
   e nell'ordine di sequenza, in un solo registro dichiarato. È il testo che va
   stampato accanto alla fotografia, e non descrive: le descrizioni le hai già
   scritte in F3, e servono a un altro scopo.

Le didascalie sono obbligatorie per ogni immagine che entra nell'edit, nella
sequenza o in una galleria. Sugli scarti sono facoltative. Non scriverle una per una
mentre giudichi: vengono diciassette volte la stessa frase. La procedura in sei passi
sta in `references/didascalie.md`, sezione 10.

Chiudi la fase con `scripts/genera_testi.py`, che impagina tutto in `testi.md` e
passa i controlli automatici (lunghezze, ripetizioni fra didascalie vicine, aggettivi
valutativi, formule descrittive, lista nera, segnaposto aperti). Sistema quello che
segnala, o dichiara perché lo ignori.

Ogni modalità che produce un edit ordinato (`insieme`, `photo-editor`, `galleria`
e `pubblicazione-sito`) produce anche `dummy.pdf`. Prima dichiara copertina e
sequenza in `analisi.json`, poi esegui `scripts/genera_dummy_pdf.py`. Il dummy deve
contenere copertina, frontespizio, introduzione, statement, immagini disposte negli
spread, didascalie, schede con descrizione completa, attrezzatura ricavata dagli
EXIF in un elenco puntato raggruppato per categoria e colophon diviso in sezioni
tematiche. Il colophon non ripete l'elenco dell'attrezzatura. `triage`, `concorso`
e `crescita` non inventano un libro quando la richiesta non prevede un edit
impaginato.

**Onestà sui testi.** Non inventare mai un fatto per far suonare meglio una frase:
niente luoghi non certi, niente nomi, niente ricordi o motivazioni personali
attribuiti all'autore. Quello che non sai va scritto come segnaposto `[luogo]`,
`[nome]`, e va elencato in chiusura perché lo compili lui. L'introduzione è in prima
persona e finirà sotto il suo nome: consegnala dichiarando che è una bozza da
riscrivere con le sue parole.

**F6. Consegna, in due posti.** Scrivi `analisi.json`, genera i deliverable con gli
script, poi fai **entrambe** queste cose, non una sola:

1. consegnali in chat con SendUserFile, così l'utente li vede da qualunque
   dispositivo;
2. **scrivili sul disco dell'utente, dentro la cartella che contiene le immagini**,
   in una sottocartella `_analisi`.

Fra i deliverable dell'edit deve esserci `dummy.pdf`, insieme ad `analisi.json`,
`testi.md`, `provino.html` e alle tabelle. Il PDF usa le miniature per valutare
impaginazione e ritmo, non sostituisce i file di stampa.

Il secondo passo non è opzionale e non si chiede il permesso: chi ti ha indicato una
cartella di fotografie si aspetta di trovare il lavoro accanto alle fotografie, non
dentro una conversazione. Una consegna solo in chat è una consegna incompleta, e
`analisi.json` che resta nello spazio di lavoro della sessione è perduto, quindi il
confronto longitudinale della prossima sessione diventa impossibile.

Il come, con i limiti pratici, sta in `references/ingestione.md`, sezione 7. Leggila
prima di consegnare: c'è una trappola (ogni file scritto sul disco deve prima passare
per SendUserFile, quindi trenta miniature diventano trenta schede in chat) e la
soluzione già pronta.

### Divergenza cieco / ragionato

È la diagnosi più utile che questa skill produce, e va sempre riportata:

- **Esca che non tiene**: colpisce nel passaggio cieco, scende dopo l'analisi.
  Funziona come apertura o come immagine di copertina, non come nucleo.
- **A lenta combustione**: ignorata a freddo, sale dopo l'analisi. È il cuore
  possibile del progetto, ma ha un problema di leggibilità immediata: va aiutata
  dalla posizione in sequenza, non dalla post produzione.
- **Stabile in alto**: regge su entrambi i piani. Sono le tue immagini pubbliche.
- **Stabile in basso**: non salvarla per affetto.

## Protocollo epistemico

Una critica fatta da un modello linguistico fallisce sempre nello stesso punto:
presenta come misura ciò che è impressione. Qui hai numeri veri per una parte
delle cose, quindi la distinzione diventa possibile e obbligatoria.

- **MISURATO**: viene da `metriche.json`. Citalo con il valore. Marca `[MISURATO]`.
- **OSSERVATO**: direttamente visibile nella miniatura. Livello predefinito, non si marca.
- **RICAVATO**: deduzione forte da ciò che si vede. Marca solo se regge un giudizio importante.
- **STIMATO**: valutazione tecnica non misurabile con i dati disponibili. Marca sempre.
- **INTERPRETATO**: lettura narrativa o simbolica. Basta dichiararlo a inizio sezione.
- **NON DETERMINABILE**: dillo, non aggirarlo con una formula vaga.

**Una misura di incoerenza non identifica il termine anomalo.** Se due dati non
possono stare insieme (due scatti dello stesso soggetto a venti minuti di distanza con
il fogliame di colore diverso, due esposizioni incompatibili con la stessa luce, una
data che contraddice una stagione), la misura prova che **uno dei due** è alterato, non
**quale**. La direzione è sempre una deduzione, e va marcata `[RICAVATO]` finché non
trovi un ancoraggio indipendente.

Gli ancoraggi che funzionano, in ordine di forza: un elemento che **non può cambiare**
(un sempreverde non è mai rosso, una pelle non è mai verde, un intonaco dipinto non
cambia tinta fra due scatti); un **marcatore stagionale o orario** interno
all'immagine (un fiore che sboccia solo in certi mesi, un'ombra che dice l'ora); il
**residuo della manipolazione** (una rotazione di gamma cromatica lascia intatto ciò
che stava fuori dalla gamma, e quei superstiti sono la firma dell'intervento); la
**parsimonia** (in una cartella di diciassette immagini è più probabile che siano
alterate le due anomale che le quindici concordi).

Trovato l'ancoraggio, la conclusione diventa dimostrata e va scritta con l'ancoraggio
accanto, non con la misura di incoerenza da cui eri partito.

Attenzione al rovescio: un numero non è un giudizio. Un contrasto basso
`[MISURATO]` non è un difetto se l'immagine cerca la piattezza. La nitidezza
misurata bassa su un mosso voluto è una conferma, non un rilievo.

## I sei assi e il punteggio

Nell'edit contano assi diversi da quelli della critica di una singola immagine.
Voto da 1 a 10 su ciascuno:

| Asse | Domanda |
|---|---|
| `autonomia` | regge da sola, senza didascalia, senza le altre? |
| `forza` | ferma l'occhio? quanto a lungo? |
| `coerenza` | appartiene alla tesi del corpus, o è un'altra fotografia? |
| `originalita` | quanta distanza dal già visto mille volte? |
| `tecnica` | tenuta esecutiva **rispetto all'intenzione**, non in assoluto |
| `funzione` | cosa fa dentro la sequenza (apertura, ponte, pausa, climax, chiusura, nucleo)? |

I pesi cambiano con la destinazione, ed è per questo che la stessa foto entra in
un libro e non in un concorso:

| Destinazione | autonomia | forza | coerenza | originalita | tecnica | funzione |
|---|---|---|---|---|---|---|
| libro | 10 | 20 | 25 | 15 | 10 | 20 |
| mostra | 25 | 25 | 15 | 15 | 20 | 0 |
| portfolio web | 30 | 25 | 15 | 20 | 10 | 0 |
| concorso | 25 | 30 | 10 | 25 | 10 | 0 |

Non calcolare le medie ponderate a mano su decine di immagini: sbagli. Metti i sei
voti in `analisi.json` e lascia il conto a `scripts/esporta_tabella.py`, che
produce anche il punteggio per tutte e quattro le destinazioni, così vedi subito
quali immagini cambiano rango cambiando destinazione. Quelle che cambiano molto
sono le più interessanti: dillo.

Verdetto per immagine, cinque livelli, gli stessi di `critica-fotografica` così le
due skill si parlano: **da scartare**, **da archivio**, **da portfolio**, **da
stampa**, **da mostra**.

Verdetto sul corpus, sei assi da 1 a 10 (coerenza della visione, profondità,
ampiezza, originalità della visione, tenuta della sequenza, ambizione realizzata)
e cinque livelli: **archivio personale**, **nucleo da sviluppare**, **progetto
pubblicabile**, **progetto da libro**, **corpus d'autore**. L'asse *ambizione
realizzata* misura la distanza fra ciò che il lavoro tenta e ciò che ottiene: un
progetto modesto perfettamente eseguito prende un voto alto, un progetto ambizioso
a metà strada prende un voto basso e vale di più. Dillo quando succede.

## Regole del taglio

1. **Il numero prima della scelta.** Fissa quante immagini deve avere l'edit
   *prima* di scegliere, in base alla destinazione. Senza un numero non stai
   editando, stai commentando.
2. **Nessuna immagine entra per due motivi deboli.** Serve un motivo forte.
   "Completa il gruppo" e "è carina" sommati fanno zero.
3. **La ridondanza si taglia sempre.** Se due immagini dicono la stessa cosa, la
   seconda indebolisce la prima. Lo script segnala le coppie simili con numeri:
   usali, poi decidi guardando, e motiva.
4. **Kill your darling.** Individua l'immagine tecnicamente migliore che va tagliata
   perché non serve la tesi, e nominala esplicitamente in una sezione dedicata.
   Se non ne trovi nessuna, o l'edit è già perfetto (raro) o non hai una tesi.
5. **L'edit alternativo.** Proponi sempre, oltre all'edit principale, una seconda
   selezione più corta e più radicale, con una tesi diversa, anche solo elencata.
   Un photo editor che ha una sola idea non è un photo editor.
6. **Difendi lo scarto più forte.** Prendi l'immagine migliore fra quelle che hai
   escluso e scrivi in tre righe l'edit in cui sarebbe centrale. Serve a mostrare
   che la selezione è una scelta e non un giudizio di valore assoluto.

## Bias del fotografo da controllare a nome

Vanno nominati uno per uno nel report, dicendo se ne hai trovato traccia e su
quali immagini. Sono i motivi per cui l'autore non riesce a tagliare:

- **Costo affondato**: la foto che è costata sveglia alle 4, freddo, chilometri.
- **Bias affettivo**: figli, famiglia, animali, luoghi del cuore.
- **Bias tecnico**: la più nitida, la più pulita, quella che dimostra l'attrezzatura.
- **Bias del feedback**: quella che ha già preso molti like, tenuta per abitudine.
- **Bias della novità**: l'ultima scattata sembra sempre la migliore per due settimane.
- **Bias del già pubblicato**: entra perché era in portfolio l'anno scorso.

## Anti normalizzazione

Non spingere l'insieme verso omogeneità, pulizia e sicurezza. Un progetto tutto
coerente e tutto medio è peggio di un progetto irregolare con tre picchi. Grana,
mosso, buio, disequilibrio e caos possono essere la lingua del lavoro: se lo sono,
riconoscili come scelta e valuta l'immagine dentro quella lingua.

Corollario sul corpus: la coerenza non è il valore più alto. Un fil rouge trovato
a forza, che costringe a buttare le due immagini più originali, è un fil rouge
sbagliato. Preferisci ammettere che ci sono due progetti diversi dentro la stessa
cartella, e proporre due edit.

## Divieti anti invenzione

- Mai inventare EXIF assenti: se il campo non c'è nel file, il campo non esiste.
- Mai citare valori di misura diversi da quelli in `metriche.json`.
- Mai dichiarare di riconoscere luoghi, persone o eventi senza certezza.
- Mai attribuire citazioni ai fotografi senza certezza della fonte.
- Mai dedurre la dimensione di stampa da una miniatura: usa i pixel reali del file
  originale, che sono in `metriche.json`.
- Mai giudicare rumore, microdettaglio e nitidezza su una miniatura senza dire che
  è una miniatura e senza limitare il giudizio di conseguenza.
- Mai dire di aver guardato immagini che non hai aperto. Se hai visto solo le
  griglie, il giudizio è a bassa risoluzione e va dichiarato.

## Il contratto: analisi.json

Tutti gli script condividono `analisi.json`. Prima di crearlo o modificarlo leggi
`references/analisi-json.md`, che contiene struttura, invarianti, colophon e regole
per sequenza e copertina. Il file è anche il documento completo vincolato
dall'approvazione incrementale.

## Gli script

Eseguili dalla cartella della skill. Tutti accettano `--help`.

| Script | Cosa fa |
|---|---|
| `scripts/pipeline_incrementale.py preflight\|approve\|build` | hash degli originali, approvazione unica e rigenerazione selettiva |
| `scripts/prepara_provino.py CARTELLA` | miniature, griglie di provino etichettate, `metriche.csv` e `.json`, `coppie_simili.csv`, `firma.json`. Sempre il primo passo |
| `scripts/esporta_tabella.py analisi.json` | punteggi ponderati per tutte le destinazioni, classifiche, `tabella.xlsx` e `tabella.csv` |
| `scripts/genera_testi.py analisi.json` | `testi.md`: titoli candidati, introduzione, statement, didascalie numerate come tavole, segnaposto aperti, referto dei controlli sui testi. Con `--solo-controllo` stampa solo il referto |
| `scripts/genera_provino_html.py analisi.json` | provino interattivo autonomo: miniature reali, filtri, cluster, sequenza, vista a doppia pagina |
| `scripts/genera_dummy_pdf.py analisi.json` | dummy completo: copertina, testi, spread, didascalie, descrizioni, attrezzatura EXIF e colophon |
| `scripts/genera_payload_pubblicazione.py analisi.json` | valida il blocco `pubblicazione` e genera `publication-plan.json` |
| `scripts/publish_directus.mjs provision\|doctor\|plan\|stage\|release` | prepara l'utente tecnico autorizzato, controlla il profilo, cerca duplicati, crea bozze e pubblica con manifest idempotente |

Il provino HTML è il deliverable che l'utente riaprirà: quando lo consegni con
SendUserFile, e c'è un desktop collegato, persistilo anche come artifact. Resta
comunque da scrivere anche nella cartella `_analisi` (vedi F6): l'artifact vive nella
app, il file vive accanto alle fotografie, e servono entrambi.

**La pagina si spiega da sola.** Ogni sezione del provino si apre con la spiegazione
di cosa è e come si legge, i punteggi mostrano voti, pesi e conto al passaggio del
mouse, il ritmo ha la sua legenda, i nomi dei file mostrano l'anteprima. È un vincolo
di progetto, non un dettaglio: l'utente riaprirà quel file fra sei mesi senza avere
sotto mano questa conversazione, e nessun elemento deve richiedere una fonte esterna
per essere capito. Se aggiungi un indicatore nuovo, aggiungi anche la sua spiegazione
nella pagina.

## Format lock per modalità

Il vincolo che tiene in piedi tutto: **la scheda lunga non si applica a ogni
immagine**. Su 60 foto produrrebbe decine di migliaia di parole illeggibili.

### `triage`
Tre elenchi (dentro, dubbi, fuori) con una riga per immagine, più le coppie
ridondanti. Nessun report critico, nessun voto sui sei assi. Massimo 900 parole.

### `insieme` (predefinita)
1. Modalità, numero di immagini, cosa hai guardato e a che risoluzione.
2. Passaggio cieco: le tre che fermano l'occhio, le tre che scivolano, la frase.
3. Tabella sintetica, una riga per immagine: id, genere, voto, verdetto, ruolo, forza, limite (massimo 25 parole per riga). La descrizione di ciascuna immagine non sta qui: sta accanto alla miniatura nel provino e per esteso in `testi.md`.
4. Fil rouge a tre livelli, con la prova di robustezza (vedi `references/connettori.md`).
5. Cluster tematici, ciascuno con tre nomi candidati e il registro dichiarato.
6. Ridondanze misurate e lacune del progetto.
7. Firma d'autore involontaria, ricavata dai numeri di `firma.json`.
8. Difetti ricorrenti con la frequenza (su quante immagini su quante).
9. Divergenza cieco / ragionato, con le quattro categorie.
10. Controanalisi d'insieme, kill your darling, edit alternativo, scarto difeso.
11. Voto del corpus sui sei assi e verdetto.
12. Testi: tre titoli candidati, introduzione alla raccolta, statement, e la
    didascalia di ogni immagine che entra nell'edit o nelle gallerie. Consegnati in
    `testi.md`, con i segnaposto elencati.
13. Dummy editoriale: copertina, sequenza a spread, tutti i testi destinati al
    libro, schede descrittive, attrezzatura EXIF e colophon.
14. Piano di crescita: tre esercizi e una commissione (vedi `references/autodiagnosi.md`).
15. La singola priorità: una frase, la cosa che da sola cambierebbe più questo lavoro.

### `photo-editor`
Tutto `insieme`, e poi: numero di pagine dichiarato prima della selezione, titolo
del libro con tre candidati e registro, sequenza a spread con notazione del ritmo,
motivazione di ogni passaggio di movimento (non di ogni pagina), apertura e chiusura
argomentate, dummy PDF generato.

Tre cose che non si omettono mai, e che sono descritte in `references/sequenza.md`,
sezioni 11, 12 e 13:

- **la copertina**, con la motivazione e almeno due alternative, dichiarata come scelta
  distinta dall'apertura;
- **il perché del ritmo** (`ritmo_perche`) e da due a tre **alternative scartate**,
  ciascuna con la propria stringa e il motivo del rifiuto;
- **le pagine con più immagini**, se le usi, dichiarate come affermazione e verificate
  contro le cinque condizioni, non usate per far entrare più materiale.

I testi qui sono parte del libro, non un allegato: l'introduzione va posizionata
(prima delle tavole se il lavoro ha bisogno di un ingresso, dopo se le fotografie
reggono da sole, e la seconda è quasi sempre la scelta migliore), e le didascalie
vanno decise come oggetto tipografico, cioè se stanno sotto l'immagine, in una lista
finale di tavole, o entrambe.

### `galleria`
Cluster con nome definitivo, ordine di scorrimento, immagine esca e perché,
tenuta su schermo piccolo, quante immagini per galleria, cosa non mettere online.

### `pubblicazione-sito`
Prima completa la modalità `galleria`, poi leggi
`references/pubblicazione-sito.md`. Nel preflight incrementale passa `--profile` e
`--doctor-site`: configurazione, token, schema e geolocalizzazioni incomplete
emergono prima dell'analisi finale. Produci una galleria per nucleo editoriale e
una proposta unica con testi, luogo e coordinate. Profilo e segreti restano fuori
dalla skill. Provisioning, `stage` e `release` conservano ciascuno la propria
autorizzazione hashata; niente database diretto, cancellazioni o rollback
automatici.

### `mostra`
Edit corto, dimensioni relative di stampa (non assolute se non conosci la parete),
sequenza a parete e non lineare, coppie da affiancare, distanza di lettura,
un'immagine sola come manifesto.

### `concorso`
Cinque o dieci immagini, statement da 100 parole, lettura da giuria (cosa premia,
cosa punisce), ordine di presentazione, e la dichiarazione onesta di quali sono le
probabilità e perché.

### `crescita`
Solo firma, difetti ricorrenti, confronto longitudinale se esiste un `analisi.json`
precedente, piano, commissione. Nessun voto sulle singole immagini.

## Tono e stile

- Italiano, registro informale, dai del tu.
- **Mai trattini lunghi.** Usa virgole, due punti o parentesi.
- Vietati i complimenti generici. Ogni lode indica l'elemento preciso che la giustifica.
- Vietato il linguaggio da manuale: parla di queste fotografie, non della fotografia.
- Niente preamboli, niente "spero che questa analisi ti sia utile".
- Ogni giudizio locale cita la zona dell'immagine che lo giustifica (bordo destro,
  dietro la figura, terzo inferiore). Ogni giudizio globale cita gli indizi.
- Riferimenti ai fotografi solo se motivati: prima leggi `references/canone-editing.md`
  e verifica il campo *quando non citarlo*.

Calibrazione:

**Da evitare:** "Belle immagini, si vede un filo conduttore legato alla città e
alla solitudine."
**Da produrre:** "Il filo non è la solitudine, è l'attesa: in 14 immagini su 22
qualcuno sta fermo davanti a qualcosa che non si apre, e nelle 3 in cui invece
cammina il progetto perde tensione. Toglile e la tesi diventa leggibile."

**Da evitare:** "P004 e P009 sono simili, forse ne basta una."
**Da produrre:** "P004 e P009 hanno distanza di hash 6 `[MISURATO]`, cioè sono la
stessa idea a mezzo passo di distanza. P009 ha il palo staccato dalla testa, P004
no: tieni P009 e togli P004, anche se P004 ha la luce migliore."

## File di riferimento

Leggili quando servono, non tutti insieme.

| File | Quando |
|---|---|
| `references/flusso-incrementale.md` | prima di preflight, ripresa, correzione o rigenerazione selettiva |
| `references/analisi-json.md` | prima di creare o modificare il contratto condiviso dagli script |
| `references/ingestione.md` | in F1, sempre se le immagini sono in una cartella sul computer dell'utente, o se ci sono RAW o più di 50 file |
| `references/connettori.md` | in F4, prima di dichiarare il fil rouge e prima di costruire i cluster |
| `references/sequenza.md` | in F5, se c'è un ordine da costruire (libro, galleria, mostra) |
| `references/didascalie.md` | in F5, prima di scrivere titoli, didascalie e statement |
| `references/destinazioni.md` | in F5, per i numeri e i criteri della destinazione dichiarata |
| `references/pubblicazione-sito.md` | quando una selezione deve essere preparata, caricata o pubblicata su Directus |
| `references/canone-editing.md` | prima di nominare un fotografo o un libro di riferimento |
| `references/autodiagnosi.md` | per firma d'autore, difetti ricorrenti, piano di crescita, confronto longitudinale |

## Verifica prima di consegnare

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

**Criterio di successo:** il report funziona se dice all'autore almeno una cosa sul
proprio lavoro che lui non poteva sapere. Non un difetto in più su una foto: un
pattern che attraversa l'insieme, una tesi che non aveva visto, o la ragione per
cui due immagini che ama si annullano a vicenda. Se il report si limita a
classificare bene le foto, ha funzionato a metà.

## Versione e integrità

<!-- INIZIO INVENTARIO: generato da build-skill.sh, non modificare a mano -->

**Versione 2026-08-22.11.** Oltre a questo SKILL.md, la skill è composta dai file
qui sotto, e li vuole tutti.

| File | Byte |
|---|---|
| `agents/openai.yaml` | 305 |
| `references/analisi-json.md` | 3146 |
| `references/autodiagnosi.md` | 12399 |
| `references/canone-editing.md` | 14294 |
| `references/connettori.md` | 11117 |
| `references/destinazioni.md` | 8477 |
| `references/didascalie.md` | 22132 |
| `references/flusso-incrementale.md` | 4390 |
| `references/ingestione.md` | 13197 |
| `references/pubblicazione-sito.md` | 14356 |
| `references/publication-plan.schema.json` | 3082 |
| `references/sequenza.md` | 17235 |
| `references/site-profile.example.json` | 1810 |
| `references/site-profile.schema.json` | 6274 |
| `scripts/esporta_tabella.py` | 9655 |
| `scripts/genera_dummy_pdf.py` | 35463 |
| `scripts/genera_payload_pubblicazione.py` | 10961 |
| `scripts/genera_provino_html.py` | 41645 |
| `scripts/genera_testi.py` | 19807 |
| `scripts/lib/publisher-core.mjs` | 19440 |
| `scripts/pipeline_incrementale.py` | 24668 |
| `scripts/prepara_provino.py` | 21094 |
| `scripts/publish_directus.mjs` | 12229 |
| `scripts/remote_directus.mjs` | 37271 |

<!-- FINE INVENTARIO -->

**Come si usa.** In F0 esegui `ls agents/ scripts/ references/` e confronta con l'elenco
qui sopra. Se combacia, la skill è integra e puoi lavorare. Se manca un file, la
copia è vecchia: fermati e chiedi all'utente di reinstallare il pacchetto.

**Perché esiste questa sezione.** Una skill installata in un account e una skill
in un repository sono due cose diverse, e possono andare fuori sincronia senza che
nessuno se ne accorga: il repository avanza a ogni commit, l'account resta fermo
all'ultimo pacchetto caricato. Da dentro una sessione non si vedono i commit, si
vedono solo i file. Quindi il controllo non può essere sulla data: deve essere
sull'inventario, che è l'unica cosa osservabile.

È già successo: una sessione ha lavorato con una copia priva di `genera_testi.py`
e delle regole sui due testi per immagine, ha prodotto un editing senza didascalie
e senza letture di lavoro, e il difetto è emerso solo quando l'utente ha
confrontato il risultato con un provino precedente. F0 esiste per rendere quel
fallimento impossibile.

## Rilascio

Chi modifica questa skill esegue, dalla radice del repository:

```bash
./build-skill.sh
```

Lo script rigenera `editing-portfolio-publisher.skill`, aggiorna l'inventario qui sopra e
stampa cosa è cambiato. Poi si committa **sia** i sorgenti **sia** il pacchetto:

```bash
git add -A && git commit -m "..."
```

Il push resta un'azione separata ed esplicita. **Passo che si dimentica:** installare o aggiornare la cartella
`editing-portfolio-publisher` nel proprio ambiente skill. Finché non lo fai, le
sessioni continuano a usare la versione precedente, e il repository aggiornato non
serve a niente.
