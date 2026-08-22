# Contratto `analisi.json`

Leggi questo riferimento prima di creare o modificare `analisi.json`. Gli ID sono
quelli assegnati da `prepara_provino.py` e non cambiano tra gli artefatti.

## Struttura minima

```json
{
  "progetto": {
    "titolo": "Nessuno al terzo piano",
    "autore": "Giuseppe Lupo",
    "modalita": "photo-editor",
    "destinazione": "libro",
    "fil_rouge": "una frase verificabile",
    "titoli_candidati": [
      {"titolo": "Nessuno al terzo piano", "registro": "obliquo", "motivazione": "una riga"}
    ],
    "introduzione": "250-500 parole",
    "introduzione_posizione": "dopo",
    "statement": "60-120 parole",
    "registro_didascalie": "descrittivo",
    "copertina": "P007",
    "copertina_motivazione": "perché funziona come soglia del libro",
    "copertina_alternative": [{"id": "P011", "motivazione": "una riga"}],
    "colophon": {
      "Progetto": ["Titolo: Nessuno al terzo piano."],
      "Edizione": ["Tipologia: dummy editoriale."]
    }
  },
  "immagini": [
    {
      "id": "P007",
      "file": "DSCF1234.jpg",
      "thumb": "thumbs/P007_DSCF1234.jpg",
      "titolo": "opzionale",
      "genere": "street",
      "voti": {
        "autonomia": 8,
        "forza": 9,
        "coerenza": 7,
        "originalita": 6,
        "tecnica": 7,
        "funzione": 8
      },
      "verdetto": "da portfolio",
      "ruolo": "climax",
      "forza_principale": "una frase",
      "limite_principale": "una frase",
      "cluster": ["attese"],
      "descrizione": "30-100 parole, obbligatoria anche per gli scarti",
      "didascalia": "solo per le immagini dell'edit",
      "cieco": "esca"
    }
  ],
  "cluster": [
    {
      "id": "attese",
      "nome": "Nessuno al terzo piano",
      "registro_nome": "obliquo",
      "tesi": "una frase",
      "immagini": ["P007", "P011"],
      "forza": 8
    }
  ],
  "sequenza": {
    "spread": [["P003", null], ["P007", "P011"], [null, ["P020", "P021"]]],
    "ritmo": "A= M+ B-",
    "ritmo_perche": "perché questa forma è sostenuta dalle immagini",
    "alternative": [
      {"nome": "Alternata a picchi", "ritmo": "A= M- A+ B-", "perche": "motivo del rifiuto"}
    ]
  },
  "scarti": [{"id": "P010", "motivo": "ridondante con P007"}],
  "gallerie": [
    {"nome": "Nessuno al terzo piano", "ordine": ["P007", "P011"], "esca": "P007"}
  ]
}
```

## Invarianti

- Ogni ID citato in sequenza, cluster, gallerie o scarti esiste in `immagini`.
- In `spread`, `null` è una pagina bianca intenzionale. Una lista nella pagina
  indica più immagini lette insieme, mai un espediente per farne entrare di più.
- Copertina e apertura sono decisioni diverse. La copertina ha motivazione e due
  alternative; se coincide con l'apertura, spiega perché.
- `ritmo_perche` e almeno due alternative scartate rendono verificabile la
  sequenza.
- `descrizione` e `didascalia` hanno funzioni diverse; consulta `didascalie.md`.
- `progetto.colophon` è facoltativo. È una mappa ordinata sezione -> elenco di
  voci. Cambiarlo invalida soltanto il dummy nella pipeline incrementale.
- Il blocco facoltativo `pubblicazione` è descritto in `pubblicazione-sito.md`.
