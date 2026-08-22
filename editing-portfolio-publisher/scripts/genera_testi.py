#!/usr/bin/env python3
"""
genera_testi.py: raccoglie e controlla tutti i testi del progetto.

Legge analisi.json e produce `testi.md`, il documento con:
  titolo e candidati, introduzione, statement, nota dell'autore,
  didascalie numerate come tavole nell'ordine della sequenza,
  elenco dei segnaposto da compilare,
  referto del controllo automatico.

Non inventa testi: quelli li scrivi tu in analisi.json seguendo
`references/didascalie.md`. Questo script li mette in ordine, li impagina e fa il
lavoro che a occhio non si riesce a fare: contare le parole, trovare le ripetizioni
fra didascalie vicine, scovare gli aggettivi valutativi, i verbi descrittivi, le
parole della lista nera e i segnaposto rimasti aperti.

Uso:
  python3 genera_testi.py analisi.json [-o testi.md] [--solo-controllo]
                          [--parole-min 5] [--parole-max 25]
"""

import argparse
import json
import os
import re
import sys

LISTA_NERA = [
    "riflessi", "frammenti", "attimi", "sguardi", "anime", "luci e ombre",
    "chiaroscuri", "emozioni", "suggestioni", "atmosfere", "visioni", "contrasti",
    "geometrie urbane", "silenzi", "il tempo sospeso", "metropoli", "umanità",
    "volti e storie", "colori del mondo", "angoli nascosti", "dettagli",
    "prospettive", "oltre lo sguardo", "il respiro della città", "essenza",
    "tracce", "impronte", "memorie",
]
FORMULE_NERE = [
    "viaggio nel", "viaggio nella", "alla ricerca di", "storie di", "il mondo di",
    "dietro le quinte",
]
VALUTATIVI = [
    "splendido", "splendida", "magnifico", "magnifica", "meraviglioso", "meravigliosa",
    "suggestivo", "suggestiva", "intenso", "intensa", "poetico", "poetica",
    "emozionante", "affascinante", "incantevole", "stupendo", "stupenda",
    "straordinario", "straordinaria", "toccante", "commovente", "delicato",
]
DESCRITTIVI = [
    "si vede", "si vedono", "in primo piano", "sullo sfondo", "l'immagine mostra",
    "la foto mostra", "ritrae", "raffigura", "si nota", "si scorge", "possiamo vedere",
    "al centro dell'immagine",
]
VIETATE_TESTI = [
    "emozioni", "ho voluto", "raccontare", "indagare", "poesia", "poetica",
]
GIUDIZI = [
    "la decisione è", "la decisione e", "il gesto fotografico", "ottiene", "non ottiene",
    "manca", "riesce", "fallisce", "debole", "il limite", "il difetto", "errore",
    "avrebbe dovuto", "sarebbe stato meglio", "non funziona", "funziona bene",
    "purtroppo", "peccato che", "andava", "sbagliato",
]
CHIUSURE_RIASSUNTIVE = [
    "in conclusione", "in definitiva", "riassumendo", "questo lavoro vuole",
    "questo progetto vuole", "in fin dei conti",
]
STOPWORD = set("""il lo la i gli le un uno una di a da in con su per tra fra e o ma
che chi cui non ne ci vi si mi ti come quando dove perché più meno molto poco tutto
tutti tutte questo questa questi queste quel quella quei quelle è era sono ero c'è
del della dei delle dal dalla al alla allo agli alle nel nella nei nelle sul sulla
suo sua loro mio mia anche ancora già solo dopo prima sopra sotto verso""".split())

MESI = ("gennaio febbraio marzo aprile maggio giugno luglio agosto settembre "
        "ottobre novembre dicembre").split()

ASSI_ORDINE = ("sequenza", "galleria", "id")


def scorri(spread):
    """Gli id di una sequenza, anche quando una pagina ne contiene piu' di uno."""
    fuori = []
    for coppia in spread or []:
        for pagina in coppia:
            if not pagina:
                continue
            fuori.extend(pagina if isinstance(pagina, list) else [pagina])
    return fuori


def parole(t):
    return re.findall(r"[\wàèéìòùÀÈÉÌÒÙ']+", (t or "").lower())


