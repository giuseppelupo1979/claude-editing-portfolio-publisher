#!/usr/bin/env python3
"""
prepara_provino.py: primo passo di ogni sessione di editing.

Legge una cartella di immagini e produce:
  thumbs/            miniature con orientamento EXIF applicato
  griglie/           provini a contatto etichettati con gli ID
  metriche.csv/.json misure oggettive, una riga per immagine
  coppie_simili.csv  coppie con distanza di hash bassa (ridondanze candidate)
  firma.json         aggregazioni (focali, ore, orientamenti, chiavi tonali...)
  saltati.csv        file non leggibili, con motivo

Uso:
  python3 prepara_provino.py CARTELLA [-o CARTELLA_USCITA]
                             [--lato-thumb 1024] [--per-griglia 12]
                             [--lato-griglia 2000] [--prefisso P]

Nessun giudizio viene prodotto qui: solo dati.
"""

import argparse
import csv
import json
import math
import os
import re
import sys
from datetime import datetime

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
    from PIL.ExifTags import TAGS
except ImportError as e:  # pragma: no cover
    sys.exit("Servono Pillow e numpy: pip install pillow numpy --break-system-packages\n%s" % e)

Image.MAX_IMAGE_PIXELS = None

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIF = True
except Exception:
    HEIF = False

try:
    import rawpy

    RAW = True
except Exception:
    RAW = False

EST_STD = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}
EST_HEIF = {".heic", ".heif"}
EST_RAW = {".nef", ".raf", ".dng", ".arw", ".cr2", ".cr3", ".orf", ".rw2", ".pef", ".srw"}

FONT_CANDIDATI = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial.ttf",
]

NOMI_COLORE = [
    (0, "rosso"), (12, "arancio"), (30, "giallo"), (48, "verde giallo"),
    (75, "verde"), (105, "verde acqua"), (128, "ciano"), (150, "azzurro"),
    (170, "blu"), (190, "viola"), (215, "magenta"), (240, "rosso"),
]


def carica_font(dim):
    for p in FONT_CANDIDATI:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, dim)
            except Exception:
                pass
    return ImageFont.load_default()


def ordina_naturale(nome):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", nome)]


def apri_immagine(percorso):
    """Restituisce (PIL.Image RGB orientata, dict exif grezzo)."""
    est = os.path.splitext(percorso)[1].lower()
    if est in EST_RAW:
        if not RAW:
            raise RuntimeError("RAW non supportato: pip install rawpy --break-system-packages")
        with rawpy.imread(percorso) as raw:
            arr = raw.postprocess(use_camera_wb=True, half_size=True, no_auto_bright=False)
        img = Image.fromarray(arr)
        exif = {}
        try:
            from PIL import Image as _I

            with _I.open(percorso) as prev:
                exif = leggi_exif(prev)
        except Exception:
            exif = {}
        return img.convert("RGB"), exif
    if est in EST_HEIF and not HEIF:
        raise RuntimeError("HEIC non supportato: pip install pillow-heif --break-system-packages")
    img = Image.open(percorso)
    exif = leggi_exif(img)
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif img.mode == "L":
        img = img.convert("RGB")
    return img, exif


def leggi_exif(img):
    dati = {}
    try:
        raw = img.getexif()
    except Exception:
        return dati
    if not raw:
        return dati
    for tag, val in raw.items():
        dati[TAGS.get(tag, str(tag))] = val
    try:
        for tag, val in raw.get_ifd(0x8769).items():
            dati[TAGS.get(tag, str(tag))] = val
    except Exception:
        pass
    return dati


def num(v):
    try:
        if isinstance(v, tuple) and len(v) == 2:
            return float(v[0]) / float(v[1]) if v[1] else None
        return float(v)
    except Exception:
        return None


