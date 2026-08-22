# Firma d'autore, difetti ricorrenti, crescita

Questa è la parte per cui vale la pena analizzare un insieme invece di una foto: su
una singola immagine puoi solo dire cosa è andato storto, su sessanta puoi dire cosa
va storto **sempre**, e quello si può correggere.

Principio di soglia: un errore su una immagine è un incidente, su tre è una
tendenza, su un terzo dell'insieme è una abitudine motoria. Le abitudini si
correggono con un esercizio, gli incidenti no. Quindi **conta sempre**, e riporta la
frequenza come numero: "in 14 immagini su 22", non "spesso".

## Indice

1. La firma d'autore involontaria
2. Come leggere firma.json
3. I difetti ricorrenti, tassonomia
4. Dalla frequenza all'esercizio
5. La commissione
6. Il confronto longitudinale
7. Come dirlo senza scoraggiare

## 1. La firma d'autore involontaria

La firma è l'insieme delle scelte che l'autore ripete senza deciderle. Non è uno
stile: lo stile è voluto, la firma è automatica. Metà è talento, metà è pigrizia
motoria, e il lavoro consiste nel separare le due.

Struttura della sezione nel report, quattro punti:

1. **Cosa fai sempre**, con i numeri (focale prevalente, altezza della camera,
   distanza, chiave tonale, orientamento, ora del giorno, densità).
2. **Cosa non fai mai**, e questa è la parte più utile: le assenze sistematiche.
   Nessun primo piano, mai il cielo, mai persone di spalle, mai il flash, mai il
   verticale, mai sotto l'altezza degli occhi. L'autore in genere non sa di avere
   queste assenze.
3. **Quale delle due liste è talento e quale è abitudine.** Criterio: se la scelta
   ripetuta serve la tesi del progetto, è talento e va nominata come risorsa; se la
   tesi non la richiede, è abitudine e va messa in discussione. Motiva.
4. **La firma in una frase**, come la descriverebbe qualcuno che vede il lavoro
   senza conoscere l'autore. È la frase che l'autore ricorderà per mesi: scrivila
   bene, precisa, senza complimenti e senza sentenze.

## 2. Come leggere firma.json

Il file contiene le aggregazioni prodotte dallo script. Uso critico di ciascuna:

| Campo | Lettura utile | Trappola |
|---|---|---|
| `focali` | una prevalenza oltre il 60 percento è una firma. Due picchi separati (per esempio 24 e 85) sono due modi di guardare, verifica se corrispondono a due cluster | la focale nominale su sensore ridotto non è l'angolo di campo: usa `focale_equivalente` se presente, altrimenti dichiara l'incertezza |
| `aperture` | tutte a tutta apertura è una firma, e spesso un riflesso condizionato: verifica se lo sfondo sfocato serve o è automatico | su alcuni corpi il dato manca con ottiche manuali |
| `iso` | ISO alti sistematici indicano ore o interni ricorrenti, non solo scelta tecnica | non giudicare il rumore da qui, guarda `rumore_proxy` e le miniature |
| `ore` | la distribuzione oraria è il dato più rivelatore di tutti: dice quando esci con la macchina, e quindi quale luce conosci e quale no | se le date sono state riscritte da un software, il dato non vale: verifica in `ingestione.md` |
| `orientamenti` | oltre l'80 percento orizzontale è quasi sempre abitudine di impugnatura, non scelta | in alcune destinazioni (web) è un limite concreto, non solo un vizio |
| `chiavi_tonali` | la coerenza tonale è la firma più visibile e la più facile da usare in sequenza | non confondere la chiave della scena con quella dello sviluppo |
| `bn_vs_colore` | se sono mescolati in proporzione simile, quasi sempre l'autore non ha deciso | verifica prima con le miniature: lo script deduce dal livello di saturazione |
| `corpi` e `ottiche` | utile per capire se cambia sguardo cambiando attrezzatura | non trarne giudizi di qualità |
| `giorni_attivi`, `arco_temporale` | dice se il progetto è un lavoro o una raccolta: dieci uscite in tre anni non sono un progetto | i doppioni di data falsano il conteggio |

