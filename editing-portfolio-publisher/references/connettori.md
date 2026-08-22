# Connettori, fil rouge, cluster

Il compito di questa fase non è trovare *un* tema. È capire che cosa tiene insieme
queste immagini **al di là dell'intenzione dell'autore**, perché quello che l'autore
crede di aver fotografato e quello che ha fotografato coincidono raramente.

## Indice

1. I tre livelli del fil rouge
2. Le diciotto specie di connettore
3. Come si costruisce un cluster
4. Le tre prove di robustezza
5. Ridondanza contro variazione
6. Le lacune, come commissione
7. Nominare un cluster
8. Quando ammettere che sono due progetti

## 1. I tre livelli del fil rouge

Dichiara sempre tutti e tre, in quest'ordine, perché l'errore tipico è fermarsi al
primo e chiamarlo tesi.

**Livello 1, il soggetto.** Cosa c'è davanti all'obiettivo. "Periferie", "mio
figlio", "mercati", "nebbia". È il livello che l'autore sa già. Non ha valore
critico da solo, ma serve come base di conteggio: dillo in una riga con i numeri
(quante immagini su quante).

**Livello 2, lo sguardo.** Come l'autore si mette davanti al soggetto: distanza,
altezza della camera, focale prevalente, tipo di luce cercata, momento scelto
rispetto all'azione, frontalità o obliquità, presenza o assenza di sguardi in
macchina. Questo livello è in gran parte **misurabile**: `firma.json` ti dà focali,
orientamenti, chiavi tonali e ore. Usalo, marcando `[MISURATO]`.

**Livello 3, l'ossessione.** Cosa ritorna senza che l'autore l'abbia deciso. Non un
soggetto e non una tecnica: una situazione, una relazione, una tensione. Esempi di
formulazione corretta:

- non "solitudine urbana", ma "qualcuno aspetta davanti a qualcosa che non si apre";
- non "architettura", ma "lo spazio è più grande di chi lo abita e lo dichiara";
- non "ritratti di mio figlio", ma "il momento in cui smette di accorgersi di me";
- non "still life", ma "oggetti appena abbandonati da qualcuno che tornerà".

Il terzo livello è la tesi del progetto, ed è l'unico che genera un titolo non
banale e una sequenza non arbitraria. Se non riesci a formularlo, non inventarlo:
scrivi che l'insieme ha un soggetto e uno sguardo ma non ancora un'ossessione, e
che questo è precisamente lo stato di un progetto non finito. È una diagnosi utile,
non un fallimento.

**Test di formulazione.** Il fil rouge di livello 3 è ben scritto se una persona che
non ha visto le foto, leggendolo, potrebbe scartare correttamente un'immagine che
non appartiene al progetto. Se la frase non permette di escludere niente, è troppo
generica: riscrivila.

## 2. Le diciotto specie di connettore

Cerca attivamente ognuna. Le prime sono ovvie, le ultime sono quelle che fanno la
differenza fra un report e una diagnosi.

**Di contenuto**

1. **Soggetto ripetuto**: lo stesso tipo di cosa o persona.
2. **Luogo**: lo stesso perimetro geografico, dichiarato o ricavabile.
3. **Tempo**: la stessa stagione, la stessa ora, lo stesso arco di giorni (dagli EXIF).
4. **Gesto**: la stessa azione o postura che torna in corpi diversi.
5. **Assenza**: quello che manca sistematicamente (mai volti, mai cielo, mai altre
   persone). L'assenza sistematica è un connettore forte e quasi sempre involontario.

**Di sguardo**

