#!/usr/bin/env python3
"""
genera_provino_html.py: provino interattivo autonomo, in un solo file HTML.

Legge analisi.json e le miniature e produce un file HTML autosufficiente (immagini
incorporate in base64, nessuna dipendenza esterna, nessuna storage del browser).

La pagina si spiega da sola: ogni sezione si apre con la spiegazione di cosa è e
come si legge, i punteggi mostrano il calcolo passandoci sopra il mouse, la notazione
del ritmo ha la sua legenda, e nessun elemento richiede di consultare altro.

Contiene: provino a contatto con punteggi, verdetti, ruoli, didascalie e letture di
lavoro; sequenza a doppia pagina con proposta di copertina, legenda del ritmo e
alternative; cluster; testi; scarti; tabella dati con anteprima al passaggio del
mouse.

Uso:
  python3 genera_provino_html.py analisi.json [-o provino.html]
                                 [--radice CARTELLA_THUMBS] [--lato-griglia 420]
                                 [--lato-dettaglio 1000]
"""

import argparse
import base64
import io
import json
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Serve Pillow: pip install pillow --break-system-packages")

ASSI = ["autonomia", "forza", "coerenza", "originalita", "tecnica", "funzione"]
PESI = {
    "libro": {"autonomia": 10, "forza": 20, "coerenza": 25, "originalita": 15, "tecnica": 10, "funzione": 20},
    "mostra": {"autonomia": 25, "forza": 25, "coerenza": 15, "originalita": 15, "tecnica": 20, "funzione": 0},
    "web": {"autonomia": 30, "forza": 25, "coerenza": 15, "originalita": 20, "tecnica": 10, "funzione": 0},
    "concorso": {"autonomia": 25, "forza": 30, "coerenza": 10, "originalita": 25, "tecnica": 10, "funzione": 0},
}


def punteggio(voti, pesi):
    tot = sum(pesi.values())
    acc = 0.0
    for a, p in pesi.items():
        if p and voti.get(a) is not None:
            acc += float(voti[a]) * p
    return round(acc / tot, 2) if tot else 0.0


def scorri(spread):
    """Gli id di una sequenza, anche quando una pagina ne contiene piu' di uno."""
    fuori = []
    for coppia in spread or []:
        for pagina in coppia:
            if not pagina:
                continue
            fuori.extend(pagina if isinstance(pagina, list) else [pagina])
    return fuori