def estrai_exif(e):
    def testo(k):
        v = e.get(k)
        if v is None:
            return ""
        if isinstance(v, bytes):
            try:
                v = v.decode("utf-8", "ignore")
            except Exception:
                return ""
        return str(v).strip().strip("\x00")

    iso = e.get("ISOSpeedRatings") or e.get("PhotographicSensitivity") or e.get("ISO")
    if isinstance(iso, (list, tuple)) and iso:
        iso = iso[0]
    tempo = num(e.get("ExposureTime"))
    data = testo("DateTimeOriginal") or testo("DateTime")
    ora = None
    iso_data = ""
    if data:
        for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(data[:19], fmt)
                ora = dt.hour
                iso_data = dt.strftime("%Y-%m-%d %H:%M:%S")
                break
            except Exception:
                continue
    return {
        "corpo": (testo("Make") + " " + testo("Model")).strip(),
        "ottica": testo("LensModel") or testo("LensMake"),
        "focale": num(e.get("FocalLength")),
        "focale_equivalente": num(e.get("FocalLengthIn35mmFilm")),
        "apertura": num(e.get("FNumber")),
        "tempo_s": tempo,
        "iso": int(iso) if iso not in (None, "") else None,
        "data": iso_data,
        "ora": ora,
    }


def nome_colore(h255):
    gradi = h255 * 360.0 / 255.0
    scelto = "rosso"
    for soglia, nome in NOMI_COLORE:
        if gradi >= soglia:
            scelto = nome
    return scelto


def dhash(gray_img, lato=9):
    piccola = gray_img.resize((lato, lato - 1), Image.BILINEAR)
    a = np.asarray(piccola, dtype=np.int16)
    bit = a[:, 1:] > a[:, :-1]
    valore = 0
    for b in bit.flatten():
        valore = (valore << 1) | int(b)
    return "%016x" % valore


