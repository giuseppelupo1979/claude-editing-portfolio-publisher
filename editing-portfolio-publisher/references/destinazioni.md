# Destinazioni: numeri e criteri

La stessa cartella di fotografie produce quattro edit diversi. Chi non lo sa fa un
solo edit e lo usa per tutto, ed è il motivo per cui i portfolio online sembrano
libri mal riusciti e le candidature ai concorsi sembrano portfolio accorciati.

Dichiara sempre la destinazione **prima** di selezionare, e con essa il numero.

## Indice

1. Libro fotografico
2. Mostra e stampa
3. Portfolio online e sito
4. Concorsi e premi
5. Tabella di confronto rapido
6. Quando la destinazione è sbagliata

## 1. Libro fotografico

**Numeri.** Vedi l'aritmetica delle pagine in `sequenza.md`. In sintesi: 16 a 24
immagini per una fanzine, 30 a 45 per un libro breve d'autore, 60 a 90 per una
monografia.

**Cosa premia il libro.** La funzione. Un'immagine mediocre in autonomia può essere
indispensabile come pausa, come ponte fra due movimenti, come abbassamento di
tensione prima di un picco. Questo è il fatto che rende il libro la destinazione più
generosa e la più difficile: accetta immagini che nessun'altra destinazione
accetterebbe, ma solo se hanno un compito preciso.

**Cosa punisce.** La ripetizione, perché il lettore ha tempo di accorgersene, e la
mancanza di vuoti. Punisce anche il picco continuo: un libro di sole immagini forti
è illeggibile dopo dieci pagine.

**Criterio decisivo.** Per ogni immagine devi poter scrivere in una riga che cosa fa
in quel punto e non altrove. Se la riga non viene, l'immagine esce.

**Verdetti utili.** Peso `coerenza` alto (25) e `funzione` alto (20). L'autonomia
conta poco (10): è l'unica destinazione dove è così.

**Da consegnare.** Selezione, titolo con tre candidati, architettura dichiarata,
sequenza a spread, notazione del ritmo, didascalie in un registro, apertura e
chiusura motivate, scelta di copertina separata, dummy PDF.

## 2. Mostra e stampa

**Numeri.** Da 8 a 15 per una parete singola, da 20 a 30 per una sala. Oltre i 30 lo
spettatore scorre invece di guardare.

**Cosa premia la mostra.** La tenuta a distanza e la materia. Un'immagine che vive di
microdettaglio non regge a tre metri; una silhouette pulita sì. Premia le immagini
che guadagnano ingrandendo, e sono meno di quante l'autore crede: la maggior parte
delle fotografie ha una dimensione ottimale oltre la quale si sfalda.

**Cosa punisce.** Il clipping delle alte luci, che a parete si vede come un buco
bianco (`clip_bianchi_pc` sopra il 2 percento è un segnale, `[MISURATO]`). Punisce
il rumore ingrandito, la nitidezza insufficiente rispetto alla dimensione, e la
mancanza di gerarchia (dieci immagini della stessa dimensione fanno un tappeto).

**Dimensione di stampa.** Usa i pixel reali da `metriche.json` e la regola dei tre
scenari: a 300 ppi (fine art, visione da vicino), a 240 ppi (compromesso corrente),
a 180 ppi (parete, visione da oltre un metro e mezzo). Non citare mai una dimensione
massima senza dichiarare a quale ppi e a quale distanza. Se stai lavorando su
miniature o su file ridotti, la dimensione di stampa non è determinabile e va detto.

**Da consegnare.** Edit corto, una sola immagine manifesto con motivazione,
dimensioni relative (una grande, tre medie, sei piccole), coppie da affiancare,
percorso probabile della parete, distanze di lettura, note su clipping e nitidezza
per ogni immagine che va oltre il formato medio.

## 3. Portfolio online e sito

**Numeri.** Da 12 a 20 immagini per galleria. Da 2 a 4 gallerie in totale: cinque
gallerie dicono al visitatore che non hai scelto.

**Cosa premia il web.** L'autonomia (peso 30, il più alto delle quattro
destinazioni) e la leggibilità in miniatura. Lo schermo è piccolo, la visione è
veloce, il contesto è zero: ogni immagine deve funzionare come se fosse la prima
vista da uno sconosciuto, perché spesso lo è.

