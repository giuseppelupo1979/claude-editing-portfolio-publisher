#!/usr/bin/env python3
"""
genera_dummy_pdf.py: costruisce il dummy (menabo') del libro in PDF.

Legge analisi.json, metriche.json e le miniature e impagina una pagina PDF per ogni
doppia pagina del libro, cosi' come il lettore la vedra': copertina, frontespizio,
introduzione, spread, statement, schede delle tavole, attrezzatura EXIF e colophon.

Le pagine bianche dichiarate come null nella sequenza restano bianche: sono parte del
progetto, non un errore.

Uso:
  python3 genera_dummy_pdf.py analisi.json [-o dummy.pdf] [--radice CARTELLA]
        [--pagina 21x26] [--dpi 150] [--senza-didascalie] [--copertina P003]
        [--metriche metriche.json]

Nota: le miniature sono a bassa risoluzione, quindi il dummy serve a valutare
sequenza, ritmo e respiro, non la qualita' di stampa.
"""

import argparse
import json
import os
import sys
from datetime import date

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Serve Pillow: pip install pillow --break-system-packages")

Image.MAX_IMAGE_PIXELS = None

SERIF = ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
         "/System/Library/Fonts/Supplemental/Georgia.ttf"]
SERIF_B = ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
           "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
           "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"]
SANS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]

CARTA = (243, 241, 237)
INCHIOSTRO = (26, 26, 26)
TENUE = (122, 120, 116)


def font(elenco, dim):
    for p in elenco:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, dim)
            except Exception:
                pass
    return ImageFont.load_default()


def a_capo(testo, fnt, largh, disegno):
    parole, righe, corrente = testo.split(), [], ""
    for p in parole:
        prova = (corrente + " " + p).strip()
        if disegno.textlength(prova, font=fnt) <= largh:
            corrente = prova
        else:
            if corrente:
                righe.append(corrente)
            corrente = p
    if corrente:
        righe.append(corrente)
    return righe


def scrivi_paragrafo(d, xy, testo, fnt, largh, colore, interlinea=1.5, allineamento="sx"):
    x, y = xy
    righe = a_capo(testo, fnt, largh, d)
    passo = int(fnt.size * interlinea)
    for r in righe:
        dx = 0
        if allineamento == "centro":
            dx = (largh - d.textlength(r, font=fnt)) / 2
        d.text((x + dx, y), r, font=fnt, fill=colore)
        y += passo
    return y


