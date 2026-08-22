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
import hashlib
import json
import os
import sys
from collections import Counter
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
        self.f_sezione = font(SERIF_B, int(self.pw * 0.028))
        self.f_testo = font(SERIF, int(self.pw * 0.030))
        self.f_didasc = font(SANS, int(self.pw * 0.019))
        self.f_mini = font(SANS, int(self.pw * 0.016))
        self.pagine = []
        self.overflow = []

    def controlla_overflow(self, sezione, lato, y):
        limite = self.ph - self.margine
        if y > limite:
            self.overflow.append({
                "sezione": sezione,
                "lato": lato,
                "oltre_px": int(y - limite),
            })

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
                fine = scrivi_paragrafo(d, (x0, y), testo, self.f_didasc, largh, TENUE, 1.45)
                self.controlla_overflow("didascalia " + ident, lato, fine)
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
        self.controlla_overflow("copertina", "dx", y)
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
            y = scrivi_paragrafo(d, (x0, y + int(self.ph * 0.05)), prog["autore"],
                                 self.f_sotto, largh, INCHIOSTRO, 1.3)
        self.controlla_overflow("frontespizio", "dx", y)
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
        y = scrivi_paragrafo(d, (x0, y), corpo, self.f_testo, largh, INCHIOSTRO, 1.62)
        self.controlla_overflow(titolo or "testo", lato, y)
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

    def sezioni_puntate(self, titolo, sezioni):
        """Impagina sezioni tematiche con voci puntate, distribuendole sullo spread."""
        sezioni = [(nome, list(voci)) for nome, voci in sezioni if voci]
        if not sezioni:
            return
        _, prova = self.nuova()
        _, _, largh, alt = self.riquadro("sx")
        rientro = int(self.pw * 0.028)
        passo = int(self.f_testo.size * 1.52)
        passo_titolo = int(self.f_sotto.size * 1.45)
        passo_sezione = int(self.f_sezione.size * 1.45)
        spazio_sezione = int(self.ph * 0.022)
        spazio_voce = int(self.ph * 0.010)

        spazio_nome = int(self.ph * 0.010)
        spazio_titolo = passo_titolo + int(self.ph * 0.035)

        def riserva_titolo(numero_colonna):
            return spazio_titolo if numero_colonna == 0 or numero_colonna % 2 == 0 else 0

        def altezza_blocco(blocco):
            return (len(blocco["righe_nome"]) * passo_sezione + spazio_nome
                    + sum(len(voce["righe"]) * passo + spazio_voce
                          for voce in blocco["voci"])
                    + spazio_sezione)

        # Ogni colonna contiene blocchi gia' spezzati. Anche una singola sezione
        # molto lunga continua quindi nella pagina successiva senza perdere voci.
        colonne = [[]]
        usati = [riserva_titolo(0)]

        def nuova_colonna():
            colonne.append([])
            usati.append(riserva_titolo(len(colonne) - 1))

        for nome, voci in sezioni:
            in_attesa = []
            for voce in voci:
                righe = a_capo(str(voce), self.f_testo, largh - rientro, prova) or [""]
                in_attesa.append({"righe": righe, "mostra_punto": True})
            continua = False

            while in_attesa:
                etichetta = nome + " (continua)" if continua else nome
                righe_nome = a_capo(etichetta, self.f_sezione, largh, prova) or [etichetta]
                base = len(righe_nome) * passo_sezione + spazio_nome + spazio_sezione
                disponibile = alt - usati[-1] - base

                # Se la sezione intera entra nella pagina successiva, spostala
                # prima di spezzarla. Mantiene compatti i gruppi brevi del colophon.
                altezza_intera = base + sum(
                    len(voce["righe"]) * passo + spazio_voce for voce in in_attesa
                )
                indice_successivo = len(colonne)
                capienza_successiva = alt - riserva_titolo(indice_successivo)
                if (not continua and colonne[-1]
                        and altezza_intera > alt - usati[-1]
                        and altezza_intera <= capienza_successiva):
                    nuova_colonna()
                    continue

                # Non lasciare un'intestazione orfana in fondo alla pagina.
                minimo_voce = passo + spazio_voce
                if disponibile < minimo_voce and colonne[-1]:
                    nuova_colonna()
                    continua = True
                    continue

                blocco = {"righe_nome": righe_nome, "voci": []}
                while in_attesa and disponibile >= minimo_voce:
                    voce = in_attesa[0]
                    altezza_voce = len(voce["righe"]) * passo + spazio_voce
                    if altezza_voce <= disponibile:
                        blocco["voci"].append(voce)
                        disponibile -= altezza_voce
                        in_attesa.pop(0)
                        continue

                    # Caso raro: una singola voce e' piu' lunga di una pagina.
                    # La si divide per righe, mantenendo il punto solo all'inizio.
                    quante_righe = int((disponibile - spazio_voce) / passo)
                    if quante_righe > 0:
                        blocco["voci"].append({
                            "righe": voce["righe"][:quante_righe],
                            "mostra_punto": voce["mostra_punto"],
                        })
                        voce["righe"] = voce["righe"][quante_righe:]
                        voce["mostra_punto"] = False
                    break

                # Con titoli eccezionalmente lunghi, garantisce comunque
                # avanzamento ed evita un ciclo infinito.
                if not blocco["voci"]:
                    voce = in_attesa[0]
                    blocco["voci"].append({
                        "righe": voce["righe"][:1],
                        "mostra_punto": voce["mostra_punto"],
                    })
                    voce["righe"] = voce["righe"][1:]
                    voce["mostra_punto"] = False
                    if not voce["righe"]:
                        in_attesa.pop(0)

                colonne[-1].append(blocco)
                usati[-1] += altezza_blocco(blocco)
                if in_attesa:
                    nuova_colonna()
                    continua = True

        # Nei progetti brevi usa entrambe le pagine dello spread e bilancia i
        # gruppi, senza spezzare una sezione che gia' entra per intero.
        if len(colonne) == 1 and len(colonne[0]) > 1:
            gruppo = colonne[0]
            altezze = [altezza_blocco(blocco) for blocco in gruppo]
            taglio = min(
                range(1, len(gruppo)),
                key=lambda n: abs(sum(altezze[:n]) + spazio_titolo - sum(altezze[n:])),
            )
            colonne = [gruppo[:taglio], gruppo[taglio:]]

        for indice in range(0, len(colonne), 2):
            tela, d = self.nuova()
            for offset, lato in enumerate(("sx", "dx")):
                numero_colonna = indice + offset
                if numero_colonna >= len(colonne):
                    continue
                x0, y0, largh, _ = self.riquadro(lato)
                y = y0
                if numero_colonna == 0:
                    d.text((x0, y), titolo, font=self.f_sotto, fill=INCHIOSTRO)
                    y += passo_titolo + int(self.ph * 0.035)
                elif numero_colonna % 2 == 0:
                    d.text((x0, y), titolo + " (continua)", font=self.f_sotto, fill=INCHIOSTRO)
                    y += passo_titolo + int(self.ph * 0.035)
                for blocco in colonne[numero_colonna]:
                    for riga in blocco["righe_nome"]:
                        d.text((x0, y), riga, font=self.f_sezione, fill=INCHIOSTRO)
                        y += passo_sezione
                    y += spazio_nome
                    for voce in blocco["voci"]:
                        if voce["mostra_punto"]:
                            d.text((x0, y), "•", font=self.f_testo, fill=TENUE)
                        for riga in voce["righe"]:
                            d.text((x0 + rientro, y), riga, font=self.f_testo,
                                   fill=INCHIOSTRO)
                            y += passo
                        y += spazio_voce
                    y += spazio_sezione
                self.controlla_overflow(titolo, lato, y)
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
                self.controlla_overflow("indice tavole", lato, y)
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
                if voce.get("place"):
                    luogo = str(voce["place"])
                    if voce.get("lat") is not None and voce.get("lng") is not None:
                        luogo += " (%.6f, %.6f)" % (float(voce["lat"]), float(voce["lng"]))
                    y = scrivi_paragrafo(d, (x0, y), luogo, self.f_mini,
                                         largh, TENUE, 1.35)
                    y += int(self.ph * 0.010)
                if voce.get("descrizione"):
                    y = scrivi_paragrafo(d, (x0, y), voce["descrizione"], self.f_testo,
                                         largh, INCHIOSTRO, 1.52)
                    y += int(self.ph * 0.018)
                if voce.get("didascalia"):
                    d.text((x0, y), "Didascalia", font=self.f_mini, fill=TENUE)
                    y += int(self.f_mini.size * 1.6)
                    y = scrivi_paragrafo(d, (x0, y), voce["didascalia"], self.f_didasc,
                                         largh, TENUE, 1.45)
                self.controlla_overflow("scheda " + str(voce.get("id", indice + 1)), lato, y)
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
    ap.add_argument("--qa-output", default=None,
                    help="manifest QA; predefinito: dummy.qa.json accanto al PDF")
    ap.add_argument("--qa-strict", action="store_true",
                    help="termina con errore se rileva overflow o pagine PDF incoerenti")
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
    sezioni_qa = []

    def impronta_file(percorso_file):
        if not percorso_file or not os.path.isfile(percorso_file):
            return None
        h = hashlib.sha256()
        with open(percorso_file, "rb") as stream:
            for blocco in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(blocco)
        return h.hexdigest()

    def aggiungi_sezione(nome, contenuto, azione):
        prima = len(libro.pagine)
        azione()
        dopo = len(libro.pagine)
        if dopo == prima:
            return
        impronta = hashlib.sha256(json.dumps(
            contenuto, ensure_ascii=False, sort_keys=True, default=str,
        ).encode("utf-8")).hexdigest()
        sezioni_qa.append({
            "id": nome,
            "sha256": impronta,
            "pdf_pages": [prima + 1, dopo],
            "book_pages": [prima * 2 + 1, dopo * 2],
        })

    aggiungi_sezione("copertina", {
        "progetto": prog,
        "immagine": impronta_file(percorso_cop),
    }, lambda: libro.copertina(prog, percorso_cop))
    aggiungi_sezione("frontespizio", prog,
                     lambda: libro.frontespizio(prog))
    introduzione = prog.get("introduzione")
    posizione_intro = prog.get("introduzione_posizione", "prima")
    if introduzione and posizione_intro == "prima":
        aggiungi_sezione("introduzione-prima", introduzione,
                         lambda: libro.testo_lungo("Introduzione", introduzione))
    for n, coppia in enumerate(sequenza, 1):
        sx, dx = (list(coppia) + [None, None])[:2]
        immagini_spread = []
        for pagina in (sx, dx):
            for ident in (pagina if isinstance(pagina, list) else [pagina]):
                if not ident or ident not in per_id:
                    continue
                immagine = per_id[ident]
                rel = immagine.get("thumb") or immagine.get("file")
                p = rel if os.path.isabs(rel) else os.path.join(base, rel)
                immagini_spread.append({"dati": immagine, "file_sha256": impronta_file(p)})
        aggiungi_sezione("spread-%03d" % n, {
            "pagine": [sx, dx], "immagini": immagini_spread,
            "didascalie": not args.senza_didascalie,
            "descrizioni": args.con_descrizioni,
        }, lambda sx=sx, dx=dx, n=n: libro.spread(
            sx, dx, per_id, base, not args.senza_didascalie, n, args.con_descrizioni
        ))
    if introduzione and posizione_intro != "prima":
        aggiungi_sezione("introduzione-dopo", introduzione,
                         lambda: libro.testo_lungo("Introduzione", introduzione))
    if prog.get("statement"):
        aggiungi_sezione("statement", prog["statement"],
                         lambda: libro.testo_lungo("Statement", prog["statement"]))
    if prog.get("nota_autore"):
        aggiungi_sezione("nota-autore", prog["nota_autore"],
                         lambda: libro.testo_lungo("Nota dell'autore", prog["nota_autore"]))
    voci = []
    for k, ident in enumerate(usate, 1):
        im = per_id.get(ident, {})
        pezzi = [str(k) + ".", im.get("titolo") or im.get("file", ident)]
        if im.get("didascalia"):
            pezzi.append("(" + im["didascalia"][:70] + ")")
        voci.append(" ".join(pezzi))
    if voci:
        aggiungi_sezione("indice", voci, lambda: libro.indice(voci))

    tavole = [per_id[ident] for ident in usate if ident in per_id]
    if tavole:
        aggiungi_sezione("schede-tavole", tavole, lambda: libro.schede_tavole(tavole))

    metriche_path = os.path.abspath(os.path.expanduser(
        args.metriche or os.path.join(os.path.dirname(percorso), "metriche.json")))
    attrezzatura = attrezzatura_sezioni(metriche_path, tavole)
    aggiungi_sezione("attrezzatura", attrezzatura,
                     lambda: libro.sezioni_puntate("Attrezzatura", attrezzatura))

    progetto = []
    if prog.get("titolo"):
        progetto.append("Titolo: " + prog["titolo"] + ".")
    if prog.get("autore"):
        progetto.append("Autore: " + prog["autore"] + ".")
    colophon_predefinito = [
        ("Progetto", progetto),
        ("Edizione", [
            "Tipologia: dummy editoriale.",
            "Data di generazione: %s." % date.today().isoformat(),
        ]),
        ("Specifiche tecniche", [
            "Formato pagina: %sx%s cm." % (lw, lh),
            "Risoluzione del dummy: %s dpi." % args.dpi,
            "Sequenza fotografica: %d spread, %d tavole." % (len(sequenza), len(tavole)),
        ]),
        ("Fonti e limiti", [
            "Immagini: miniature del progetto, non file destinati alla stampa.",
            "Attrezzatura: ricavata esclusivamente dai campi EXIF disponibili in metriche.json.",
            "Uso: valutare sequenza, ritmo, respiro e impaginazione, non la qualità di stampa.",
        ]),
    ]
    colophon_personalizzato = prog.get("colophon")
    if isinstance(colophon_personalizzato, dict):
        colophon = [(str(nome), voci if isinstance(voci, list) else [str(voci)])
                    for nome, voci in colophon_personalizzato.items()]
    elif isinstance(colophon_personalizzato, list):
        colophon = [(str(voce.get("sezione", "Sezione")), voce.get("voci") or [])
                    for voce in colophon_personalizzato if isinstance(voce, dict)]
    else:
        colophon = colophon_predefinito
    aggiungi_sezione("colophon", colophon,
                     lambda: libro.sezioni_puntate("Colophon", colophon))

    out = os.path.abspath(os.path.expanduser(
        args.uscita or os.path.join(os.path.dirname(percorso) or ".", "dummy.pdf")))
    libro.salva(out)
    pagine_libro = len(libro.pagine) * 2
    qa_path = os.path.abspath(os.path.expanduser(
        args.qa_output or os.path.splitext(out)[0] + ".qa.json"))
    precedente = {}
    if os.path.exists(qa_path):
        try:
            with open(qa_path, encoding="utf-8") as stream:
                precedente = json.load(stream)
        except (OSError, json.JSONDecodeError):
            precedente = {}
    vecchie = {sezione.get("id"): sezione for sezione in precedente.get("sections", [])}
    cambiate = []
    pagine_modificate = set()
    for sezione in sezioni_qa:
        vecchia = vecchie.get(sezione["id"])
        if not vecchia or vecchia.get("sha256") != sezione["sha256"] or vecchia.get("pdf_pages") != sezione["pdf_pages"]:
            cambiate.append(sezione["id"])
            pagine_modificate.update(range(sezione["pdf_pages"][0], sezione["pdf_pages"][1] + 1))
    rimosse = sorted(set(vecchie) - {sezione["id"] for sezione in sezioni_qa})
    errori_qa = []
    pdf_pages = len(libro.pagine)
    try:
        from pypdf import PdfReader
        pdf_pages = len(PdfReader(out).pages)
        if pdf_pages != len(libro.pagine):
            errori_qa.append("numero di pagine PDF diverso dagli spread generati")
    except ImportError:
        pass
    qa = {
        "version": 1,
        "pdf_pages": pdf_pages,
        "book_pages": pagine_libro,
        "sections": sezioni_qa,
        "changed_sections": cambiate,
        "removed_sections": rimosse,
        "changed_pdf_pages": sorted(pagine_modificate),
        "overflow": libro.overflow,
        "errors": errori_qa,
        "qa_ok": not libro.overflow and not errori_qa,
    }
    with open(qa_path, "w", encoding="utf-8") as stream:
        json.dump(qa, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print("Scritto: %s" % out)
    print("QA: %s, pagine PDF da ricontrollare: %s" % (
        qa_path, ", ".join(map(str, qa["changed_pdf_pages"])) or "nessuna"))
    print("Spread impaginati: %d, pagine interne: %d" % (len(sequenza), pagine_libro))
    if pagine_libro % 4:
        print("Attenzione: %d pagine non e' multiplo di 4. In segnatura diventerebbe %d o %d."
              % (pagine_libro, pagine_libro - pagine_libro % 4, pagine_libro + (4 - pagine_libro % 4)))
    bianche = sum(1 for c in sequenza for x in c if not x)
    print("Pagine bianche dichiarate: %d" % bianche)
    if bianche == 0:
        print("Nessun respiro: verifica se e' voluto.")
    if args.qa_strict and not qa["qa_ok"]:
        sys.exit("QA dummy fallita: overflow o conteggio pagine incoerente, vedi %s" % qa_path)


def _attrezzatura_dati(metriche_path, tavole):
    """Raccoglie e conta solo i dati EXIF delle immagini effettivamente usate."""
    if not os.path.exists(metriche_path):
        return None, "Attrezzatura non determinabile: metriche.json non disponibile."
    try:
        with open(metriche_path, encoding="utf-8") as fh:
            documento = json.load(fh)
    except Exception as exc:
        return None, "Attrezzatura non determinabile: metriche.json non leggibile (%s)." % exc

    righe = documento.get("immagini") if isinstance(documento, dict) else documento
    if not isinstance(righe, list):
        return None, "Attrezzatura non determinabile: struttura di metriche.json non valida."
    per_file = {r.get("file"): r for r in righe if isinstance(r, dict) and r.get("file")}
    selezionate = [per_file.get(t.get("file")) for t in tavole]
    selezionate = [r for r in selezionate if r]
    return {
        "copertura": len(selezionate),
        "totale": len(tavole),
        "corpi": Counter(r.get("corpo") for r in selezionate if r.get("corpo")),
        "ottiche": Counter(r.get("ottica") for r in selezionate if r.get("ottica")),
        "focali": Counter(r.get("focale") for r in selezionate
                          if isinstance(r.get("focale"), (int, float))),
        "equivalenti": Counter(r.get("focale_equivalente") for r in selezionate
                               if isinstance(r.get("focale_equivalente"), (int, float))),
    }, None


def _uso_tavole(quante):
    return "%d %s" % (quante, "tavola" if quante == 1 else "tavole")


def attrezzatura_sezioni(metriche_path, tavole):
    """Restituisce sezioni e voci pronte per l'impaginazione puntata."""
    dati, errore = _attrezzatura_dati(metriche_path, tavole)
    if errore:
        return [("Disponibilità", [errore])]
    sezioni = [("Copertura EXIF", [
        "Dati disponibili per %d tavole su %d." % (dati["copertura"], dati["totale"])
    ])]
    corpi = ["%s (%s)." % (nome, _uso_tavole(quante))
             for nome, quante in sorted(dati["corpi"].items())]
    sezioni.append(("Corpi macchina", corpi or ["Non determinabili dai dati disponibili."]))
    ottiche = ["%s (%s)." % (nome, _uso_tavole(quante))
               for nome, quante in sorted(dati["ottiche"].items())]
    sezioni.append(("Obiettivi", ottiche or ["Non determinabili dai dati disponibili."]))
    focali = ["%g mm (%s)." % (valore, _uso_tavole(quante))
              for valore, quante in sorted(dati["focali"].items())]
    sezioni.append(("Focali utilizzate", focali or ["Non determinabili dai dati disponibili."]))
    if dati["equivalenti"] and dati["equivalenti"] != dati["focali"]:
        equivalenti = ["%g mm equivalenti (%s)." % (valore, _uso_tavole(quante))
                       for valore, quante in sorted(dati["equivalenti"].items())]
        sezioni.append(("Focali equivalenti", equivalenti))
    return sezioni


def attrezzatura_exif(metriche_path, tavole):
    """Compatibilità testuale: rende le sezioni EXIF come elenco puntato."""
    righe = []
    for nome, voci in attrezzatura_sezioni(metriche_path, tavole):
        righe.append(nome + ":")
        righe.extend("- " + voce for voce in voci)
    return "\n".join(righe)


if __name__ == "__main__":
    main()