**Cosa punisce.** Le immagini che hanno bisogno di stare accanto ad altre. Le
orizzontali su telefono (perdono metà dell'effetto). I dettagli fini. I contrasti
delicati, che su schermo non calibrato scompaiono. E la lunghezza: le ultime
immagini di una galleria da 40 non le vede nessuno, quindi ci sono solo per l'autore.

**Criterio decisivo.** Guarda la miniatura a 200 px di lato lungo: se non capisci
cosa è, sul web quell'immagine non esiste. Le griglie prodotte da
`prepara_provino.py` servono anche a questo, ed è un uso legittimo delle miniature.

**Prima immagine.** È l'unico caso in cui va in testa la fotografia migliore: sul web
la prima immagine è un'esca, non un'apertura. Vedi `sequenza.md`, sezione 9.

**Da consegnare.** Gallerie con nome definitivo (registro dichiarato, mai una
categoria), ordine di scorrimento, immagine esca con motivazione, quali immagini
tenere fuori dal web e perché, nota sulla proporzione verticali/orizzontali.

## 4. Concorsi e premi

**Numeri.** Quasi sempre 5 o 10, e quasi sempre il bando lo dice: chiedi il bando
all'utente, o chiedi il numero, prima di selezionare. Se il numero è 5, non
consegnarne 6 "fra cui scegliere": la selezione è il lavoro.

**Cosa premia una giuria.** In ordine di peso reale: l'originalità (peso 25, secondo
solo alla forza), la coerenza interna della serie letta in due minuti, e la
riconoscibilità immediata di un punto di vista. Una giuria guarda migliaia di
immagini: la tua serie ha circa quindici secondi per essere messa nella pila giusta.

**Cosa punisce.** Il già visto (il tramonto, il senzatetto in bianco e nero, il
bambino che ride nel paese povero, il riflesso nella pozzanghera, il tuffo dal molo).
Punisce anche la varietà: cinque immagini brave ma slegate perdono contro cinque
immagini meno brave che sono chiaramente un progetto. Punisce lo statement retorico,
e punisce i titoli della lista nera in `didascalie.md`.

**Criterio decisivo.** La serie deve essere leggibile come progetto **senza lo
statement**. Lo statement conferma, non spiega.

**Onestà sulle probabilità.** Chiudi sempre con una valutazione esplicita: in che
tipo di concorso questa serie ha una possibilità, in quale no, e cosa mancherebbe per
alzare le probabilità. È l'informazione che l'autore non ha, e vale più del voto.

**Da consegnare.** Le 5 o 10 immagini nell'ordine di presentazione, statement da 100
parole, lettura da giuria (cosa vedrà nei primi quindici secondi), i cliché che
sfiori e come li disinneschi, valutazione delle probabilità.

## 5. Tabella di confronto rapido

| | libro | mostra | web | concorso |
|---|---|---|---|---|
| numero tipico | 30 a 45 | 8 a 15 | 12 a 20 | 5 o 10 |
| asse dominante | coerenza | autonomia e forza | autonomia | forza e originalità |
| conta la funzione in sequenza | molto | poco | no | poco |
| accetta immagini deboli da sole | sì, con compito | no | no | no |
| tollera l'eterogeneità | sì, per movimenti | poco | sì, per gallerie separate | no |
| tempo di attenzione | ore | minuti | secondi | quindici secondi |
| errore fatale | ridondanza | clipping e ingrandimento | illeggibilità in piccolo | cliché |
| il testo serve | poco | didascalie brevi | quasi mai | statement obbligatorio |

Uso pratico della tabella: dopo aver dato i sei voti a ogni immagine, `esporta_tabella.py`
calcola il punteggio per tutte e quattro le destinazioni. Le immagini che cambiano
molto di rango fra due destinazioni sono le più informative del lavoro, perché
mostrano all'autore che tipo di fotografo è: chi ha molte immagini forti per il
concorso e debolí per il libro fa singole fotografie, chi ha l'inverso fa progetti.
Dillo, è una delle cose che l'autore non può sapere da solo.

## 6. Quando la destinazione è sbagliata

Capita che l'utente chieda un edit per una destinazione che il materiale non regge.
In quel caso non fare finta: fai l'edit richiesto **e** aggiungi due righe sulla
destinazione più adatta.

Segnali tipici:

- **Vuole un libro** ma le immagini sono 18 tutte forti e tutte autonome, senza
  pause né ponti. Non è un libro, è una mostra o un portfolio: un libro con 18
  immagini eccellenti e nessun respiro dura otto pagine.
- **Vuole un concorso** ma le immagini sono legate da un fil rouge debole e sono
  brave singolarmente. Meglio candidare a un premio a immagine singola.
- **Vuole una mostra** ma le immagini vivono di dettaglio fine e di piccolo formato.
  Meglio un libro o una cartella di stampe da sfogliare.
- **Vuole un portfolio online** ma il lavoro è una sequenza che ha senso solo
  nell'ordine. Sul web l'ordine non si controlla: proponi la sequenza come progetto
  a pagina singola, non come galleria.
