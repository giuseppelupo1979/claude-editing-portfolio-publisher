# Flusso incrementale

Leggi questo riferimento quando esistono già artefatti in `_analisi`, quando il
progetto prosegue in più turni o quando una correzione non deve riavviare l'intera
analisi.

## Stato e impronte

`scripts/pipeline_incrementale.py` mantiene `_analisi/.pipeline-incrementale.json`.
Per ogni originale registra nome, dimensione, mtime e SHA-256. Se dimensione e
mtime non cambiano riusa l'hash precedente; `--rehash` rilegge tutti i byte e va
usato prima della consegna finale o quando si sospetta una modifica che abbia
conservato i metadati del file.

Lo stato non contiene immagini, credenziali o testi segreti. Contiene impronte,
dipendenze e hash degli output. Un output modificato a mano diventa `stale`.

## Tre comandi

Preflight unico, senza generare deliverable:

```bash
python3 scripts/pipeline_incrementale.py preflight CARTELLA \
  --profile ~/.config/editing-portfolio-publisher/sites/SITO.json \
  --doctor-site
```

`--doctor-site` è sola lettura ma apre SSH; usalo nel preflight quando il lavoro
include la pubblicazione. Senza pubblicazione ometti profilo e doctor. Il report
riunisce inventario, artefatti correnti o scaduti, geolocalizzazioni incomplete,
configurazione del sito, stato dell'approvazione e prossimo passo.

La prima preparazione, o la riparazione dei soli artefatti scaduti, usa:

```bash
python3 scripts/pipeline_incrementale.py build CARTELLA --confirm
```

Se `analisi.json` non esiste, il comando produce soltanto ingestione, metriche,
miniature e griglia e poi si ferma. Non inventa l'analisi.

## Che cosa richiede una firma

Solo la pubblicazione. `testi.md`, `tabella`, `provino.html` e `dummy.pdf` sono file
riscrivibili nella cartella dell'utente: `build --confirm` li rigenera senza chiedere
niente, e correggere un refuso in una didascalia costa un comando, non un giro di
autorizzazione. Il piano che finisce su Directus è un'altra cosa, e resta vincolato a
un `authorization_hash`.

Quando la proposta di pubblicazione è completa, genera il documento di approvazione:

```bash
python3 scripts/pipeline_incrementale.py approve CARTELLA
```

Il documento include l'hash degli originali e tutto ciò che finisce online: blocco
`pubblicazione`, gallerie, e per ogni immagine file, titolo, descrizione, didascalia,
luogo, coordinate, provenienza e precisione. Non include titolo del progetto,
introduzione, statement, colophon e sequenza del libro, che non escono da questa
macchina. Mostralo all'utente. Dopo la sua approvazione registra esattamente lo
stesso documento:

```bash
python3 scripts/pipeline_incrementale.py approve CARTELLA \
  --confirm --authorization-hash HASH
```

Qualsiasi modifica a ciò che il documento copre invalida l'approvazione, e
`--only publication` si rifiuta di ricostruire il piano finché non ne registri una
nuova. Gli altri artefatti non se ne accorgono. `build --confirm` genera solo gli
output scaduti; `--only dummy` o `--only texts,table` restringe il lavoro.

## Grafo delle dipendenze

| Artefatto | Dipende da |
|---|---|
| ingestione, metriche, miniature, griglie | hash originali, parametri e script di ingestione |
| `testi.md` | campi testuali, ordine editoriale e script testi |
| `tabella.csv` e, se `openpyxl` è installato, `tabella.xlsx` | voti, ruoli, cluster, sequenza, disponibilità di `openpyxl` e script tabella |
| `provino.html` | campi visualizzati, miniature e script HTML |
| `dummy.pdf` + `dummy.qa.json` | sequenza, apparato del libro, colophon, metriche EXIF, miniature e script PDF |
| `publication-plan.json` | solo blocco pubblicazione, campi immagine usati, metriche, sorgente e profilo |

Conseguenze intenzionali:

- cambiare soltanto il colophon rende scaduto soltanto il dummy;
- cambiare soltanto il blocco `pubblicazione` rende scaduto soltanto il piano;
- una correzione a descrizione, didascalia o luogo rigenera gli elaborati che
  mostrano quel campo, senza ricalcolare EXIF, metriche o miniature;
- cambiare un originale invalida ingestione e approvazione di pubblicazione;
- il foglio Excel entra nel grafo solo quando `openpyxl` c'è: senza, l'artefatto è
  il solo CSV e non risulta perennemente scaduto.

## Controllo PDF mirato

`genera_dummy_pdf.py` scrive anche `dummy.qa.json`. Contiene numero di pagine PDF,
numero di pagine fisiche del libro, intervalli delle sezioni, overflow rilevati e
`changed_pdf_pages`. Alla prima generazione controlla tutto il PDF. Nei cicli
successivi apri le sole pagine elencate, purché `qa_ok=true`; con `--qa-strict` un
overflow o un conteggio incoerente interrompe la build.

Il numero di pagine fisiche è doppio rispetto alle pagine PDF perché ogni pagina
del file rappresenta uno spread. Copertina, frontespizio, testi, tavole, indice,
schede, attrezzatura e colophon si sommano alle fotografie: cinque immagini non
implicano un dummy di cinque pagine.

## Lettura visuale e contesto

Per 3-12 foto produci una sola griglia. Apri l'alta risoluzione solo per scatti in
cui miniatura e decisione divergono, dettagli tecnici rilevanti, geolocalizzazione
visiva incerta o coppie simili da risolvere. Non duplicare lo stesso audit in più
agenti. Se l'utente richiede esplicitamente agenti secondari, passa a ciascuno solo
la griglia o l'artefatto necessario, le domande assegnate e gli ID interessati, non
l'intera conversazione.