Un incrocio che vale sempre la pena: **ora del giorno per punteggio**. Se le
immagini migliori sono tutte nella stessa fascia oraria, l'autore ha una luce che sa
usare e le altre no, e la conseguenza operativa è immediata (esci in quell'ora, o
studia deliberatamente l'altra). Lo stesso incrocio con la focale e con la distanza.

## 3. I difetti ricorrenti, tassonomia

Cerca attivamente questi, contali, e riporta solo quelli con frequenza rilevante.
Ordinati per quanto spesso si trovano in insiemi di fotografi avanzati.

**Di bordo e di cornice**
1. Intrusioni sul bordo (un pezzo di elemento estraneo che entra e non ha funzione).
2. Amputazioni infelici (arti, oggetti o teste tagliati in un punto che disturba).
3. Fusioni sfondo e soggetto (il palo dietro la testa, il ramo che nasce dalla spalla).
4. Bordo inferiore trascurato (in genere si compone guardando il centro e in alto).

**Di distanza e di scelta del momento**
5. Un passo troppo indietro. Il difetto più comune in assoluto: la fotografia
   contiene la scena giusta più il venti percento di roba inutile.
6. Momento anticipato o postumo in modo involontario. Distinguilo da quello voluto.
7. Assenza di primo piano: composizioni a un solo piano ripetute.

**Di luce**
8. Alte luci bruciate ricorrenti (`clip_bianchi_pc` alto `[MISURATO]`), tipico di chi
   espone per l'ombra senza controllare.
9. Luce frontale ripetuta, che appiattisce: sintomo del fotografare senza girare
   intorno al soggetto.
10. Contrasto uniforme su tutto l'insieme applicato in post, che cancella le
    differenze di luce reale fra le scene.

**Di trattamento e post produzione**

> **Come si dimostra una manipolazione, e come non si dimostra.** Due immagini
> incoerenti provano che una delle due è alterata, mai quale. Per stabilire la
> direzione servono elementi che non possono cambiare (sempreverdi, incarnati,
> superfici dipinte), marcatori di stagione o di ora interni all'immagine, i residui
> lasciati dall'intervento (una rotazione di gamma risparmia ciò che stava fuori
> gamma: quei superstiti sono la firma), oppure la parsimonia sull'insieme. Finché non
> hai uno di questi, scrivi `[RICAVATO]` e dillo. E quando la manipolazione è
> accertata, non trattarla come una colpa: è una scelta d'autore, e il rilievo
> semmai è che faccia il lavoro che doveva fare l'occhio.

11. Ricetta unica applicata a tutto, riconoscibile da valori di `contrasto` e
    `saturazione_media` molto simili su scene diversissime `[MISURATO]`.
12. Nitidezza eccessiva, aloni sui contorni.
13. Virata di colore incoerente fra immagini contigue della stessa scena.
14. Bianco e nero usato come rimedio: se le immagini in bianco e nero dell'insieme
    sono tutte quelle con colore problematico, il bianco e nero non è una scelta.

**Di struttura del lavoro**
15. Ridondanza sistematica (molte coppie in `coppie_simili.csv`): l'autore non decide
    sul campo e delega la scelta al computer.
16. Copertura sbilanciata (venti immagini di un aspetto del tema e due di un altro).
17. Mancanza di varianti: una sola inquadratura per situazione, cioè nessun margine di
    scelta in fase di editing.
18. Titolo o tema dichiarato che non corrisponde a quello che le immagini mostrano.

Per ciascuno riporta: nome del difetto, frequenza (n su totale), gli id delle
immagini in cui si vede meglio, e la causa probabile sul campo (non la correzione in
post: la causa). La causa è ciò che rende l'informazione utile.

## 4. Dalla frequenza all'esercizio

Massimo **tre esercizi** per report. Oltre, nessuno li fa. Scegli i tre difetti con
frequenza più alta fra quelli correggibili sul campo, e ignora quelli che dipendono
dall'attrezzatura o dal caso.

Un esercizio è ben scritto se ha tutte e cinque queste cose:

1. **Vincolo unico**, non un elenco di buoni propositi.
2. **Eseguibile in una sola uscita** (una o due ore).
3. **Verificabile**: al ritorno si può dire se l'hai fatto o no, senza opinioni.
4. **Collegato al difetto**, esplicitamente.
5. **Fastidioso**: se l'esercizio è comodo, non corregge niente.

Esempi di forma corretta:

- Difetto: un passo troppo indietro (14 su 22). Esercizio: un'uscita con una sola
  focale fissa da 50 mm, obbligo di scattare solo a meno di due metri dal soggetto,
  trenta scatti, nessun ritaglio consentito in post.
