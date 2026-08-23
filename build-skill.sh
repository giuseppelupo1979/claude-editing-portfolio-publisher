#!/usr/bin/env bash
#
# Rigenera editing-portfolio-publisher.skill dai sorgenti, riscrive il manifest
# di integrita' e aggiorna la riga di versione dentro SKILL.md.
#
# Da eseguire dalla radice del repository, dopo ogni modifica alla skill:
#
#     ./build-skill.sh
#
# Poi: git add -A && git commit. Il push resta sempre un'azione esplicita.
# Infine installare la cartella della skill nel proprio ambiente.
#
# Tre proprieta', le prime due imparate rompendole:
#
#   1. La versione si incrementa solo se il contenuto e' cambiato davvero.
#      Altrimenti due build a vuoto producono due numeri diversi per la stessa
#      skill, e il repository comincia a dichiarare una versione che nessun
#      pacchetto ha mai avuto.
#
#   2. VERSIONE si scrive solo dopo che il pacchetto e' stato creato. Se lo
#      script muore a meta' (e' successo: `rm` vietato su un filesystem montato
#      in sola lettura), i sorgenti restano coerenti col pacchetto invece di
#      dichiarare una versione mai impacchettata.
#
#   3. L'inventario non vive piu' dentro SKILL.md ma in
#      references/integrita.json, con byte e SHA-256 di ogni file, SKILL.md
#      compreso. Serve a rendere il controllo di F0 eseguibile da un comando
#      invece che da un confronto a occhio: un file troncato o modificato non
#      passa piu' inosservato, e le sottocartelle come scripts/lib vengono
#      controllate come tutto il resto.

set -euo pipefail

CARTELLA="editing-portfolio-publisher"
PACCHETTO="editing-portfolio-publisher.skill"
SKILLMD="$CARTELLA/SKILL.md"
MANIFEST="$CARTELLA/references/integrita.json"
INIZIO="<!-- INIZIO VERSIONE: generato da build-skill.sh, non modificare a mano -->"
FINE="<!-- FINE VERSIONE -->"

cd "$(dirname "$0")"

if [ ! -f "$SKILLMD" ]; then
  echo "Errore: $SKILLMD non trovato. Esegui lo script dalla radice del repository." >&2
  exit 1
fi
if ! grep -qF "$INIZIO" "$SKILLMD" || ! grep -qF "$FINE" "$SKILLMD"; then
  echo "Errore: marcatori della versione non trovati in $SKILLMD." >&2
  echo "Ripristina la sezione 'Versione e integrita' prima di rilanciare." >&2
  exit 1
fi

# --- elenco dei file della skill ---------------------------------------------
# integrita.json e' escluso: e' derivato dagli altri e non puo' contenere se stesso.
elenco_file() {
  find "$CARTELLA/agents" "$CARTELLA/references" "$CARTELLA/scripts" -type f \
       \( -name '*.md' -o -name '*.py' -o -name '*.mjs' -o -name '*.json' -o -name '*.yaml' -o -name '*.html' \) \
       ! -path "$MANIFEST" \
    | LC_ALL=C sort
}

somma() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$@"
  else
    sha256sum "$@"
  fi
}

# --- impronta del contenuto, esclusa la riga di versione ---------------------
# Serve a non incrementare il numero quando non e' cambiato niente.
impronta() {
  {
    grep -v '^\*\*Versione 20' "$SKILLMD"
    elenco_file | xargs cat
  } | somma | cut -c1-12
}
IMPRONTA=$(impronta)

VERSIONE_PRECEDENTE=""
IMPRONTA_PRECEDENTE=""
if [ -f VERSIONE ]; then
  VERSIONE_PRECEDENTE=$(awk 'NR==1{print $1}' VERSIONE)
  IMPRONTA_PRECEDENTE=$(awk 'NR==2{print $1}' VERSIONE)
fi

if [ -n "$IMPRONTA_PRECEDENTE" ] && [ "$IMPRONTA" = "$IMPRONTA_PRECEDENTE" ]; then
  VERSIONE="$VERSIONE_PRECEDENTE"
  CAMBIATO="no"
