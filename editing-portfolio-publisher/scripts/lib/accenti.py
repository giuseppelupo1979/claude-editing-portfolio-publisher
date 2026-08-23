"""Accenti veri al posto degli apostrofi, in un posto solo.

Perche' esiste questo modulo. Scrivere ``perche'`` invece di ``perché`` e'
un refuso da tastiera che chi scrive non vede piu' dopo la seconda riga, e che
chi legge vede subito. Nell'editing quelle stringhe finiscono stampate accanto
alle fotografie; in pubblicazione finiscono su un sito pubblico, dentro il
titolo di una galleria e dentro gli alt text, dove restano finche' qualcuno non
li corregge a mano nel CMS.

Quindi il controllo sta in due punti, con due severita' diverse:

- ``genera_testi.py`` lo riporta fra gli avvisi, perche' li' il testo e' ancora
  una bozza e l'autore puo' decidere;
- ``genera_payload_pubblicazione.py`` lo fa fallire, perche' li' il testo sta
  per uscire di casa.
"""

from __future__ import annotations

import re

# (forma sbagliata, forma giusta). Le voci sono minuscole salvo quando la
# maiuscola cambia il caso, come "E'" a inizio frase.
ACCENTI_APOSTROFATI: list[tuple[str, str]] = [
    ("e'", "è"), ("E'", "È"),
    ("perche'", "perché"), ("poiche'", "poiché"), ("benche'", "benché"),
    ("finche'", "finché"), ("affinche'", "affinché"), ("nonche'", "nonché"),
    ("piu'", "più"), ("puo'", "può"), ("gia'", "già"), ("cosi'", "così"),
    ("cioe'", "cioè"), ("percio'", "perciò"), ("pero'", "però"),
    ("citta'", "città"), ("meta'", "metà"), ("verita'", "verità"),
    ("liberta'", "libertà"), ("realta'", "realtà"), ("novita'", "novità"),
    ("qualita'", "qualità"), ("quantita'", "quantità"), ("attivita'", "attività"),
    ("possibilita'", "possibilità"), ("profondita'", "profondità"),
    ("identita'", "identità"), ("intensita'", "intensità"), ("umanita'", "umanità"),
    ("meta'", "metà"), ("eta'", "età"), ("liberta'", "libertà"),
    ("se'", "sé"), ("ne'", "né"),
    ("sara'", "sarà"), ("verra'", "verrà"), ("andra'", "andrà"),
    ("fara'", "farà"), ("dara'", "darà"), ("stara'", "starà"),
    ("li'", "lì"), ("la'", "là"),
]

# Nomi propri che vengono scritti spesso senza accento. Non sono refusi di
# tastiera ma errori di trascrizione, e sbagliano allo stesso modo.
NOMI_ACCENTATI: list[tuple[str, str]] = [
    ("Ballaro", "Ballarò"),
]

_TUTTE = ACCENTI_APOSTROFATI + NOMI_ACCENTATI


def accenti_apostrofati(testo: object) -> list[tuple[str, str]]:
    """Elenca le coppie (sbagliata, giusta) trovate in una stringa.

    Il confine e' costruito a mano invece che con ``\\b`` perche' l'apostrofo
    finale fa parte della forma sbagliata: senza, ``e'`` verrebbe trovato dentro
    ``perche'`` e il referto direbbe due cose per un errore solo.
    """
    if not isinstance(testo, str) or not testo:
        return []
    trovati: list[tuple[str, str]] = []
    for sbagliata, giusta in _TUTTE:
        if re.search(r"(?<![\w'])" + re.escape(sbagliata) + r"(?![\w'])", testo):
            if (sbagliata, giusta) not in trovati:
                trovati.append((sbagliata, giusta))
    return trovati


def correggi(testo: str) -> str:
    """Applica le correzioni. Utile per riparare, non per nascondere il problema."""
    for sbagliata, giusta in _TUTTE:
        testo = re.sub(r"(?<![\w'])" + re.escape(sbagliata) + r"(?![\w'])", giusta, testo)
    return testo