def codifica(percorso, lato, qualita):
    with Image.open(percorso) as im:
        im = im.convert("RGB")
        im.thumbnail((lato, lato), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=qualita, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


# Stringa grezza: i backslash devono arrivare intatti a JavaScript (regex e apostrofi
# protetti). Senza la r, Python interpreta \n dentro le regex e le spezza.
TEMPLATE = r"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITOLO__ | provino</title>
<style>
:root{--fondo:#111214;--carta:#191a1d;--bordo:#2b2d31;--testo:#e9e9ea;--tenue:#9a9ba0;
--accento:#c8a26a;--ok:#6ea87f;--medio:#c9a227;--basso:#a55b4b;}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--testo);
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Helvetica,Arial,sans-serif;font-size:14px}
header{padding:22px 26px 16px;border-bottom:1px solid var(--bordo);background:var(--carta)}
h1{margin:0 0 4px;font-size:22px;font-weight:600;letter-spacing:.2px}
.sotto{color:var(--tenue);font-size:13px;max-width:900px;line-height:1.5}
.filo{margin-top:10px;padding:10px 14px;border-left:2px solid var(--accento);background:#00000030;
font-style:italic;color:#d9d9db;max-width:900px}
nav{display:flex;gap:2px;padding:0 26px;background:var(--carta);border-bottom:1px solid var(--bordo);
position:sticky;top:0;z-index:30;flex-wrap:wrap}
nav button{background:none;border:none;border-bottom:2px solid transparent;color:var(--tenue);
padding:11px 16px;font-size:13px;cursor:pointer;font-family:inherit}
nav button.on{color:var(--testo);border-bottom-color:var(--accento)}
.barra{display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:14px 26px;
border-bottom:1px solid var(--bordo)}
select,input[type=search]{background:#0d0e10;color:var(--testo);border:1px solid var(--bordo);
border-radius:5px;padding:6px 9px;font-size:13px;font-family:inherit}
label.mini{color:var(--tenue);font-size:12px;margin-right:4px}
main{padding:20px 26px 60px}
.intro{background:var(--carta);border:1px solid var(--bordo);border-left:3px solid var(--accento);
border-radius:6px;padding:18px 22px;margin-bottom:24px;max-width:1000px}
.intro h2{margin:0 0 8px;font-size:16px;font-weight:600}
.intro p{margin:0 0 10px;line-height:1.7;color:#d2d0cc;font-size:13.5px}
.intro p:last-child{margin-bottom:0}
.intro dl{margin:10px 0 0;display:grid;grid-template-columns:auto 1fr;gap:5px 14px;
font-size:12.5px;line-height:1.6}
.intro dt{color:var(--accento);font-weight:600;white-space:nowrap}
.intro dd{margin:0;color:#c0bebb}
.intro .att{color:var(--medio)}
.griglia{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px;
align-items:start}
.scheda{background:var(--carta);border:1px solid var(--bordo);border-radius:7px;overflow:hidden;
cursor:pointer;transition:border-color .15s,transform .15s;position:relative}
.scheda:hover{border-color:var(--accento);transform:translateY(-2px)}
.scheda.cop{border-color:var(--accento)}
.scheda .im{width:100%;height:150px;display:flex;align-items:center;justify-content:center;
background:#0a0b0c}
.scheda img{max-width:100%;max-height:150px;display:block}
.bollo{position:absolute;top:8px;left:8px;background:var(--accento);color:#14150f;font-size:9.5px;
text-transform:uppercase;letter-spacing:.8px;padding:2px 7px;border-radius:3px;font-weight:700}
.piede{padding:7px 9px;display:flex;justify-content:space-between;align-items:center;gap:6px}
.ident{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;color:var(--tenue)}
.voto{font-weight:600;font-size:13px;cursor:help;border-bottom:1px dotted currentColor}
.riga2{padding:0 9px 8px;font-size:11px;color:var(--tenue);display:flex;gap:6px;flex-wrap:wrap}
.tag{border:1px solid var(--bordo);border-radius:20px;padding:1px 7px}
.alto{color:var(--ok)}.medio{color:var(--medio)}.basso{color:var(--basso)}
.pannello{position:fixed;top:0;right:0;width:min(560px,94vw);height:100%;background:var(--carta);
border-left:1px solid var(--bordo);overflow-y:auto;transform:translateX(100%);
transition:transform .22s;z-index:60;padding:22px}
.pannello.on{transform:none}
.pannello img{width:100%;border-radius:5px;background:#000}
.chiudi{position:absolute;top:12px;right:16px;background:none;border:none;color:var(--tenue);
font-size:24px;cursor:pointer}
.assi{margin:16px 0}
.asse{display:grid;grid-template-columns:96px 1fr 26px;gap:9px;align-items:center;margin-bottom:5px;
font-size:12px;color:var(--tenue)}
.tratto{height:6px;background:#0d0e10;border-radius:3px;overflow:hidden}
.tratto i{display:block;height:100%;background:var(--accento)}
.blocco{margin:13px 0}.blocco h4{margin:0 0 3px;font-size:11px;text-transform:uppercase;
letter-spacing:.7px;color:var(--tenue);font-weight:600}
.blocco p{margin:0;line-height:1.55}
.spread{display:flex;gap:0;justify-content:center;margin:0 auto 26px;max-width:1120px;
background:var(--carta);border:1px solid var(--bordo);border-radius:5px;padding:22px;
box-shadow:0 10px 30px #0006}
.pagina{width:50%;padding:0 20px;display:flex;flex-direction:column;align-items:center;
justify-content:center;min-height:250px;gap:14px}
.pagina.sx{border-right:1px solid #ffffff12}
.pagina img{max-width:100%;max-height:380px;width:auto;box-shadow:0 3px 14px #0008}
.pagina.multi img{max-height:190px}
.blocchino{display:flex;flex-direction:column;align-items:center}
.bianca{color:#3a3c40;font-size:12px;letter-spacing:1px;text-transform:uppercase}
.didasc{margin-top:9px;font-size:12px;color:#cfcdc9;text-align:left;max-width:94%;line-height:1.55}
.didasc .ident{display:block;margin-bottom:3px}
.numsp{text-align:center;color:#4c4e54;font-size:11px;margin-bottom:7px;
font-family:ui-monospace,Menlo,monospace}
.codsp{color:var(--accento);font-family:ui-monospace,Menlo,monospace}
.gruppo{margin-bottom:34px}
.gruppo h3{margin:0 0 3px;font-size:17px}
.gruppo .tesi{color:var(--tenue);margin:0 0 12px;max-width:820px;line-height:1.5}
.ritmo{font-family:ui-monospace,Menlo,monospace;letter-spacing:2px;color:var(--accento);
background:#00000040;padding:10px 14px;border-radius:5px;display:inline-block;font-size:15px}
.didcard{padding:0 9px 9px;font-size:11.5px;color:#c9c6c1;line-height:1.5}
.desccard{padding:2px 9px 10px;font-size:11.5px;color:#a5a39f;line-height:1.5;
border-top:1px solid var(--bordo);margin-top:2px;padding-top:8px}
.etich{display:block;font-size:9.5px;text-transform:uppercase;letter-spacing:.9px;
color:#6b6d73;margin-bottom:4px;font-style:normal}
.etich.pub{color:var(--accento)}
.descpanel{margin:10px 0 2px;font-size:13px;line-height:1.6;color:#b6b4b0}
.descseq{margin-top:8px;font-size:11px;color:#7e7c78;line-height:1.5}
.descmanca{color:var(--basso);font-size:12px;padding:0 9px 9px}
.didpanel{margin:9px 0 4px;padding:9px 12px;border-left:2px solid var(--accento);
background:#00000030;color:#e4e2de;font-size:13.5px;line-height:1.6}
.didpanel.manca{border-left-color:var(--basso);color:var(--basso)}
.testi{max-width:780px}
.testi h3{font-size:12px;text-transform:uppercase;letter-spacing:.8px;color:var(--tenue);
margin:30px 0 8px;font-weight:600}
.testi p{line-height:1.75;font-size:14.5px;margin:0 0 14px}
.testi .conta{color:#5a5c62;font-size:11.5px;font-family:ui-monospace,Menlo,monospace}
.tav{display:grid;grid-template-columns:100px 1fr;gap:12px;padding:9px 0;
border-bottom:1px solid var(--bordo);align-items:baseline}
.tav b{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:var(--tenue);font-weight:400}
mark{background:#5a4423;color:#f0d9a8;border-radius:3px;padding:0 3px}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--bordo)}
th{color:var(--tenue);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.5px}
td.filo{cursor:help;color:var(--accento);border-left:none;background:none;font-style:normal;
padding:7px 9px}
.vuoto{color:var(--tenue);padding:40px 0;text-align:center}
footer{padding:18px 26px;color:#5a5c62;font-size:11.5px;border-top:1px solid var(--bordo)}
.copertina{display:flex;gap:22px;align-items:flex-start;background:var(--carta);
border:1px solid var(--bordo);border-radius:6px;padding:20px;margin-bottom:26px;max-width:1000px}
.copertina img{max-width:230px;max-height:230px;box-shadow:0 4px 18px #0009;cursor:pointer}
.copertina h3{margin:0 0 6px;font-size:15px}
.copertina p{margin:0 0 10px;line-height:1.65;color:#cfcdc9;font-size:13.5px}
.alt{border-top:1px solid var(--bordo);padding-top:10px;margin-top:6px;font-size:12.5px;
color:var(--tenue);line-height:1.6}
.legenda{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;
margin:14px 0 0}
.legenda div{background:#00000030;border-radius:5px;padding:10px 13px;font-size:12.5px;
line-height:1.55;color:#c0bebb}
.legenda b{color:var(--accento)}
#tip{position:fixed;z-index:90;pointer-events:none;background:#0b0c0e;border:1px solid var(--accento);
border-radius:6px;padding:11px 13px;font-size:12px;line-height:1.55;max-width:330px;
box-shadow:0 8px 26px #000a;display:none;color:#e9e9ea}
#tip img{max-width:290px;max-height:210px;display:block;border-radius:3px}
#tip table{font-size:11.5px;margin-top:6px}
#tip th,#tip td{padding:2px 6px;border-bottom:1px solid #26282c}
#tip .tot{color:var(--accento);font-weight:600}
</style></head><body>
<header>
<h1>__TITOLO__</h1>
<div class="sotto">__SOTTO__</div>
__FILO__
</header>
<nav>
<button class="on" data-vista="provino">Provino</button>
<button data-vista="sequenza">Sequenza</button>
<button data-vista="cluster">Cluster</button>
<button data-vista="testi">Testi</button>
<button data-vista="scarti">Scarti</button>
<button data-vista="dati">Dati</button>
</nav>
<div class="barra" id="barra">
<label class="mini">ordina</label>
<select id="ordine">
<option value="p_libro">punteggio libro</option>
<option value="p_mostra">punteggio mostra</option>
<option value="p_web">punteggio web</option>
<option value="p_concorso">punteggio concorso</option>
<option value="id">id</option>
</select>
<label class="mini">cluster</label><select id="fcluster"></select>
<label class="mini">verdetto</label><select id="fverdetto"></select>
<label class="mini">cieco</label><select id="fcieco"></select>
<input type="search" id="cerca" placeholder="cerca file, ruolo, nota">
<span class="mini" id="conteggio"></span>
</div>
<main>
<div id="vista-provino"></div>
<div id="vista-sequenza" hidden></div>
<div id="vista-cluster" hidden></div>
<div id="vista-testi" hidden></div>
<div id="vista-scarti" hidden></div>
<div id="vista-dati" hidden></div>
</main>
<div class="pannello" id="pannello"><button class="chiudi" onclick="chiudi()">&times;</button>
<div id="dettaglio"></div></div>
<div id="tip"></div>
<footer>__PIEDE__</footer>
<script>
const D = __DATI__;
const ASSI = ["autonomia","forza","coerenza","originalita","tecnica","funzione"];
const PESI = __PESI__;
const NOMEDEST = {p_libro:"libro", p_mostra:"mostra", p_web:"portfolio web", p_concorso:"concorso"};
const per = {}; D.immagini.forEach(i => per[i.id] = i);
const P = D.progetto || {};

function classe(v){ return v >= 7.5 ? "alto" : (v >= 6 ? "medio" : "basso"); }
function conta(t){ return (String(t||'').match(/[\wàèéìòùÀÈÉÌÒÙ']+/g) || []).length; }
function segna(t){ return String(t||'').replace(/\[([^\]]+)\]/g, '<mark>[$1]</mark>'); }
function paragrafi(t){ return String(t||'').split(/\n\s*\n/).map(p => '<p>' + segna(p.trim()) + '</p>').join(''); }
function chiaveDest(){ const v = document.getElementById('ordine').value; return v === 'id' ? 'p_libro' : v; }

/* ---------- suggerimento flottante ---------- */
const tip = document.getElementById('tip');
function mostraTip(html, e){
  tip.innerHTML = html; tip.style.display = 'block';
  const r = tip.getBoundingClientRect();
  let x = e.clientX + 16, y = e.clientY + 16;
  if (x + r.width > window.innerWidth - 10) x = e.clientX - r.width - 16;
  if (y + r.height > window.innerHeight - 10) y = e.clientY - r.height - 16;
  tip.style.left = Math.max(8, x) + 'px'; tip.style.top = Math.max(8, y) + 'px';
}
function nascondiTip(){ tip.style.display = 'none'; }
function tipPunteggio(id, dest){
  const i = per[id]; if (!i) return '';
  const pesi = PESI[dest.replace('p_','') === 'web' ? 'web' : dest.replace('p_','')];
  let somma = 0, tot = 0, righe = '';
  ASSI.forEach(a => {
    const w = pesi[a], v = (i.voti||{})[a];
    tot += w;
    if (w) somma += (v||0) * w;
    righe += '<tr><td>' + a + '</td><td>' + (v ?? '-') + '</td><td>' + w + '%</td><td>' +
             (w ? ((v||0)*w/100).toFixed(2) : '&mdash;') + '</td></tr>';
  });
  return '<b>Punteggio per ' + NOMEDEST[dest] + ': ' + (somma/tot).toFixed(2) + ' su 10</b>' +
    '<div style="color:#9a9ba0;margin-top:4px">Media dei sei assi pesata per la destinazione. ' +
    'I pesi cambiano con la destinazione: nel libro conta la coerenza col progetto, ' +
    'al concorso contano forza e originalità.</div>' +
    '<table><tr><th>asse</th><th>voto</th><th>peso</th><th>contributo</th></tr>' + righe +
    '<tr class="tot"><td colspan="3">totale</td><td>' + (somma/tot).toFixed(2) + '</td></tr></table>' +
    '<div style="margin-top:6px;color:#9a9ba0">Altre destinazioni: libro ' + i.p_libro.toFixed(2) +
    ', mostra ' + i.p_mostra.toFixed(2) + ', web ' + i.p_web.toFixed(2) +
    ', concorso ' + i.p_concorso.toFixed(2) + '.</div>';
}
document.addEventListener('mouseover', e => {
  const v = e.target.closest('[data-voto]');
  if (v){ mostraTip(tipPunteggio(v.dataset.voto, chiaveDest()), e); return; }
  const t = e.target.closest('[data-thumb]');
  if (t){ const i = per[t.dataset.thumb];
    if (i) mostraTip('<img src="' + i.mini + '"><div style="margin-top:6px"><b>' + i.id +
      '</b> &middot; ' + i.file + '</div>', e); return; }
  nascondiTip();
});
document.addEventListener('mousemove', e => { if (tip.style.display === 'block'){
  const s = e.target.closest('[data-voto],[data-thumb]'); if (!s) nascondiTip(); else mostraTip(tip.innerHTML, e); } });

/* ---------- filtri ---------- */
function opzioni(sel, valori, etichetta){
  sel.innerHTML = '<option value="">' + etichetta + '</option>' +
    valori.map(v => '<option value="' + v + '">' + v + '</option>').join('');
}
opzioni(document.getElementById('fcluster'),
  [...new Set(D.immagini.flatMap(i => i.cluster || []))].sort(), 'tutti');
opzioni(document.getElementById('fverdetto'),
  [...new Set(D.immagini.map(i => i.verdetto).filter(Boolean))], 'tutti');
opzioni(document.getElementById('fcieco'),
  [...new Set(D.immagini.map(i => i.cieco).filter(Boolean))], 'tutti');

/* ---------- introduzioni ---------- */
const INTRO = {
provino: `<div class="intro"><h2>Provino a contatto</h2>
<p>Tutte le <b>${D.immagini.length} immagini analizzate</b>, comprese quelle scartate.
Serve a vedere l'insieme in un colpo d'occhio, confrontare, filtrare e capire quali
fotografie cambiano valore al cambiare della destinazione. Clicca una scheda per il
pannello di dettaglio, passa il mouse sul punteggio per vedere come è calcolato.</p>
<p>Sotto ogni fotografia trovi, nell'ordine: <b>il punteggio</b> per la destinazione
scelta nel menu "ordina", <b>il verdetto</b>, <b>il ruolo</b> che l'immagine avrebbe
in una sequenza, <b>l'esito del passaggio cieco</b>, <b>la didascalia da pubblicare</b>
e <b>la lettura di lavoro</b>.</p>
<dl>
<dt>Il punteggio</dt><dd>media dei sei assi (autonomia, forza, coerenza col progetto,
originalità, tenuta tecnica, funzione in sequenza) pesata secondo la destinazione.
Va da 1 a 10. Passaci sopra il mouse per vedere voti, pesi e conto.</dd>
<dt>Il verdetto</dt><dd>cinque livelli crescenti: <b>da scartare</b>, <b>da archivio</b>
(tienila ma non mostrarla), <b>da portfolio</b>, <b>da stampa</b>, <b>da mostra</b>.</dd>
<dt>Il ruolo</dt><dd>cosa farebbe dentro una sequenza: apertura, nucleo, ponte fra due
momenti, pausa che abbassa la tensione, climax, chiusura, oppure nessuno.</dd>
<dt>Il passaggio cieco</dt><dd>prima di aprire dati tecnici e metriche, le fotografie
sono state guardate solo come provini, a freddo, e la prima impressione è stata
registrata. Confrontandola con la classifica ragionata escono quattro casi:
<b>esca</b> (colpisce subito e scende dopo l'analisi: buona come copertina o apertura,
non come nucleo), <b>lenta</b> (ignorata a freddo, sale dopo: è il cuore possibile del
lavoro, ma va aiutata dalla posizione), <b>stabile alta</b> (regge su entrambi i piani,
sono le immagini pubbliche), <b>stabile bassa</b> (non salvarla per affetto).</dd>
<dt>I due testi</dt><dd>la <b>didascalia da pubblicare</b> è scritta per il lettore del
libro e non contiene giudizi; la <b>lettura di lavoro</b> è il giudizio del photo editor,
serve a te e non va stampata.</dd>
</dl></div>`,

sequenza: `<div class="intro"><h2>Sequenza</h2>
<p>L'ordine proposto per la pubblicazione, mostrato come lo vedrà il lettore: non una
fotografia alla volta ma <b>una doppia pagina alla volta</b>, perché sfogliando un libro
non si può vedere una pagina sola. La pagina destra è quella su cui cade l'occhio per
prima e regge la tensione; la sinistra sostiene, contrasta o resta bianca.</p>
<p>Le <b>pagine bianche non sono un errore</b>: sono il respiro, e servono a rendere
percepibili i picchi. Quando due o più fotografie stanno sulla stessa pagina è una
scelta dichiarata: significa che si leggono insieme e che il senso nasce
dall'accostamento, non dalla singola immagine.</p>
<p>Sotto ogni fotografia c'è <b>la didascalia destinata al lettore</b>, quella che andrà
stampata. La riga più piccola in grigio è la lettura di lavoro e non fa parte della
pubblicazione: è lì solo per farti decidere.</p></div>`,

cluster: `<div class="intro"><h2>Cluster tematici</h2>
<p>I gruppi in cui le fotografie si organizzano da sole quando si guarda cosa hanno in
comune. Un cluster non è una categoria: è un gruppo che reggerebbe come piccolo
progetto autonomo, e per esserlo deve avere almeno quattro immagini, una tesi propria
in una frase, una variazione interna (se sono tutte la stessa inquadratura è una
ripetizione, non un gruppo) e un confine, cioè si deve poter dire quale immagine è
stata esclusa e perché.</p>
<p>Il numero accanto al nome è la <b>forza da 1 a 10</b>: quanto quel gruppo reggerebbe
da solo come galleria o come progetto. Su un insieme di questa dimensione, di norma
reggono davvero due o tre cluster: se ne trovi otto, sono categorie.</p></div>`,

testi: `<div class="intro"><h2>Testi</h2>
<p>Tutto il testo che accompagna le fotografie, con il conteggio delle parole. Sono
quattro cose diverse e non si sostituiscono a vicenda.</p>
<dl>
<dt>Il titolo</dt><dd>tre candidati, ciascuno con il suo registro, perché la scelta è
tua. Un titolo non deve spiegare la tesi: se la spiega, rende il libro inutile.</dd>
<dt>L'introduzione</dt><dd>da 250 a 500 parole, è la pagina che il lettore legge prima
o dopo le fotografie. Non descrive le immagini e non chiude il senso.</dd>
<dt>Lo statement</dt><dd>da 60 a 120 parole, è una scheda: serve a chi deve capire in
fretta cosa è questo lavoro, cioè giurie, editori, curatori, moduli di bandi.</dd>
<dt>Le didascalie</dt><dd>una per ogni fotografia della sequenza, numerate come tavole,
tutte nello stesso registro. Sono scritte per il lettore e non contengono giudizi.</dd>
<dt>Le letture di lavoro</dt><dd>in fondo, separate: sono il giudizio del photo editor
su ogni immagine e <b>non vanno nella pubblicazione</b>.</dd>
</dl>
<p class="att">Le parti fra parentesi quadre evidenziate in giallo sono segnaposto: dati
che non possono essere affermati con certezza e che devi compilare tu. Nessun luogo,
nome o fatto è stato inventato per far suonare meglio una frase.</p></div>`,

scarti: `<div class="intro"><h2>Scarti</h2>
<p>Le fotografie escluse dall'edit, ciascuna con il motivo. Sono qui e non nascoste per
una ragione precisa: <b>una selezione senza le esclusioni motivate non è discutibile</b>,
e tu devi poter contestare ogni singolo taglio.</p>
<p>Un'immagine può essere scartata per ridondanza (dice la stessa cosa di un'altra più
forte), per estraneità alla tesi, o perché non regge da sola. Nessuno di questi motivi
è un giudizio definitivo sulla fotografia: la stessa immagine può essere centrale in un
altro edit, con un'altra tesi.</p></div>`,

dati: `<div class="intro"><h2>Dati</h2>
<p>La tabella completa: per ogni immagine i sei voti e i quattro punteggi di
destinazione, per confrontare tutto a colpo d'occhio senza scorrere le schede.</p>
<p><b>Passa il mouse sul nome del file</b> per vedere l'anteprima della fotografia, e
<b>sui punteggi</b> per il conto completo.</p>
<dl>
<dt>I sei assi</dt><dd><b>aut</b>onomia: regge da sola, senza didascalia e senza le
altre. <b>forz</b>a: ferma l'occhio, e per quanto. <b>coer</b>enza: appartiene alla tesi
del progetto. <b>orig</b>inalità: distanza dal già visto. <b>tecn</b>ica: tenuta
esecutiva rispetto all'intenzione, non in assoluto. <b>funz</b>ione: cosa fa dentro la
sequenza.</dd>
<dt>Le quattro destinazioni</dt><dd>gli stessi voti pesati in modo diverso. Libro:
coerenza 25%, funzione 20%, autonomia solo 10%. Mostra: autonomia e forza 25% ciascuna,
tecnica 20%. Web: autonomia 30%, la più alta. Concorso: forza 30% e originalità 25%.</dd>
<dt>Cosa guardare</dt><dd>le immagini che <b>cambiano molto di rango</b> fra libro e
concorso: dicono se sei un autore di fotografie singole o di progetti.</dd>
</dl></div>`,
};

/* ---------- provino ---------- */
function schedaHtml(i, dest){
  const cop = (P.copertina === i.id);
  return `<div class="scheda ${cop ? 'cop' : ''}" onclick="apri('${i.id}')">
    ${cop ? '<span class="bollo">copertina proposta</span>' : ''}
    <div class="im"><img src="${i.mini}" alt="${i.id}"></div>
    <div class="piede"><span class="ident">${i.id}</span>
      <span class="voto ${classe(i[dest]||0)}" data-voto="${i.id}">${(i[dest]||0).toFixed(1)}</span></div>
    <div class="riga2">${i.verdetto ? '<span class="tag">' + i.verdetto + '</span>' : ''}
      ${i.ruolo ? '<span class="tag">' + i.ruolo + '</span>' : ''}
      ${i.cieco ? '<span class="tag">' + i.cieco + '</span>' : ''}</div>
    ${i.didascalia ? '<div class="didcard"><span class="etich pub">didascalia da pubblicare</span>' + i.didascalia + '</div>' : ''}
    ${i.descrizione ? '<div class="desccard"><span class="etich">lettura di lavoro, non pubblicare</span>' + i.descrizione + '</div>'
                    : '<div class="descmanca">lettura di lavoro mancante</div>'}
  </div>`;
}
function disegnaGriglia(){
  const ord = document.getElementById('ordine').value, dest = chiaveDest();
  const fc = document.getElementById('fcluster').value;
  const fv = document.getElementById('fverdetto').value;
  const fk = document.getElementById('fcieco').value;
  const q = document.getElementById('cerca').value.toLowerCase();
  let lista = D.immagini.filter(i =>
    (!fc || (i.cluster || []).includes(fc)) && (!fv || i.verdetto === fv) &&
    (!fk || i.cieco === fk) && (!q || JSON.stringify(i).toLowerCase().includes(q)));
  lista.sort((a, b) => ord === 'id' ? a.id.localeCompare(b.id) : (b[ord] || 0) - (a[ord] || 0));
  document.getElementById('conteggio').textContent = lista.length + ' di ' + D.immagini.length;
  document.getElementById('vista-provino').innerHTML = INTRO.provino +
    '<div class="griglia">' + (lista.map(i => schedaHtml(i, dest)).join('') ||
    '<div class="vuoto">Nessuna immagine con questi filtri.</div>') + '</div>';
}
function blocco(t, c){ return `<div class="blocco"><h4>${t}</h4><p>${c}</p></div>`; }
function apri(id){
  const i = per[id];
  document.getElementById('dettaglio').innerHTML = `
    <img src="${i.grande || i.mini}" alt="${i.id}">
    <h3 style="margin:14px 0 2px">${i.titolo || i.file}</h3>
    <div class="ident">${i.id} &middot; ${i.file}${i.genere ? ' &middot; ' + i.genere : ''}</div>
    ${P.copertina === i.id ? '<div class="didpanel" style="border-left-color:var(--ok)"><span class="etich pub">copertina proposta</span>' + (P.copertina_motivazione || '') + '</div>' : ''}
    ${i.didascalia ? '<div class="didpanel"><span class="etich pub">didascalia da pubblicare</span>' + i.didascalia + '</div>' : ''}
    ${i.descrizione ? '<div class="descpanel"><span class="etich">lettura di lavoro, non pubblicare</span>' + i.descrizione + '</div>' : ''}
    <div class="assi">${ASSI.map(a => {
      const v = (i.voti || {})[a];
      return `<div class="asse"><span>${a}</span><span class="tratto"><i style="width:${(v || 0) * 10}%"></i></span><span>${v ?? '-'}</span></div>`;
    }).join('')}</div>
    <table><tr><th>libro</th><th>mostra</th><th>web</th><th>concorso</th></tr>
    <tr><td class="${classe(i.p_libro)}" data-voto="${i.id}">${i.p_libro.toFixed(2)}</td>
    <td class="${classe(i.p_mostra)}">${i.p_mostra.toFixed(2)}</td>
    <td class="${classe(i.p_web)}">${i.p_web.toFixed(2)}</td>
    <td class="${classe(i.p_concorso)}">${i.p_concorso.toFixed(2)}</td></tr></table>
    ${i.verdetto ? blocco('verdetto', i.verdetto) : ''}
    ${i.ruolo ? blocco('ruolo in sequenza', i.ruolo) : ''}
    ${i.cieco ? blocco('passaggio cieco', i.cieco) : ''}
    ${(i.cluster || []).length ? blocco('cluster', i.cluster.join(', ')) : ''}
    ${i.forza_principale ? blocco('forza', i.forza_principale) : ''}
    ${i.limite_principale ? blocco('limite', i.limite_principale) : ''}
    ${i.note ? blocco('note', i.note) : ''}`;
  document.getElementById('pannello').classList.add('on');
}
function chiudi(){ document.getElementById('pannello').classList.remove('on'); }
document.addEventListener('keydown', e => { if (e.key === 'Escape') chiudi(); });

/* ---------- sequenza ---------- */
function unaFoto(id){
  const i = per[id];
  if (!i) return '<span class="bianca">' + id + ' assente</span>';
  return `<div class="blocchino"><img src="${i.grande || i.mini}" alt="${id}">
    <div class="didasc"><span class="ident">${id}</span>${i.didascalia || ''}
    ${i.descrizione ? '<div class="descseq"><span class="etich">lettura di lavoro, non va nel libro</span>' + i.descrizione + '</div>' : ''}</div></div>`;
}
function pagina(val, lato){
  if (!val) return `<div class="pagina ${lato}"><span class="bianca">pagina bianca</span></div>`;
  const ids = Array.isArray(val) ? val : [val];
  return `<div class="pagina ${lato} ${ids.length > 1 ? 'multi' : ''}">${ids.map(unaFoto).join('')}</div>`;
}
function disegnaSequenza(){
  const s = (D.sequenza && D.sequenza.spread) || [];
  const el = document.getElementById('vista-sequenza');
  let h = INTRO.sequenza;

  if (P.copertina && per[P.copertina]){
    const c = per[P.copertina];
    h += `<div class="copertina"><img src="${c.grande || c.mini}" onclick="apri('${c.id}')">
      <div><h3>Copertina proposta: ${c.id}</h3>
      <p>${P.copertina_motivazione || ''}</p>
      <p style="color:#9a9ba0;font-size:12.5px">Una copertina non è l'apertura del libro e
      quasi mai è la fotografia migliore: deve funzionare <b>fuori dal contesto</b>, ridotta a
      pochi centimetri, con il titolo stampato sopra, e deve incuriosire senza raccontare.
      L'apertura invece lavora dentro la sequenza, quando il lettore ha già il libro in mano.</p>
      ${(P.copertina_alternative || []).length ? '<div class="alt"><b>Alternative:</b> ' +
        P.copertina_alternative.map(a => '<span style="cursor:pointer;color:var(--accento)" onclick="apri(\'' +
        a.id + '\')">' + a.id + '</span> ' + (a.motivazione || '')).join(' &nbsp;&middot;&nbsp; ') +
        '</div>' : ''}</div></div>`;
  }

  if (!s.length){ el.innerHTML = h + '<div class="vuoto">Nessuna sequenza in analisi.json.</div>'; return; }

  const codici = (D.sequenza.ritmo || '').trim().split(/\s+/).filter(Boolean);
  h += `<div class="intro"><h2>Il ritmo della sequenza</h2>
    <p>Questa stringa è la sequenza vista come struttura, senza le fotografie che
    distraggono. <b>Un codice di due caratteri per ogni doppia pagina</b>, nell'ordine.</p>
    <div class="ritmo">${D.sequenza.ritmo || 'non calcolato'}</div>
    <div class="legenda">
      <div><b>Primo carattere, la tensione.</b> <b>A</b> alta: il picco, l'immagine che
      chiede attenzione. <b>M</b> media: il corpo del discorso. <b>B</b> bassa: la pausa,
      il respiro dopo un picco.</div>
      <div><b>Secondo carattere, la densità visiva.</b> <b>+</b> affollata, molti elementi
      nel fotogramma. <b>=</b> media. <b>-</b> vuota, poca materia, molto spazio.</div>
      <div><b>Come si legge.</b> Nessuna A nelle prime due posizioni significa che il
      lettore non entra. Tre A di fila saturano: dal terzo picco non si sentono più i
      picchi. Quattro B di fila e il libro si è spento. Tutte <b>+</b> affaticano, tutte
      <b>=</b> vuol dire che il ritmo non esiste. L'ultima posizione deve essere A o B, mai
      M: si chiude col colpo finale o con la dissolvenza, mai a metà.</div>
    </div>
    ${D.sequenza.ritmo_perche ? '<p style="margin-top:14px">' + D.sequenza.ritmo_perche + '</p>' : ''}
    ${(D.sequenza.alternative || []).length ? '<h2 style="margin-top:18px;font-size:14px">Alternative scartate</h2>' +
      D.sequenza.alternative.map(a => '<p><b>' + a.nome + '</b> <span class="ritmo" style="font-size:12px;padding:3px 8px">' +
      (a.ritmo || '') + '</span><br>' + (a.perche || '') + '</p>').join('') : ''}
    </div>`;

  h += s.map((c, n) => {
    const cod = codici[n] ? '<span class="codsp">' + codici[n] + '</span>' : '';
    return `<div class="numsp">spread ${n + 1} &nbsp; ${cod} &nbsp; pagine ${n*2+2} e ${n*2+3}</div>
      <div class="spread">${pagina(c[0], 'sx')}${pagina(c[1], 'dx')}</div>`;
  }).join('');
  el.innerHTML = h;
}

/* ---------- cluster, testi, scarti, dati ---------- */
function disegnaCluster(){
  const el = document.getElementById('vista-cluster');
  const g = D.cluster || [];
  el.innerHTML = INTRO.cluster + (!g.length ? '<div class="vuoto">Nessun cluster.</div>' :
    g.map(c => `<div class="gruppo"><h3>${c.nome || c.id}
      ${c.forza ? '<span class="voto ' + classe(c.forza) + '" style="font-size:14px;border:none"> ' + c.forza + '/10</span>' : ''}</h3>
      <p class="tesi">${c.tesi || ''}${c.registro_nome ? ' <span class="tag">' + c.registro_nome + '</span>' : ''}</p>
      <div class="griglia">${(c.immagini || []).map(id => per[id] ? schedaHtml(per[id], chiaveDest()) : '').join('')}</div></div>`
    ).join(''));
}
function disegnaScarti(){
  const el = document.getElementById('vista-scarti');
  const s = D.scarti || [];
  el.innerHTML = INTRO.scarti + (!s.length ? '<div class="vuoto">Nessuno scarto dichiarato.</div>' :
    '<div class="griglia">' + s.map(x => {
      const i = per[x.id]; if (!i) return '';
      return `<div class="scheda" onclick="apri('${x.id}')"><div class="im"><img src="${i.mini}"></div>
        <div class="piede"><span class="ident">${x.id}</span>
        <span class="voto ${classe(i.p_libro)}" data-voto="${i.id}">${i.p_libro.toFixed(1)}</span></div>
        <div class="didcard"><span class="etich pub">motivo dello scarto</span>${x.motivo || ''}</div>
        ${i.descrizione ? '<div class="desccard"><span class="etich">lettura di lavoro</span>' + i.descrizione + '</div>' : ''}</div>`;
    }).join('') + '</div>');
}
function disegnaTesti(){
  let h = INTRO.testi + '<div class="testi">';
  h += '<h3>Titolo</h3><p style="font-size:22px;margin-bottom:4px">' + (P.titolo || 'senza titolo') +
       (P.sottotitolo ? '<span style="font-size:14px;color:var(--tenue)"><br>' + P.sottotitolo + '</span>' : '') + '</p>';
  if ((P.titoli_candidati || []).length)
    h += '<table><tr><th>candidato</th><th>registro</th><th>perché</th></tr>' +
      P.titoli_candidati.map(c => '<tr><td>' + (c.titolo||'') + '</td><td>' + (c.registro||'') +
      '</td><td>' + (c.motivazione||'') + '</td></tr>').join('') + '</table>';
  if (P.introduzione)
    h += '<h3>Introduzione <span class="conta">' + (P.registro_introduzione || 'registro non dichiarato') +
         ', ' + conta(P.introduzione) + ' parole</span></h3>' + paragrafi(P.introduzione);
  if (P.nota_autore)
    h += '<h3>Nota dell\'autore <span class="conta">' + conta(P.nota_autore) + ' parole</span></h3>' + paragrafi(P.nota_autore);
  if (P.statement)
    h += '<h3>Statement <span class="conta">' + conta(P.statement) + ' parole</span></h3>' + paragrafi(P.statement);
  const tav = D.tavole || [];
  if (tav.length){
    h += '<h3>Didascalie da pubblicare <span class="conta">registro ' + (P.registro_didascalie || 'non dichiarato') +
         ', ' + tav.length + ' tavole</span></h3>';
    h += tav.map((id, n) => '<div class="tav"><b>Tavola ' + (n+1) + ' &middot; <span data-thumb="' + id + '">' +
      id + '</span></b><span>' + segna((per[id]||{}).didascalia || 'manca') + '</span></div>').join('');
    const aperti = tav.reduce((a, id) => a + ((String((per[id]||{}).didascalia||'').match(/\[[^\]]+\]/g)||[]).length), 0);
    if (aperti) h += '<p class="conta" style="margin-top:14px">Segnaposto ancora da compilare: ' + aperti + '.</p>';
  }
  const conDesc = D.immagini.filter(i => i.descrizione);
  if (conDesc.length){
    h += '<h3>Letture di lavoro <span class="conta">' + conDesc.length + ' su ' + D.immagini.length +
         ' immagini, non vanno nella pubblicazione</span></h3>';
    h += conDesc.map(i => '<div class="tav"><b><span data-thumb="' + i.id + '">' + i.id +
      '</span></b><span>' + segna(i.descrizione) + '</span></div>').join('');
  }
  document.getElementById('vista-testi').innerHTML = h + '</div>';
}
function disegnaDati(){
  const righe = D.immagini.map(i => `<tr><td>${i.id}</td><td class="filo" data-thumb="${i.id}">${i.file}</td>
    ${ASSI.map(a => '<td>' + ((i.voti || {})[a] ?? '-') + '</td>').join('')}
    <td class="${classe(i.p_libro)}" data-voto="${i.id}">${i.p_libro.toFixed(2)}</td>
    <td class="${classe(i.p_mostra)}">${i.p_mostra.toFixed(2)}</td>
    <td class="${classe(i.p_web)}">${i.p_web.toFixed(2)}</td>
    <td class="${classe(i.p_concorso)}">${i.p_concorso.toFixed(2)}</td>
    <td>${i.verdetto || ''}</td><td>${i.ruolo || ''}</td></tr>`).join('');
  document.getElementById('vista-dati').innerHTML = INTRO.dati + `<table><tr><th>id</th><th>file</th>
    ${ASSI.map(a => '<th>' + a.slice(0, 4) + '</th>').join('')}
    <th>libro</th><th>mostra</th><th>web</th><th>conc</th><th>verdetto</th><th>ruolo</th></tr>${righe}</table>`;
}

document.querySelectorAll('nav button').forEach(b => b.onclick = () => {
  document.querySelectorAll('nav button').forEach(x => x.classList.remove('on'));
  b.classList.add('on');
  const v = b.dataset.vista;
  ['provino', 'sequenza', 'cluster', 'testi', 'scarti', 'dati'].forEach(n =>
    document.getElementById('vista-' + n).hidden = (n !== v));
  document.getElementById('barra').style.display = (v === 'provino') ? 'flex' : 'none';
  nascondiTip();
});
['ordine', 'fcluster', 'fverdetto', 'fcieco'].forEach(k =>
  document.getElementById(k).onchange = () => { disegnaGriglia(); disegnaCluster(); });
document.getElementById('cerca').oninput = disegnaGriglia;
disegnaGriglia(); disegnaSequenza(); disegnaCluster(); disegnaTesti(); disegnaScarti(); disegnaDati();
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description="Provino interattivo autonomo da analisi.json")
    ap.add_argument("analisi")
    ap.add_argument("-o", "--uscita", default=None)
    ap.add_argument("--radice", default=None, help="cartella base per i percorsi thumb")
    ap.add_argument("--lato-griglia", type=int, default=420)
    ap.add_argument("--lato-dettaglio", type=int, default=1000)
    args = ap.parse_args()

    percorso = os.path.abspath(os.path.expanduser(args.analisi))
    with open(percorso, encoding="utf-8") as fh:
        dati = json.load(fh)
    base = os.path.abspath(os.path.expanduser(args.radice or os.path.dirname(percorso) or "."))
    prog = dati.get("progetto") or {}

    immagini, mancanti = [], []
    for im in dati.get("immagini") or []:
        rel = im.get("thumb") or im.get("file")
        p = rel if os.path.isabs(rel) else os.path.join(base, rel)
        if not os.path.exists(p):
            mancanti.append(rel)
            continue
        voti = im.get("voti", {})
        immagini.append({
            "id": im["id"], "file": im.get("file", ""), "titolo": im.get("titolo", ""),
            "genere": im.get("genere", ""), "voti": voti, "verdetto": im.get("verdetto", ""),
            "ruolo": im.get("ruolo", ""), "cluster": im.get("cluster", []) or [],
            "didascalia": im.get("didascalia", ""), "descrizione": im.get("descrizione", ""),
            "cieco": im.get("cieco", ""), "note": im.get("note", ""),
            "forza_principale": im.get("forza_principale", ""),
            "limite_principale": im.get("limite_principale", ""),
            "mini": codifica(p, args.lato_griglia, 70),
            "grande": codifica(p, args.lato_dettaglio, 72),
            "p_libro": punteggio(voti, PESI["libro"]),
            "p_mostra": punteggio(voti, PESI["mostra"]),
            "p_web": punteggio(voti, PESI["web"]),
            "p_concorso": punteggio(voti, PESI["concorso"]),
        })
    if not immagini:
        sys.exit("Nessuna miniatura trovata. Controlla i percorsi thumb o passa --radice.")
    if mancanti:
        print("Attenzione, miniature non trovate: %s" % ", ".join(mancanti[:8]))

    validi = {i["id"] for i in immagini}
    tavole = [t for t in scorri((dati.get("sequenza") or {}).get("spread")) if t in validi]
    if not tavole:
        gall = dati.get("gallerie") or []
        tavole = [t for t in (gall[0].get("ordine") if gall else []) if t in validi] or sorted(validi)

    carico = {
        "immagini": immagini,
        "cluster": dati.get("cluster") or [],
        "sequenza": dati.get("sequenza") or {},
        "scarti": dati.get("scarti") or [],
        "tavole": tavole,
        "progetto": {k: prog.get(k) for k in (
            "titolo", "sottotitolo", "autore", "fil_rouge", "introduzione",
            "registro_introduzione", "statement", "nota_autore", "registro_didascalie",
            "titoli_candidati", "copertina", "copertina_motivazione", "copertina_alternative",
        ) if prog.get(k)},
    }
    sotto = " &middot; ".join([x for x in [
        prog.get("autore"), prog.get("modalita"), prog.get("destinazione"),
        "%d immagini" % len(immagini)] if x])
    filo = ('<div class="filo">%s</div>' % prog["fil_rouge"]) if prog.get("fil_rouge") else ""
    piede = ("Provino generato dalla skill editing-portfolio. Le miniature sono incorporate nel file: "
             "funziona anche offline e non richiede nulla di esterno.")

    html = (TEMPLATE
            .replace("__TITOLO__", prog.get("titolo") or "Provino")
            .replace("__SOTTO__", sotto)
            .replace("__FILO__", filo)
            .replace("__PIEDE__", piede)
            .replace("__PESI__", json.dumps(PESI))
            .replace("__DATI__", json.dumps(carico, ensure_ascii=False)))
    out = os.path.abspath(os.path.expanduser(
        args.uscita or os.path.join(os.path.dirname(percorso) or ".", "provino.html")))
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("Scritto: %s (%.1f MB, %d immagini)" % (out, os.path.getsize(out) / 1048576.0, len(immagini)))


if __name__ == "__main__":
    main()