else
  OGGI=$(date +%Y-%m-%d)
  PROG=1
  if [[ "$VERSIONE_PRECEDENTE" == "$OGGI".* ]]; then
    PROG=$(( ${VERSIONE_PRECEDENTE##*.} + 1 ))
  fi
  VERSIONE="$OGGI.$PROG"
  CAMBIATO="si"
fi

# Se il contenuto non e' cambiato non si tocca niente: riscrivere SKILL.md, il
# manifest e lo zip aggiornerebbe le date dei file e produrrebbe un pacchetto
# diverso a parita' di contenuto. La CI si appoggia a questa proprieta' per
# capire se chi ha committato aveva davvero rigenerato il pacchetto.
if [ "$CAMBIATO" = "no" ] && [ -f "$PACCHETTO" ] && [ -f "$MANIFEST" ]; then
  echo "Versione:  $VERSIONE  (contenuto cambiato: no)"
  echo "Impronta:  $IMPRONTA"
  python3 "$CARTELLA/scripts/verifica_integrita.py"
  echo
  echo "Niente e' cambiato dai sorgenti: versione, manifest e pacchetto restano quelli."
  exit 0
fi

# --- riga di versione dentro SKILL.md ----------------------------------------
BLOCCO=$(mktemp)
{
  echo "**Versione $VERSIONE.** L'inventario completo, con byte e SHA-256 di ogni"
  echo "file compreso questo, sta in \`references/integrita.json\` e si controlla con"
  echo "\`scripts/verifica_integrita.py\`."
} > "$BLOCCO"

TEMP_SKILLMD=$(mktemp)
python3 - "$SKILLMD" "$BLOCCO" "$TEMP_SKILLMD" "$INIZIO" "$FINE" <<'PY'
import sys, re
sorgente, blocco, destinazione, inizio, fine = sys.argv[1:6]
testo = open(sorgente, encoding="utf-8").read()
nuovo = open(blocco, encoding="utf-8").read().strip()
testo = re.sub(re.escape(inizio) + r".*?" + re.escape(fine),
               inizio + "\n\n" + nuovo + "\n\n" + fine, testo, flags=re.S)
open(destinazione, "w", encoding="utf-8").write(testo)
PY
cp "$TEMP_SKILLMD" "$SKILLMD"

# --- manifest di integrita' ---------------------------------------------------
# Scritto dopo SKILL.md, che ormai e' definitivo, e prima dello zip, cosi'
# il pacchetto contiene un manifest che descrive esattamente il pacchetto.
ELENCO=$(mktemp)
elenco_file > "$ELENCO"

# L'elenco passa da un file e non da una pipe: `python3 -` legge il programma da
# stdin, quindi un heredoc e una pipe non possono coesistere sullo stesso comando.
python3 - "$SKILLMD" "$MANIFEST" "$VERSIONE" "$IMPRONTA" "$CARTELLA" "$ELENCO" <<'PY'
import hashlib, json, sys
from pathlib import Path

skillmd, destinazione, versione, impronta, cartella, elenco = sys.argv[1:7]
radice = Path(cartella)
percorsi = [Path(riga.strip()) for riga in Path(elenco).read_text().splitlines() if riga.strip()]
percorsi.insert(0, Path(skillmd))

def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

voci = [
    {
        "path": path.relative_to(radice).as_posix(),
        "byte": path.stat().st_size,
        "sha256": sha256(path),
    }
    for path in percorsi
]
Path(destinazione).write_text(
    json.dumps({"versione": versione, "impronta": impronta, "file": voci},
               ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY
rm -f "$ELENCO"

N_FILE=$(python3 -c "import json,sys; print(len(json.load(open(sys.argv[1]))['file']))" "$MANIFEST")

# --- pacchetto -----------------------------------------------------------------
# Lo zip si costruisce da una copia con date normalizzate: uno zip conserva la
# data di ogni file, quindi lo stesso contenuto prodotto in momenti diversi (o su
# un checkout appena fatto) darebbe byte diversi. Con le date fissate, contenuto
# uguale significa pacchetto identico, ed e' quello che la CI puo' verificare.
TEMP_PACCHETTO=$(mktemp -u).zip
STAGING=$(mktemp -d)
cp -R "$CARTELLA" "$STAGING/$CARTELLA"
find "$STAGING" -exec touch -t 202001010000.00 {} +
if ! ( cd "$STAGING" && zip -q -r -X "$TEMP_PACCHETTO" "$CARTELLA" \
        -x '*.DS_Store' -x '*__pycache__*' -x '*.pyc' ); then
  echo "Errore: creazione del pacchetto fallita. VERSIONE non aggiornata." >&2
  rm -rf "$STAGING"
  exit 1
fi
rm -rf "$STAGING"

mv -f "$TEMP_PACCHETTO" "$PACCHETTO"
printf '%s\n%s\n' "$VERSIONE" "$IMPRONTA" > VERSIONE
rm -f "$BLOCCO" "$TEMP_SKILLMD"

# --- postcondizione: il manifest deve descrivere davvero questi file ----------
if ! python3 "$CARTELLA/scripts/verifica_integrita.py"; then
  echo "Errore: il manifest appena scritto non verifica. Pacchetto sospetto." >&2
  exit 1
fi

echo "Versione:  $VERSIONE  (contenuto cambiato: $CAMBIATO)"
echo "Impronta:  $IMPRONTA"
echo "File:      $N_FILE nel manifest, SKILL.md compreso"
echo "Pacchetto: $PACCHETTO ($(wc -c < "$PACCHETTO" | tr -d ' ') byte)"

if [ "$CAMBIATO" = "no" ]; then
  echo
  echo "Niente e' cambiato dai sorgenti: versione e pacchetto restano quelli."
  exit 0
fi

echo
echo "Ora, nell'ordine:"
echo "  1. git add -A && git commit -m \"...\""
echo "  2. installa la cartella $CARTELLA nella directory delle skill"
echo
echo "Il push del repository resta separato e richiede conferma esplicita."