- Difetto: intrusioni sul bordo (9 su 22). Esercizio: prima di ogni scatto, un giro
  completo dei quattro bordi con l'occhio, e obbligo di dichiarare a voce (o
  annotare) cosa c'è su ciascuno. Venti scatti, non uno di più.
- Difetto: luce frontale ripetuta (12 su 22). Esercizio: un'uscita in cui il sole deve
  stare sempre fra i 90 e i 180 gradi rispetto all'asse di ripresa. Se non lo è, non
  si scatta, si cammina.
- Difetto: nessuna variante per situazione (17 su 22). Esercizio: cinque situazioni,
  cinque scatti diversi per ciascuna (cambio di altezza, di distanza, di orientamento,
  di momento, di focale), e in editing si tiene una sola immagine per situazione.

Esempi di forma sbagliata: "presta più attenzione ai bordi", "cerca luci più
interessanti", "prova a variare le inquadrature". Non sono esercizi, sono desideri.

## 5. La commissione

Oltre agli esercizi, chiudi con una **commissione**: da tre a cinque scatti precisi
che mancano al progetto e che vanno fatti. Vengono dalle lacune individuate in
`connettori.md`, sezione 6. Ogni voce contiene: cosa deve accadere nell'immagine,
dove o in che tipo di situazione, quale focale e quale distanza, quale momento
aspettare, quante varianti.

La commissione è la differenza fra un'analisi e un piano di lavoro. Un fotografo che
esce con cinque scatti da fare in tasca torna con materiale, un fotografo che esce
con un consiglio generico torna con le solite foto.

Se il progetto è già chiuso e non è più possibile aggiungere immagini, dillo e
trasforma la commissione nel **prossimo progetto**: le lacune di un lavoro finito
sono la traccia del successivo, e questa è una delle cose più utili che puoi dire.

## 6. Il confronto longitudinale

Si fa se esiste un `analisi.json` di una sessione precedente (nella cartella
`_analisi`, o fornito dall'utente). È la funzione che rende questa skill uno
strumento di crescita invece che un giudizio.

Cosa confrontare, in questo ordine:

1. **I difetti ricorrenti**: quali frequenze sono scese, quali sono uguali, quali
   sono salite. Le frequenze, non le impressioni.
2. **La firma**: si è allargata (nuove focali, nuove ore, nuovi orientamenti) o si è
   stretta? Una firma che si stringe può essere maturazione o irrigidimento: decidi
   quale, guardando se la varietà persa serviva la tesi.
3. **Il voto del corpus sui sei assi**: quale asse è cresciuto. Di norma cresce prima
   la tecnica, poi la coerenza, poi l'originalità, e quest'ultima è la sola che conta
   davvero: dillo.
4. **Le lacune della volta precedente**: sono state colmate? Se la commissione non è
   stata eseguita, non fare la predica, ma non riproporla identica: chiediti se era
   sbagliata (troppo generica, troppo scomoda, non interessava) e riformulala.
5. **Le immagini ancora presenti**: quali foto della selezione precedente
   sopravvivono a questa. Se sopravvivono tutte, l'autore non sta scattando; se non
   sopravvive nessuna, o è cresciuto molto o ha cambiato progetto.

Chiudi il confronto con una riga sola: cosa è cambiato davvero. Non tre paragrafi.

## 7. Come dirlo senza scoraggiare

L'obiettivo non è essere gentili, è essere utili, e l'utilità dipende dal fatto che
l'autore continui a fotografare. Tre accortezze che non costano niente in onestà:

- **Ogni difetto ricorrente ha una causa sul campo, non una colpa.** "Fotografi a un
  passo di troppo" è un dato, "sei timido col soggetto" è un giudizio sulla persona:
  attieniti al primo, che è anche più vero e più utile.
- **Nomina sempre la risorsa insieme al limite**, quando la risorsa esiste
  davvero. Non per addolcire, ma perché quasi sempre sono la stessa cosa: la distanza
  che rovina i primi piani è la stessa che rende buoni i campi larghi, e capirlo
  cambia il modo di lavorare.
- **Un solo verdetto duro per report.** Se tutto è duro, niente viene ascoltato.
  Scegli il rilievo più importante, dallo senza attenuazioni, e lascia che gli altri
  siano informativi invece che perentori.

Vietato in ogni caso: l'incoraggiamento generico in chiusura, le formule tipo
"continua così", i paragoni con "molti fotografi", e qualunque frase che si potrebbe
scrivere senza aver visto queste immagini.