6. **Distanza**: sempre lontano, sempre addosso, sempre a un metro e mezzo.
7. **Altezza**: camera all'altezza degli occhi, del petto, del ginocchio, dall'alto.
8. **Focale**: prevalenza misurabile, e cosa comporta (il 35 racconta, il 50 osserva,
   l'85 isola, il 24 include e distorce, il tele comprime e spia).
9. **Rapporto col soggetto**: complice, rubato, autorizzato, indifferente.
10. **Momento**: prima dell'azione, sul culmine, dopo. Un autore che sceglie sempre
    il "dopo" ha una poetica, non un ritardo di riflessi. Verifica quale dei due è.

**Di forma**

11. **Chiave tonale**: alta, media, bassa, `[MISURATO]` con `luminanza_media` e `p5`/`p95`.
12. **Palette**: dominante cromatica ricorrente, `[MISURATO]` con `hue_dominante`.
    Attenzione a distinguere una palette scelta da una palette che è solo la
    conseguenza dell'ora e del luogo.
13. **Struttura compositiva**: la stessa geometria che ritorna (centrale, diagonale
    sinistra a destra, figura piccola in campo grande, riempimento totale).
14. **Densità**: quanto è affollato il fotogramma, `[MISURATO]` con `entropia`.
15. **Orientamento**: la prevalenza di verticali o orizzontali, e se è una scelta o
    una abitudine dell'impugnatura.
16. **Trattamento**: grana, contrasto, bianco e nero, mosso, come lingua costante.

**Di senso**

17. **Registro emotivo**: ironico, elegiaco, clinico, tenero, ostile. Uno solo, di
    norma, e quando ce ne sono due mescolati il progetto vacilla: verificalo.
18. **Attrito irrisolto**: la contraddizione che il progetto non scioglie (tenerezza
    e distanza, ordine e minaccia, bellezza e abbandono). È il connettore più
    prezioso, perché è ciò che rende un progetto interessante invece che coerente.

Nel report non elencare tutte e diciotto: cita le tre o quattro che reggono
davvero, con i numeri, e una sola frase per dire quali hai cercato e non trovato.

## 3. Come si costruisce un cluster

Un cluster non è una categoria: è un gruppo che regge come mini progetto autonomo.

Requisiti minimi:

- **almeno 4 immagini**, altrimenti è un accenno e va detto tale;
- **una tesi propria** in una frase, distinta dalla tesi generale;
- **almeno una variazione interna**: se tutte le immagini del cluster sono la stessa
  inquadratura, non è un cluster, è una ridondanza;
- **un confine**: devi poter dire quale immagine è stata esclusa e perché.

Procedura: parti dai connettori misurabili (chiave tonale, palette, orientamento,
densità) per fare i raggruppamenti grezzi, poi correggili guardando. I numeri
raggruppano per apparenza, il senso raggruppa per contenuto: quando le due cose
divergono, vince il senso, ma la divergenza va notata perché spesso indica un
problema di trattamento (due foto della stessa idea sviluppate in modo
incompatibile, che si separano solo per il colore).

Una immagine può stare in due cluster. Se sta in quattro, i cluster sono sbagliati.

Dai a ogni cluster un voto di forza da 1 a 10 (quanto reggerebbe da solo come
progetto o come galleria) e dichiara quanti cluster reggono davvero. Su 60 immagini
di norma ne reggono da 2 a 4: se te ne escono 9, hai fatto categorie.

## 4. Le tre prove di robustezza

Da fare sempre, e da riportare in due righe ciascuna. Sono il modo di verificare se
la tesi esiste o l'hai costruita tu.

**Prova della decapitazione.** Togli le 5 immagini più forti. Il fil rouge è ancora
leggibile nelle rimanenti? Se sì, il progetto ha un corpo. Se no, non hai un
progetto: hai 5 buone fotografie e un contorno, e questa è l'informazione più utile
che puoi dare all'autore.

**Prova dell'intruso.** Prendi l'immagine più bella dell'insieme e chiediti se
appartiene alla tesi o è arrivata da un altro lavoro. Le immagini più belle sono le
più frequenti intruse, perché sono state fatte in un momento di ispirazione diverso.
Se è un'intrusa, va nell'edit alternativo, non in questo.

**Prova del titolo cieco.** Se il titolo che stai proponendo funzionerebbe
altrettanto bene su un'altra cartella di foto di un altro autore, è un titolo vuoto
e la tesi che descrive è vuota. Riformula entrambi.

## 5. Ridondanza contro variazione

Lo script ti dà `coppie_simili.csv` con la distanza di hash. Interpretazione:

| Distanza dhash | Significato | Cosa fare |
|---|---|---|
| 0 a 5 | quasi identiche, spesso scatti a raffica | tenerne una, sempre. Nessuna eccezione |
| 6 a 12 | stessa idea a mezzo passo | tenerne una, salvo funzione diversa in sequenza dichiarata |
| 13 a 20 | stessa struttura, contenuto diverso | può essere variazione utile: verifica guardando |
| oltre 20 | non correlate visivamente | ignora il dato |

L'hash misura la forma, non il senso, quindi due immagini con distanza 25 possono
essere ridondanti di significato (dicono la stessa cosa in due modi diversi) e due
con distanza 8 possono essere una serie voluta. Il numero apre la domanda, non la
chiude.

**La differenza fra ridondanza e variazione** è la funzione. Una variazione è utile
se la seconda immagine aggiunge un dato, cambia il ritmo o abbassa la tensione in un
punto in cui serve. Se non riesci a scrivere che cosa aggiunge, è ridondanza.

Quando decidi fra due immagini quasi identiche, l'ordine dei criteri è: pulizia dei
bordi, poi gesto o espressione, poi luce, poi nitidezza. La nitidezza è ultima
perché è la prima cosa che l'autore guarda, e lo porta a scegliere male.

## 6. Le lacune, come commissione

Una lacuna non è "manca un ritratto". È un buco che la tesi apre e che le immagini
non riempiono. Come trovarle: prendi il fil rouge di livello 3 e chiediti quali
situazioni implica logicamente. Le implicazioni non fotografate sono le lacune.

Esempio. Tesi: "qualcuno aspetta davanti a qualcosa che non si apre". Implica: il
momento in cui si apre, chi non aspetta più, la cosa chiusa senza nessuno davanti,
un'attesa collettiva. Se nell'insieme non ce n'è nessuna, sono 4 lacune, e sono 4
istruzioni di scatto.

Formula ogni lacuna come **commissione eseguibile**, non come rimprovero: luogo o
tipo di situazione, cosa cercare, quale focale, quale momento, quante varianti. Una
lacuna che non si può andare a colmare domani mattina è formulata male.

Massimo 4 lacune. Oltre diventa un elenco di desideri.

## 7. Nominare un cluster

Ogni cluster e ogni galleria ha bisogno di un nome, e il nome deve essere buono
altrimenti sporca il lavoro. Proponi **tre candidati** e dichiara il registro di
ciascuno (i registri e la lista nera delle parole esauste sono in
`didascalie.md`, sezione titoli: leggila prima di proporre).

Regola specifica dei nomi di galleria, diversa da quella dei titoli di libro: la
galleria vive in un menu o in una griglia di anteprime, quindi il nome deve essere
breve (da una a tre parole), non deve competere con gli altri nomi di galleria dello
stesso sito, e non deve essere un'etichetta di categoria. "Street", "Ritratti",
"Viaggi" non sono nomi: sono cartelle. Se l'utente ha bisogno di categorie per
navigare, quelle stanno sotto, e sopra ci va il nome.

Verifica finale su ogni nome: cercandolo su internet, restituisce già mille
progetti fotografici identici? Se sì, cambialo.

## 8. Quando ammettere che sono due progetti

Segnali che la cartella contiene due lavori e non uno:

- i cluster più forti hanno teste diverse e non si toccano;
- il registro emotivo cambia in modo netto fra due gruppi;
- la prova della decapitazione fa emergere un fil rouge diverso da quello dichiarato;
- per far stare tutto in una tesi devi usare una formulazione così larga da non
  escludere niente (vedi il test di formulazione, sezione 1);
- le date raccontano due periodi distanti con un salto di stile in mezzo.

In quel caso non forzare. Dichiara i due progetti, dai a ciascuno una tesi e un
titolo, di' quale dei due è più maturo e perché, e consiglia su quale lavorare
adesso. Un fotografo che scopre di avere due progetti invece di uno confuso ha
ricevuto un servizio, non una bocciatura.