def trova(testo, elenco):
    t = (testo or "").lower()
    return [x for x in elenco if x in t]


def ordine_tavole(dati):
    seq = (dati.get("sequenza") or {}).get("spread")
    if seq:
        return scorri(seq), "sequenza"
    gall = dati.get("gallerie") or []
    if gall and gall[0].get("ordine"):
        return list(gall[0]["ordine"]), "galleria"
    return sorted(i["id"] for i in dati.get("immagini") or []), "id"


def controlla(dati, ids_tavole, pmin, pmax):
    """Restituisce (elenco_avvisi, elenco_segnaposto)."""
    avvisi, segnaposto = [], []
    prog = dati.get("progetto") or {}
    per_id = {i["id"]: i for i in dati.get("immagini") or []}
    registro = (prog.get("registro_didascalie") or "").lower()

    if not registro:
        avvisi.append(("registro", "Nessun registro di didascalia dichiarato in progetto.registro_didascalie. Sceglierne uno e uno solo: muto, fattuale, contestuale, obliquo, citazionale."))

    # titoli
    for campo in ("titolo", "sottotitolo"):
        v = prog.get(campo)
        if v:
            for parola in trova(v, LISTA_NERA) + trova(v, FORMULE_NERE):
                avvisi.append((campo, "Contiene una voce della lista nera: %s. Cambiare." % parola))
    for c in dati.get("cluster") or []:
        for parola in trova(c.get("nome", ""), LISTA_NERA):
            avvisi.append(("cluster %s" % c.get("id", ""), "Nome nella lista nera: %s." % parola))
    for g in dati.get("gallerie") or []:
        for parola in trova(g.get("nome", ""), LISTA_NERA):
            avvisi.append(("galleria %s" % g.get("nome", ""), "Nome nella lista nera: %s." % parola))
    if not prog.get("titoli_candidati"):
        avvisi.append(("titolo", "Manca progetto.titoli_candidati: servono tre candidati, ciascuno con registro e motivazione."))
    elif len(prog["titoli_candidati"]) < 3:
        avvisi.append(("titolo", "Solo %d candidati su 3." % len(prog["titoli_candidati"])))

    # introduzione
    intro = prog.get("introduzione")
    if not intro:
        avvisi.append(("introduzione", "Assente. Obbligatoria per libro, galleria, mostra e concorso."))
    else:
        n = len(parole(intro))
        if n < 250:
            avvisi.append(("introduzione", "%d parole, sotto le 250: è una nota, non un'introduzione." % n))
        elif n > 500:
            avvisi.append(("introduzione", "%d parole, oltre le 500: taglia, il lettore vuole le fotografie." % n))
        for v in trova(intro, VIETATE_TESTI):
            avvisi.append(("introduzione", "Parola vietata nei testi: %s." % v))
        for v in trova(intro, DESCRITTIVI):
            avvisi.append(("introduzione", "Descrive le immagini invece di affiancarle: %s." % v))
        frasi = [f.strip() for f in re.split(r"(?<=[.!?])\s+", intro.strip()) if f.strip()]
        if frasi:
            for c in trova(frasi[-1], CHIUSURE_RIASSUNTIVE):
                avvisi.append(("introduzione", "L'ultima frase riassume (%s): l'introduzione non deve chiudere il senso." % c))
        if not prog.get("registro_introduzione"):
            avvisi.append(("introduzione", "Manca progetto.registro_introduzione: fatto e metodo, scena madre, oggetto, lettera, elenco."))

    # statement
    st = prog.get("statement")
    if not st:
        avvisi.append(("statement", "Assente. Obbligatorio per i concorsi, utile sempre."))
    else:
        n = len(parole(st))
        if not 60 <= n <= 120:
            avvisi.append(("statement", "%d parole, fuori dall'intervallo 60 a 120." % n))
        if (prog.get("destinazione") == "concorso") and abs(n - 100) > 10:
            avvisi.append(("statement", "%d parole: per un concorso stare entro 100 più o meno 10." % n))
        for v in trova(st, VIETATE_TESTI):
            avvisi.append(("statement", "Parola vietata nei testi: %s." % v))

    # didascalie
    precedenti = []
    lunghezze = []
    for ident in ids_tavole:
        im = per_id.get(ident)
        if im is None:
            avvisi.append((ident, "Presente nella sequenza ma assente da immagini."))
            continue
        d = (im.get("didascalia") or "").strip()
        if not d:
            avvisi.append((ident, "Didascalia mancante: ogni immagine dell'edit deve averne una."))
            precedenti.append([])
            continue
        p = parole(d)
        lunghezze.append(len(p))
        if registro == "muto":
            if len(p) > 8:
                avvisi.append((ident, "Registro muto dichiarato ma la didascalia ha %d parole: il muto è luogo e data." % len(p)))
        elif registro == "descrittivo":
            if len(p) < 15:
                avvisi.append((ident, "Solo %d parole: nel registro descrittivo il lettore si aspetta una frase compiuta." % len(p)))
            if len(p) > 50:
                avvisi.append((ident, "%d parole, oltre le 50: nel libro diventa un paragrafo e ruba spazio alla fotografia." % len(p)))
        else:
            if len(p) < pmin:
                avvisi.append((ident, "Solo %d parole, sotto il minimo di %d." % (len(p), pmin)))
            if len(p) > pmax:
                avvisi.append((ident, "%d parole, oltre il massimo di %d: non è una didascalia, è un testo." % (len(p), pmax)))
        for v in trova(d, VALUTATIVI):
            avvisi.append((ident, "Aggettivo valutativo: %s. La didascalia non giudica." % v))
        for v in trova(d, GIUDIZI):
            avvisi.append((ident, "Giudizio da photo editor in una didascalia da pubblicare: \"%s\". Il lettore del libro non deve leggere la tua valutazione: spostala nella descrizione." % v))
        if registro != "descrittivo":
            for v in trova(d, DESCRITTIVI):
                avvisi.append((ident, "Descrive quello che si vede: %s. Il lettore vede già." % v))
        if "?" in d:
            avvisi.append((ident, "Domanda retorica in didascalia."))
        for sp in re.findall(r"\[([^\]]+)\]", d):
            segnaposto.append((ident, sp))
        # le ripetizioni si controllano solo fuori dal registro muto: nel muto la
        # forma "luogo, data" è identica per costruzione, ed è giusto che lo sia.
        # la coda "luogo, giorno mese anno" è identica per costruzione in molti
        # registri: escluderla evita di segnalare ripetizioni che sono la forma.
        senza_segnaposto = re.sub(r"\[[^\]]*\]", " ", d)
        pieno = [w for w in parole(senza_segnaposto)
                 if w not in STOPWORD and len(w) > 3 and w not in MESI
                 and not re.fullmatch(r"\d{4}", w)]
        if registro != "muto":
            if precedenti and precedenti[-1] and p and precedenti[-1][0] == p[0]:
                avvisi.append((ident, "Comincia con la stessa parola della didascalia precedente: %s." % p[0]))
            if precedenti:
                comuni = set(pieno) & set(precedenti[-1])
                if len(comuni) >= 2:
                    avvisi.append((ident, "Ripete con la precedente: %s." % ", ".join(sorted(comuni)[:3])))
        precedenti.append(pieno)

    if len(lunghezze) >= 5 and registro != "muto":
        media = sum(lunghezze) / len(lunghezze)
        var = sum((x - media) ** 2 for x in lunghezze) / len(lunghezze)
        if var < 1.0:
            avvisi.append(("didascalie", "Tutte della stessa lunghezza (media %.1f parole, varianza %.2f): la voce suona meccanica." % (media, var)))

    # sequenza: copertina e ragioni del ritmo, obbligatorie quando c'e' un ordine
    seq = dati.get("sequenza") or {}
    if seq.get("spread"):
        if not prog.get("copertina"):
            avvisi.append(("copertina", "Nessuna copertina proposta. Va sempre indicata, ed e' una scelta distinta dall'apertura."))
        elif not prog.get("copertina_motivazione"):
            avvisi.append(("copertina", "Copertina indicata senza motivazione: perche' questa e non l'apertura?"))
        if len(prog.get("copertina_alternative") or []) < 2:
            avvisi.append(("copertina", "Servono almeno due alternative di copertina, ciascuna col motivo per cui perde."))
        if prog.get("copertina") and prog["copertina"] not in per_id:
            avvisi.append(("copertina", "La copertina %s non esiste fra le immagini." % prog["copertina"]))
        if not seq.get("ritmo"):
            avvisi.append(("ritmo", "Manca la stringa del ritmo in sequenza.ritmo."))
        else:
            codici = seq["ritmo"].split()
            attesi = len(seq["spread"])
            reali = [c for c in codici if c != "|"]
            if len(reali) != attesi:
                avvisi.append(("ritmo", "%d codici di ritmo per %d spread: devono corrispondere." % (len(reali), attesi)))
            if reali and reali[-1][0] == "M":
                avvisi.append(("ritmo", "L'ultimo spread e' M: le chiusure funzionano in alto (A) o in basso (B), mai a meta'."))
            for k in range(len(reali) - 2):
                if reali[k][0] == reali[k+1][0] == reali[k+2][0] == "A":
                    avvisi.append(("ritmo", "Tre A di fila agli spread %d, %d, %d: dal terzo picco il lettore non sente piu' i picchi." % (k+1, k+2, k+3)))
        if not seq.get("ritmo_perche"):
            avvisi.append(("ritmo", "Manca sequenza.ritmo_perche: la forma va motivata a partire dal materiale, non dal gusto."))
        if len(seq.get("alternative") or []) < 2:
            avvisi.append(("ritmo", "Servono da due a tre alternative di sequenza scartate, con la loro stringa e il motivo."))
        multi = sum(1 for c in seq["spread"] for pag in c if isinstance(pag, list) and len(pag) > 1)
        if multi and multi > max(1, len(seq["spread"]) // 4):
            avvisi.append(("sequenza", "%d pagine con piu' immagini su %d spread: se sono la norma non e' un libro, e' un provino stampato." % (multi, len(seq["spread"]))))

    # descrizioni: valgono per OGNI immagine analizzata, non solo per quelle dell'edit
    viste_desc = {}
    for im in dati.get("immagini") or []:
        ident = im["id"]
        d = (im.get("descrizione") or "").strip()
        if not d:
            avvisi.append((ident, "Descrizione mancante. Ogni immagine sottoposta deve averne una: cosa si vede e cosa fa fotograficamente."))
            continue
        n = len(parole(d))
        if n < 30:
            avvisi.append((ident, "Descrizione di %d parole: sotto le 30 non arriva al significato fotografico, si ferma all'inventario." % n))
        elif n > 100:
            avvisi.append((ident, "Descrizione di %d parole: oltre le 100 diventa una scheda critica, e quella sta altrove." % n))
        chiave = re.sub(r"\W+", " ", d.lower()).strip()
        if chiave in viste_desc:
            avvisi.append((ident, "Descrizione identica a quella di %s." % viste_desc[chiave]))
        else:
            viste_desc[chiave] = ident

    if registro != "muto":
        visti = {}
        for ident in ids_tavole:
            t = ((per_id.get(ident) or {}).get("didascalia") or "").strip().lower()
            chiave = re.sub(r"\[[^\]]*\]", "", t).strip()
            if not chiave:
                continue
            if chiave in visti:
                avvisi.append((ident, "Didascalia identica a quella di %s." % visti[chiave]))
            else:
                visti[chiave] = ident
    return avvisi, segnaposto


def scrivi(dati, ids_tavole, fonte_ordine, avvisi, segnaposto, percorso):
    prog = dati.get("progetto") or {}
    per_id = {i["id"]: i for i in dati.get("immagini") or []}
    R = []
    R.append("# Testi del progetto\n")
    R.append("Generato da `genera_testi.py`. I segnaposto fra parentesi quadre vanno")
    R.append("compilati dall'autore: nessun dato di fatto è stato inventato.\n")

    R.append("## Titolo\n")
    R.append("**%s**%s\n" % (prog.get("titolo", "senza titolo"),
                            (", " + prog["sottotitolo"]) if prog.get("sottotitolo") else ""))
    cand = prog.get("titoli_candidati") or []
    if cand:
        R.append("| candidato | registro | perché |")
        R.append("|---|---|---|")
        for c in cand:
            R.append("| %s | %s | %s |" % (c.get("titolo", ""), c.get("registro", ""),
                                           c.get("motivazione", "")))
        R.append("")

    if prog.get("introduzione"):
        R.append("## Introduzione\n")
        if prog.get("registro_introduzione"):
            R.append("Registro: %s. Parole: %d.\n" % (prog["registro_introduzione"],
                                                      len(parole(prog["introduzione"]))))
        R.append(prog["introduzione"].strip() + "\n")

    if prog.get("nota_autore"):
        R.append("## Nota dell'autore\n")
        R.append(prog["nota_autore"].strip() + "\n")

    if prog.get("statement"):
        R.append("## Statement, %d parole\n" % len(parole(prog["statement"])))
        R.append(prog["statement"].strip() + "\n")

    R.append("## Didascalie\n")
    R.append("Registro dichiarato: **%s**. Ordine: %s. Tavole: %d.\n" % (
        prog.get("registro_didascalie") or "non dichiarato", fonte_ordine, len(ids_tavole)))
    for n, ident in enumerate(ids_tavole, 1):
        im = per_id.get(ident) or {}
        R.append("**Tavola %d** (%s, `%s`)  " % (n, ident, im.get("file", "")))
        R.append("%s\n" % (im.get("didascalia") or "_manca_"))

    con_desc = [i for i in (dati.get("immagini") or []) if (i.get("descrizione") or "").strip()]
    if con_desc:
        R.append("## Descrizioni\n")
        R.append("Cosa si vede e cosa fa fotograficamente. Una per ogni immagine analizzata, "
                 "%d su %d.\n" % (len(con_desc), len(dati.get("immagini") or [])))
        for im in sorted(con_desc, key=lambda x: x["id"]):
            R.append("**%s** (`%s`)  " % (im["id"], im.get("file", "")))
            R.append("%s\n" % im["descrizione"].strip())

    if segnaposto:
        R.append("## Segnaposto da compilare, %d\n" % len(segnaposto))
        for ident, sp in segnaposto:
            R.append("- %s: `[%s]`" % (ident, sp))
        R.append("")

    R.append("## Referto del controllo automatico\n")
    if not avvisi:
        R.append("Nessun avviso.\n")
    else:
        R.append("%d avvisi. Non sono errori bloccanti: sono i punti da guardare.\n" % len(avvisi))
        R.append("| dove | avviso |")
        R.append("|---|---|")
        for dove, msg in avvisi:
            R.append("| %s | %s |" % (dove, msg))
        R.append("")

    with open(percorso, "w", encoding="utf-8") as fh:
        fh.write("\n".join(R))


def main():
    ap = argparse.ArgumentParser(description="Raccoglie e controlla titoli, introduzione, statement e didascalie.")
    ap.add_argument("analisi")
    ap.add_argument("-o", "--uscita", default=None)
    ap.add_argument("--solo-controllo", action="store_true", help="stampa il referto e non scrive testi.md")
    ap.add_argument("--parole-min", type=int, default=5)
    ap.add_argument("--parole-max", type=int, default=25)
    args = ap.parse_args()

    percorso = os.path.abspath(os.path.expanduser(args.analisi))
    with open(percorso, encoding="utf-8") as fh:
        dati = json.load(fh)
    ids, fonte = ordine_tavole(dati)
    if not ids:
        sys.exit("analisi.json non contiene immagini.")
    avvisi, segnaposto = controlla(dati, ids, args.parole_min, args.parole_max)

    print("Ordine delle tavole: %s (%d immagini)" % (fonte, len(ids)))
    print("Segnaposto aperti: %d" % len(segnaposto))
    print("Avvisi: %d" % len(avvisi))
    for dove, msg in avvisi:
        print("  [%s] %s" % (dove, msg))
    if not avvisi:
        print("  nessuno")

    if not args.solo_controllo:
        out = os.path.abspath(os.path.expanduser(
            args.uscita or os.path.join(os.path.dirname(percorso) or ".", "testi.md")))
        scrivi(dati, ids, fonte, avvisi, segnaposto, out)
        print("\nScritto: %s" % out)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