def distanza_hash(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def misura(img):
    """Misure su una copia ridotta: confrontabili fra immagini, non assolute."""
    lavoro = img.copy()
    lavoro.thumbnail((1000, 1000), Image.LANCZOS)
    gray = lavoro.convert("L")
    g = np.asarray(gray, dtype=np.float32)
    rgb = np.asarray(lavoro, dtype=np.float32)

    lum_media = float(g.mean())
    p5, p50, p95 = [float(x) for x in np.percentile(g, [5, 50, 95])]
    contrasto = float(g.std())
    clip_neri = float((g <= 2).mean() * 100.0)
    clip_bianchi = float((g >= 253).mean() * 100.0)

    hsv = np.asarray(lavoro.convert("HSV"))
    s = hsv[:, :, 1].astype(np.float32)
    v = hsv[:, :, 2].astype(np.float32)
    sat_media = float(s.mean())

    r, gg, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    rg = r - gg
    yb = 0.5 * (r + gg) - b
    colorfulness = float(
        math.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * math.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
    )

    maschera = (s > 45) & (v > 25) & (v < 245)
    if maschera.sum() > 200:
        hues = hsv[:, :, 0][maschera]
        conteggi = np.bincount(hues, minlength=256)
        h_dom = int(np.argmax(conteggi))
        col = nome_colore(h_dom)
    else:
        h_dom, col = -1, "neutro"

    lap = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
    gp = np.pad(g, 1, mode="edge")
    conv = (
        lap[0, 1] * gp[:-2, 1:-1] + lap[1, 0] * gp[1:-1, :-2] + lap[1, 1] * gp[1:-1, 1:-1]
        + lap[1, 2] * gp[1:-1, 2:] + lap[2, 1] * gp[2:, 1:-1]
    )
    nitidezza = float(conv.var())

    hp = g - np.asarray(gray.filter(ImageFilter.MedianFilter(3)), dtype=np.float32)
    h, w = g.shape
    th, tw = max(8, h // 12), max(8, w // 12)
    piatti = []
    for y in range(0, h - th + 1, th):
        for x in range(0, w - tw + 1, tw):
            blocco = g[y:y + th, x:x + tw]
            piatti.append((float(blocco.std()), y, x))
    piatti.sort()
    quanti = max(1, len(piatti) // 10)
    rumore = float(
        np.mean([hp[y:y + th, x:x + tw].std() for _, y, x in piatti[:quanti]])
    )

    try:
        entropia = float(gray.entropy())
    except Exception:
        ist = np.bincount(np.asarray(gray).flatten(), minlength=256).astype(np.float64)
        p = ist / ist.sum()
        p = p[p > 0]
        entropia = float(-(p * np.log2(p)).sum())

    if lum_media < 85:
        chiave = "bassa"
    elif lum_media > 170:
        chiave = "alta"
    else:
        chiave = "media"

    bn = colorfulness < 8.0 or sat_media < 12.0
    ist64 = np.bincount((np.asarray(gray).flatten() // 4), minlength=64).astype(np.float64)
    ist64 = (ist64 / ist64.sum()).tolist()

    return {
        "luminanza_media": round(lum_media, 1),
        "p5": round(p5, 1),
        "p50": round(p50, 1),
        "p95": round(p95, 1),
        "contrasto": round(contrasto, 1),
        "clip_neri_pc": round(clip_neri, 2),
        "clip_bianchi_pc": round(clip_bianchi, 2),
        "saturazione_media": round(sat_media, 1),
        "colorfulness": round(colorfulness, 1),
        "hue_dominante": h_dom,
        "nome_colore": col,
        "nitidezza": round(nitidezza, 1),
        "rumore_proxy": round(rumore, 2),
        "entropia": round(entropia, 2),
        "chiave_tonale": chiave,
        "probabile_bn": bool(bn),
        "dhash": dhash(gray),
        "_ist64": ist64,
    }


def pulisci(nome):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", nome)[:60]


def costruisci_griglie(voci, dir_out, per_griglia, lato_griglia):
    os.makedirs(dir_out, exist_ok=True)
    colonne = 4 if per_griglia % 4 == 0 else 3
    righe = int(math.ceil(per_griglia / colonne))
    margine = 14
    banda = 34
    cella_w = (lato_griglia - margine * (colonne + 1)) // colonne
    cella_h = cella_w * 3 // 4
    alt = margine + righe * (cella_h + banda + margine)
    font = carica_font(20)
    prodotte = []
    for indice in range(0, len(voci), per_griglia):
        gruppo = voci[indice:indice + per_griglia]
        tela = Image.new("RGB", (lato_griglia, alt), (26, 26, 28))
        d = ImageDraw.Draw(tela)
        for k, v in enumerate(gruppo):
            rr, cc = divmod(k, colonne)
            x0 = margine + cc * (cella_w + margine)
            y0 = margine + rr * (cella_h + banda + margine)
            try:
                mini = Image.open(v["thumb_path"])
            except Exception:
                continue
            mini.thumbnail((cella_w, cella_h), Image.LANCZOS)
            ox = x0 + (cella_w - mini.width) // 2
            oy = y0 + (cella_h - mini.height) // 2
            tela.paste(mini, (ox, oy))
            etichetta = "%s  %s" % (v["id"], v["file"][:26])
            d.rectangle([x0, y0 + cella_h, x0 + cella_w, y0 + cella_h + banda], fill=(12, 12, 14))
            d.text((x0 + 6, y0 + cella_h + 7), etichetta, font=font, fill=(235, 235, 235))
        nome = os.path.join(dir_out, "griglia_%02d.jpg" % (indice // per_griglia + 1))
        tela.save(nome, "JPEG", quality=88, optimize=True)
        prodotte.append(nome)
    return prodotte


def aggrega_firma(righe):
    def conta(chiave, trasf=lambda x: x):
        c = {}
        for r in righe:
            v = r.get(chiave)
            if v in (None, "", -1):
                continue
            k = str(trasf(v))
            c[k] = c.get(k, 0) + 1
        return dict(sorted(c.items(), key=lambda kv: -kv[1]))

    date = [r["data"] for r in righe if r.get("data")]
    giorni = sorted({d[:10] for d in date})
    tot = len(righe)
    bn = sum(1 for r in righe if r.get("probabile_bn"))
    return {
        "totale_immagini": tot,
        "focali": conta("focale", lambda v: int(round(float(v)))),
        "focali_equivalenti": conta("focale_equivalente", lambda v: int(round(float(v)))),
        "aperture": conta("apertura", lambda v: round(float(v), 1)),
        "iso": conta("iso", lambda v: int(v)),
        "ore": conta("ora", lambda v: "%02d" % int(v)),
        "orientamenti": conta("orientamento"),
        "chiavi_tonali": conta("chiave_tonale"),
        "colori_dominanti": conta("nome_colore"),
        "corpi": conta("corpo"),
        "ottiche": conta("ottica"),
        "bn_vs_colore": {"probabile_bn": bn, "colore": tot - bn},
        "arco_temporale": {
            "primo": min(date)[:10] if date else None,
            "ultimo": max(date)[:10] if date else None,
            "giorni_attivi": len(giorni),
            "giorni": giorni[:80],
        },
        "medie": {
            "luminanza": round(sum(r["luminanza_media"] for r in righe) / tot, 1) if tot else None,
            "contrasto": round(sum(r["contrasto"] for r in righe) / tot, 1) if tot else None,
            "saturazione": round(sum(r["saturazione_media"] for r in righe) / tot, 1) if tot else None,
            "entropia": round(sum(r["entropia"] for r in righe) / tot, 2) if tot else None,
        },
        "segnali": {
            "con_clip_bianchi_oltre_2pc": sum(1 for r in righe if r["clip_bianchi_pc"] > 2),
            "con_clip_neri_oltre_5pc": sum(1 for r in righe if r["clip_neri_pc"] > 5),
            "verticali_pc": round(
                100.0 * sum(1 for r in righe if r["orientamento"] == "verticale") / tot, 1
            ) if tot else None,
        },
    }


def main():
    ap = argparse.ArgumentParser(description="Prepara provino, metriche e firma da una cartella di immagini.")
    ap.add_argument("cartella")
    ap.add_argument("-o", "--uscita", default=None, help="predefinito: CARTELLA/_analisi")
    ap.add_argument("--lato-thumb", type=int, default=1024)
    ap.add_argument("--per-griglia", type=int, default=12)
    ap.add_argument("--lato-griglia", type=int, default=2000)
    ap.add_argument("--prefisso", default="P")
    ap.add_argument("--soglia-simili", type=int, default=20)
    args = ap.parse_args()

    sorgente = os.path.abspath(os.path.expanduser(args.cartella))
    if not os.path.isdir(sorgente):
        sys.exit("Cartella non trovata: %s" % sorgente)
    uscita = os.path.abspath(os.path.expanduser(args.uscita or os.path.join(sorgente, "_analisi")))
    dir_thumb = os.path.join(uscita, "thumbs")
    os.makedirs(dir_thumb, exist_ok=True)

    tutti = sorted(
        [f for f in os.listdir(sorgente) if not f.startswith(".")], key=ordina_naturale
    )
    saltati = []
    candidati = []
    for f in tutti:
        p = os.path.join(sorgente, f)
        if os.path.isdir(p):
            if os.path.abspath(p) != uscita:
                saltati.append((f, "cartella, non esplorata"))
            continue
        est = os.path.splitext(f)[1].lower()
        if est in EST_STD or est in EST_HEIF or est in EST_RAW:
            candidati.append(f)
        else:
            saltati.append((f, "estensione non gestita"))

    basi = {}
    for f in candidati:
        basi.setdefault(os.path.splitext(f)[0], []).append(f)
    scelti = []
    for base, gruppo in basi.items():
        if len(gruppo) == 1:
            scelti.append(gruppo[0])
            continue
        pref = [g for g in gruppo if os.path.splitext(g)[1].lower() in (".jpg", ".jpeg")]
        tenuto = pref[0] if pref else sorted(gruppo)[0]
        scelti.append(tenuto)
        for g in gruppo:
            if g != tenuto:
                saltati.append((g, "doppione dello stesso scatto, tenuto %s" % tenuto))
    scelti.sort(key=ordina_naturale)

    righe = []
    for i, f in enumerate(scelti, 1):
        percorso = os.path.join(sorgente, f)
        ident = "%s%03d" % (args.prefisso, i)
        try:
            img, exif_raw = apri_immagine(percorso)
        except Exception as e:
            saltati.append((f, "illeggibile: %s" % e))
            continue
        w, h = img.size
        m = misura(img)
        ex = estrai_exif(exif_raw)
        thumb = img.copy()
        thumb.thumbnail((args.lato_thumb, args.lato_thumb), Image.LANCZOS)
        nome_thumb = "%s_%s.jpg" % (ident, pulisci(os.path.splitext(f)[0]))
        percorso_thumb = os.path.join(dir_thumb, nome_thumb)
        thumb.save(percorso_thumb, "JPEG", quality=90, optimize=True)
        orient = "quadrato" if abs(w - h) / max(w, h) < 0.03 else ("verticale" if h > w else "orizzontale")
        riga = {
            "id": ident,
            "file": f,
            "thumb": os.path.join("thumbs", nome_thumb),
            "thumb_path": percorso_thumb,
            "larghezza": w,
            "altezza": h,
            "mp": round(w * h / 1e6, 1),
            "aspetto": round(w / h, 3),
            "orientamento": orient,
            "peso_mb": round(os.path.getsize(percorso) / 1048576.0, 2),
        }
        riga.update(ex)
        riga.update(m)
        righe.append(riga)
        img.close()

    if not righe:
        sys.exit("Nessuna immagine leggibile in %s" % sorgente)

    valori = sorted(r["nitidezza"] for r in righe)
    for r in righe:
        pos = sum(1 for v in valori if v < r["nitidezza"])
        r["nitidezza_rango_pc"] = round(100.0 * pos / max(1, len(valori) - 1), 1)

    griglie = costruisci_griglie(righe, os.path.join(uscita, "griglie"), args.per_griglia, args.lato_griglia)

    coppie = []
    for i in range(len(righe)):
        for j in range(i + 1, len(righe)):
            d = distanza_hash(righe[i]["dhash"], righe[j]["dhash"])
            if d <= args.soglia_simili:
                a = np.array(righe[i]["_ist64"])
                b = np.array(righe[j]["_ist64"])
                denom = (np.linalg.norm(a - a.mean()) * np.linalg.norm(b - b.mean())) or 1.0
                corr = float(((a - a.mean()) * (b - b.mean())).sum() / denom)
                if d <= 12 and corr < 0.5:
                    liv = "forma simile, tono diverso: verifica guardando"
                elif d <= 5:
                    liv = "quasi identiche"
                elif d <= 12:
                    liv = "stessa idea"
                else:
                    liv = "stessa struttura"
                coppie.append(
                    {
                        "id_a": righe[i]["id"], "file_a": righe[i]["file"],
                        "id_b": righe[j]["id"], "file_b": righe[j]["file"],
                        "distanza_dhash": d, "correlazione_istogramma": round(corr, 3),
                        "livello": liv,
                    }
                )
    coppie.sort(key=lambda c: c["distanza_dhash"])

    for r in righe:
        r.pop("_ist64", None)
        r.pop("thumb_path", None)

    campi = list(righe[0].keys())
    with open(os.path.join(uscita, "metriche.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=campi)
        wr.writeheader()
        wr.writerows(righe)
    with open(os.path.join(uscita, "metriche.json"), "w", encoding="utf-8") as fh:
        json.dump({"cartella": sorgente, "immagini": righe}, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(uscita, "coppie_simili.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(
            fh,
            fieldnames=["id_a", "file_a", "id_b", "file_b", "distanza_dhash",
                        "correlazione_istogramma", "livello"],
        )
        wr.writeheader()
        wr.writerows(coppie)
    with open(os.path.join(uscita, "firma.json"), "w", encoding="utf-8") as fh:
        json.dump(aggrega_firma(righe), fh, ensure_ascii=False, indent=1)
    with open(os.path.join(uscita, "saltati.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["file", "motivo"])
        wr.writerows(saltati)

    print("Cartella di uscita: %s" % uscita)
    print("Immagini analizzate: %d" % len(righe))
    print("File saltati: %d (vedi saltati.csv)" % len(saltati))
    print("Griglie prodotte: %d" % len(griglie))
    for g in griglie:
        print("  %s" % g)
    print("Coppie simili sotto soglia %d: %d" % (args.soglia_simili, len(coppie)))
    quasi = sum(1 for c in coppie if c["distanza_dhash"] <= 5)
    if quasi:
        print("  di cui quasi identiche (0-5): %d" % quasi)
    if not RAW:
        print("Nota: rawpy assente, eventuali RAW sono stati saltati.")
    if not HEIF:
        print("Nota: pillow-heif assente, eventuali HEIC sono stati saltati.")
    print("Prossimo passo: guarda le griglie prima delle metriche (passaggio cieco).")


if __name__ == "__main__":
    main()