class Libro:
    def __init__(self, larghezza_cm, altezza_cm, dpi):
        self.pw = int(larghezza_cm / 2.54 * dpi)
        self.ph = int(altezza_cm / 2.54 * dpi)
        self.dpi = dpi
        self.margine = int(self.pw * 0.10)
        self.piega = int(self.pw * 0.06)
        self.f_titolo = font(SERIF_B, int(self.pw * 0.085))
        self.f_sotto = font(SERIF, int(self.pw * 0.038))
        self.f_testo = font(SERIF, int(self.pw * 0.030))
        self.f_didasc = font(SANS, int(self.pw * 0.019))
        self.f_mini = font(SANS, int(self.pw * 0.016))
        self.pagine = []

    def nuova(self):
        tela = Image.new("RGB", (self.pw * 2, self.ph), CARTA)
        d = ImageDraw.Draw(tela)
        for k in range(14):
            alfa = int(16 - k)
            if alfa <= 0:
                break
            d.line([(self.pw - k, 0), (self.pw - k, self.ph)], fill=(
                CARTA[0] - alfa, CARTA[1] - alfa, CARTA[2] - alfa))
            d.line([(self.pw + k, 0), (self.pw + k, self.ph)], fill=(
                CARTA[0] - alfa, CARTA[1] - alfa, CARTA[2] - alfa))
        return tela, d

    def riquadro(self, lato):
        """Restituisce (x0, y0, larghezza, altezza) dello specchio di una pagina."""
        if lato == "sx":
            x0 = self.margine
            largh = self.pw - self.margine - self.piega
        else:
            x0 = self.pw + self.piega
            largh = self.pw - self.margine - self.piega
        return x0, self.margine, largh, self.ph - 2 * self.margine

    def posa(self, tela, d, percorso, lato, didascalia, ident, con_didasc,
             quante=1, indice=0):
        x0, y0, largh, alt = self.riquadro(lato)
        alt = alt // quante
        y0 = y0 + alt * indice
        area_h = int(alt * (0.84 if con_didasc else 0.94))
        try:
            with Image.open(percorso) as im:
                im = im.convert("RGB")
                im.thumbnail((largh, area_h), Image.LANCZOS)
                foto = im.copy()
        except Exception as e:
            d.text((x0, y0), "immagine non leggibile: %s" % e, font=self.f_mini, fill=TENUE)
            return
        ix = x0 + (largh - foto.width) // 2
        iy = y0 + (area_h - foto.height) // 2
        ombra = int(self.pw * 0.004)
        d.rectangle([ix + ombra, iy + ombra, ix + foto.width + ombra, iy + foto.height + ombra],
                    fill=(226, 224, 220))
        tela.paste(foto, (ix, iy))
        if con_didasc:
            testo = didascalia or ""
            y = iy + foto.height + int(self.ph * 0.022)
            if testo:
                scrivi_paragrafo(d, (x0, y), testo, self.f_didasc, largh, TENUE, 1.45)
            else:
                d.text((x0, y), ident, font=self.f_mini, fill=(198, 196, 192))

    def copertina(self, prog, percorso_cop):
        tela, d = self.nuova()
        x0, y0, largh, alt = self.riquadro("dx")
        y = scrivi_paragrafo(d, (x0, y0), prog.get("titolo", "senza titolo"),
                             self.f_titolo, largh, INCHIOSTRO, 1.15)
        if prog.get("sottotitolo"):
            y = scrivi_paragrafo(d, (x0, y + int(self.ph * 0.012)), prog["sottotitolo"],
                                 self.f_sotto, largh, TENUE, 1.3)
        y_autore = y0 + alt - int(self.f_sotto.size * 1.4)
        alto_area = y_autore - int(self.ph * 0.05) - (y + int(self.ph * 0.04))
        if percorso_cop and os.path.exists(percorso_cop) and alto_area > int(alt * 0.2):
            try:
                with Image.open(percorso_cop) as im:
                    im = im.convert("RGB")
                    im.thumbnail((largh, alto_area), Image.LANCZOS)
                    foto = im.copy()
                oy = y + int(self.ph * 0.04) + (alto_area - foto.height) // 2
                tela.paste(foto, (x0 + (largh - foto.width) // 2, oy))
            except Exception:
                pass
        if prog.get("autore"):
            d.text((x0, y_autore), prog["autore"], font=self.f_sotto, fill=INCHIOSTRO)
        d.text((self.margine, self.ph - self.margine + int(self.ph * 0.01)),
               "dummy, quarta di copertina", font=self.f_mini, fill=(214, 212, 208))
        self.pagine.append(tela)

    def frontespizio(self, prog):
        tela, d = self.nuova()
        x0, y0, largh, alt = self.riquadro("dx")
        y = y0 + int(alt * 0.30)
        y = scrivi_paragrafo(d, (x0, y), prog.get("titolo", ""), self.f_titolo, largh, INCHIOSTRO, 1.15)
        if prog.get("sottotitolo"):
            y = scrivi_paragrafo(d, (x0, y + int(self.ph * 0.01)), prog["sottotitolo"],
                                 self.f_sotto, largh, TENUE, 1.3)
        if prog.get("autore"):
            scrivi_paragrafo(d, (x0, y + int(self.ph * 0.05)), prog["autore"],
                             self.f_sotto, largh, INCHIOSTRO, 1.3)
        self.pagine.append(tela)

    def spread(self, sx, dx, per_id, base, con_didasc, numero, usa_descrizione=False):
        tela, d = self.nuova()
        for lato, val in (("sx", sx), ("dx", dx)):
            if not val:
                continue
            identi = val if isinstance(val, list) else [val]
            for k, ident in enumerate(identi):
                im = per_id.get(ident)
                if not im:
                    continue
                rel = im.get("thumb") or im.get("file")
                p = rel if os.path.isabs(rel) else os.path.join(base, rel)
                testo = im.get("descrizione", "") if usa_descrizione else im.get("didascalia", "")
                self.posa(tela, d, p, lato, testo, ident, con_didasc, len(identi), k)
        d.text((self.margine, self.ph - self.margine + int(self.ph * 0.012)),
               "%d" % (numero * 2), font=self.f_mini, fill=(206, 204, 200))
        larg_num = d.textlength("%d" % (numero * 2 + 1), font=self.f_mini)
        d.text((self.pw * 2 - self.margine - larg_num, self.ph - self.margine + int(self.ph * 0.012)),
               "%d" % (numero * 2 + 1), font=self.f_mini, fill=(206, 204, 200))
        self.pagine.append(tela)

    def testo_pagina(self, titolo, corpo, lato="dx"):
        tela, d = self.nuova()
        x0, y0, largh, alt = self.riquadro(lato)
        y = y0 + int(alt * 0.16)
        if titolo:
            y = scrivi_paragrafo(d, (x0, y), titolo, self.f_sotto, largh, INCHIOSTRO, 1.4) + int(self.ph * 0.02)
        scrivi_paragrafo(d, (x0, y), corpo, self.f_testo, largh, INCHIOSTRO, 1.62)
        self.pagine.append(tela)

    def testo_lungo(self, titolo, corpo):
        """Distribuisce un testo lungo su pagine affiancate senza tagliarlo."""
        if not corpo:
            return
        prova, disegno = self.nuova()
        _, _, largh, alt = self.riquadro("sx")
        righe = a_capo(corpo, self.f_testo, largh, disegno)
        passo = int(self.f_testo.size * 1.62)
        capienza = max(8, int((alt - self.f_sotto.size * 3.2) / passo))
        blocchi = [righe[i:i + capienza] for i in range(0, len(righe), capienza)]
        for indice in range(0, len(blocchi), 2):
            tela, d = self.nuova()
            for offset, lato in enumerate(("sx", "dx")):
                n = indice + offset
                if n >= len(blocchi):
                    continue
                x0, y0, largh, _ = self.riquadro(lato)
                etichetta = titolo if n == 0 else titolo + " (continua)"
                d.text((x0, y0), etichetta, font=self.f_sotto, fill=INCHIOSTRO)
                y = y0 + int(self.f_sotto.size * 2.2)
                for riga in blocchi[n]:
                    d.text((x0, y), riga, font=self.f_testo, fill=INCHIOSTRO)
                    y += passo
            self.pagine.append(tela)

    def indice(self, voci):
        per_pagina = max(8, int((self.ph - 2 * self.margine) / (self.f_didasc.size * 2.1)))
        blocchi = [voci[i:i + per_pagina * 2] for i in range(0, len(voci), per_pagina * 2)]
        for blocco in blocchi:
            tela, d = self.nuova()
            meta = (len(blocco) + 1) // 2
            for lato, gruppo in (("sx", blocco[:meta]), ("dx", blocco[meta:])):
                x0, y0, largh, _ = self.riquadro(lato)
                y = y0
                if lato == "sx" and blocco is blocchi[0]:
                    d.text((x0, y), "Tavole", font=self.f_sotto, fill=INCHIOSTRO)
                    y += int(self.f_sotto.size * 2.2)
                for v in gruppo:
                    y = scrivi_paragrafo(d, (x0, y), v, self.f_didasc, largh, INCHIOSTRO, 1.45)
                    y += int(self.f_didasc.size * 0.55)
            self.pagine.append(tela)

    def schede_tavole(self, voci):
        """Una scheda per pagina: titolo, file, descrizione e didascalia."""
        for inizio in range(0, len(voci), 2):
            tela, d = self.nuova()
            for offset, lato in enumerate(("sx", "dx")):
                indice = inizio + offset
                if indice >= len(voci):
                    continue
                voce = voci[indice]
                x0, y0, largh, _ = self.riquadro(lato)
                titolo = "%d. %s" % (indice + 1, voce.get("titolo") or voce.get("file") or voce["id"])
                y = scrivi_paragrafo(d, (x0, y0), titolo, self.f_sotto,
                                     largh, INCHIOSTRO, 1.3)
                if voce.get("file"):
                    d.text((x0, y + int(self.ph * 0.008)), voce["file"],
                           font=self.f_mini, fill=TENUE)
                    y += int(self.f_mini.size * 2.2)
                if voce.get("descrizione"):
                    y = scrivi_paragrafo(d, (x0, y), voce["descrizione"], self.f_testo,
                                         largh, INCHIOSTRO, 1.52)
                    y += int(self.ph * 0.018)
                if voce.get("didascalia"):
                    d.text((x0, y), "Didascalia", font=self.f_mini, fill=TENUE)
                    y += int(self.f_mini.size * 1.6)
                    scrivi_paragrafo(d, (x0, y), voce["didascalia"], self.f_didasc,
                                     largh, TENUE, 1.45)
            self.pagine.append(tela)

    def salva(self, percorso):
        if not self.pagine:
            sys.exit("Nessuna pagina generata.")
        prima, resto = self.pagine[0], self.pagine[1:]
        prima.save(percorso, "PDF", resolution=self.dpi, save_all=True, append_images=resto)


def main():
    ap = argparse.ArgumentParser(description="Dummy del libro in PDF da analisi.json")
    ap.add_argument("analisi")
    ap.add_argument("-o", "--uscita", default=None)
    ap.add_argument("--radice", default=None)
    ap.add_argument("--pagina", default="21x26", help="larghezza x altezza in cm della singola pagina")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--senza-didascalie", action="store_true")
    ap.add_argument("--con-descrizioni", action="store_true",
                    help="usa la descrizione al posto della didascalia: menabo' di lavoro, non da stampa")
    ap.add_argument("--copertina", default=None, help="id dell'immagine di copertina")
    ap.add_argument("--metriche", default=None,
                    help="metriche.json per ricavare l'attrezzatura EXIF")
    args = ap.parse_args()

    percorso = os.path.abspath(os.path.expanduser(args.analisi))
    with open(percorso, encoding="utf-8") as fh:
        dati = json.load(fh)
    base = os.path.abspath(os.path.expanduser(args.radice or os.path.dirname(percorso) or "."))
    prog = dati.get("progetto") or {}
    per_id = {i["id"]: i for i in dati.get("immagini") or []}
    if not per_id:
        sys.exit("analisi.json non contiene immagini.")

    try:
        lw, lh = [float(x) for x in args.pagina.lower().replace(",", ".").split("x")]
    except Exception:
        sys.exit("Formato pagina non valido, esempio: --pagina 21x26")

    sequenza = (dati.get("sequenza") or {}).get("spread")
    if not sequenza:
        ordinati = sorted(per_id.values(), key=lambda i: i["id"])
        sequenza = [[None, ordinati[0]["id"]]] if ordinati else []
        resto = [i["id"] for i in ordinati[1:]]
        for k in range(0, len(resto), 2):
            sequenza.append([resto[k], resto[k + 1] if k + 1 < len(resto) else None])
        print("Nessuna sequenza in analisi.json: impaginato in ordine di id, da rivedere.")

    id_cop = args.copertina or prog.get("copertina")
    percorso_cop = None
    if id_cop and id_cop in per_id:
        rel = per_id[id_cop].get("thumb") or per_id[id_cop].get("file")
        percorso_cop = rel if os.path.isabs(rel) else os.path.join(base, rel)

    usate = []
    for c in sequenza:
        for pag in c:
            if pag:
                usate.extend(pag if isinstance(pag, list) else [pag])

    libro = Libro(lw, lh, args.dpi)
    libro.copertina(prog, percorso_cop)
    libro.frontespizio(prog)
    introduzione = prog.get("introduzione")
    posizione_intro = prog.get("introduzione_posizione", "prima")
    if introduzione and posizione_intro == "prima":
        libro.testo_lungo("Introduzione", introduzione)
    for n, coppia in enumerate(sequenza, 1):
        sx, dx = (list(coppia) + [None, None])[:2]
        libro.spread(sx, dx, per_id, base, not args.senza_didascalie, n, args.con_descrizioni)
    if introduzione and posizione_intro != "prima":
        libro.testo_lungo("Introduzione", introduzione)
    if prog.get("statement"):
        libro.testo_lungo("Statement", prog["statement"])
    if prog.get("nota_autore"):
        libro.testo_lungo("Nota dell'autore", prog["nota_autore"])
    voci = []
    for k, ident in enumerate(usate, 1):
        im = per_id.get(ident, {})
        pezzi = [str(k) + ".", im.get("titolo") or im.get("file", ident)]
        if im.get("didascalia"):
            pezzi.append("(" + im["didascalia"][:70] + ")")
        voci.append(" ".join(pezzi))
    if voci:
        libro.indice(voci)

    tavole = [per_id[ident] for ident in usate if ident in per_id]
    if tavole:
        libro.schede_tavole(tavole)

    metriche_path = os.path.abspath(os.path.expanduser(
        args.metriche or os.path.join(os.path.dirname(percorso), "metriche.json")))
    attrezzatura = attrezzatura_exif(metriche_path, tavole)
    libro.testo_lungo("Attrezzatura", attrezzatura)

    colophon = []
    if prog.get("titolo"):
        colophon.append("Titolo: " + prog["titolo"] + ".")
    if prog.get("autore"):
        colophon.append("Autore: " + prog["autore"] + ".")
    colophon.append("Dummy editoriale generato il %s." % date.today().isoformat())
    colophon.append("Formato pagina: %sx%s cm; risoluzione dummy: %s dpi." % (lw, lh, args.dpi))
    colophon.append(attrezzatura)
    colophon.append("Le immagini del dummy possono provenire da miniature e non sono file di stampa.")
    libro.testo_lungo("Colophon", " ".join(colophon))

    out = os.path.abspath(os.path.expanduser(
        args.uscita or os.path.join(os.path.dirname(percorso) or ".", "dummy.pdf")))
    libro.salva(out)
    pagine_libro = len(libro.pagine) * 2
    print("Scritto: %s" % out)
    print("Spread impaginati: %d, pagine interne: %d" % (len(sequenza), pagine_libro))
    if pagine_libro % 4:
        print("Attenzione: %d pagine non e' multiplo di 4. In segnatura diventerebbe %d o %d."
              % (pagine_libro, pagine_libro - pagine_libro % 4, pagine_libro + (4 - pagine_libro % 4)))
    bianche = sum(1 for c in sequenza for x in c if not x)
    print("Pagine bianche dichiarate: %d" % bianche)
    if bianche == 0:
        print("Nessun respiro: verifica se e' voluto.")


def attrezzatura_exif(metriche_path, tavole):
    """Raccoglie solo i dati EXIF presenti per le immagini effettivamente usate."""
    if not os.path.exists(metriche_path):
        return "Attrezzatura non determinabile: metriche.json non disponibile."
    try:
        with open(metriche_path, encoding="utf-8") as fh:
            documento = json.load(fh)
    except Exception as exc:
        return "Attrezzatura non determinabile: metriche.json non leggibile (%s)." % exc

    righe = documento.get("immagini") if isinstance(documento, dict) else documento
    if not isinstance(righe, list):
        return "Attrezzatura non determinabile: struttura di metriche.json non valida."
    per_file = {r.get("file"): r for r in righe if isinstance(r, dict) and r.get("file")}
    selezionate = [per_file.get(t.get("file")) for t in tavole]
    selezionate = [r for r in selezionate if r]
    corpi = sorted({r.get("corpo") for r in selezionate if r.get("corpo")})
    ottiche = sorted({r.get("ottica") for r in selezionate if r.get("ottica")})
    focali = sorted({r.get("focale") for r in selezionate if isinstance(r.get("focale"), (int, float))})
    equivalenti = sorted({r.get("focale_equivalente") for r in selezionate
                          if isinstance(r.get("focale_equivalente"), (int, float))})
    parti = ["Dati EXIF disponibili per %d tavole su %d." % (len(selezionate), len(tavole))]
    parti.append("Corpi: %s." % (", ".join(corpi) if corpi else "non determinabili"))
    parti.append("Ottiche: %s." % (", ".join(ottiche) if ottiche else "non determinabili"))
    parti.append("Focali registrate: %s." % (
        ", ".join("%g mm" % valore for valore in focali) if focali else "non determinabili"))
    parti.append("Focali equivalenti: %s." % (
        ", ".join("%g mm" % valore for valore in equivalenti) if equivalenti else "non determinabili"))
    return " ".join(parti)


if __name__ == "__main__":
    main()
