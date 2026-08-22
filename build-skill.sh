#!/usr/bin/env bash
#
# Rigenera editing-portfolio-publisher.skill dai sorgenti e aggiorna l'inventario
# dentro SKILL.md, sezione "Versione e integrità".
#
# Da eseguire dalla radice del repository, dopo ogni modifica alla skill:
#
#     ./build-skill.sh
#
# Poi: git add -A && git commit. Il push resta sempre un'azione esplicita.
# Infine installare la cartella della skill in Codex oppure distribuire il .skill.
#
# Due proprietà, entrambe imparate rompendole:
#
#   1. La versione si incrementa solo se il contenuto è cambiato davvero.
#      Altrimenti due build a vuoto producono due numeri diversi per la stessa
#      skill, e il repository comincia a dichiarare una versione che nessun
#      pacchetto ha mai avuto.
#
#   2. VERSIONE e SKILL.md si scrivono solo dopo che il pacchetto è stato
#      creato. Se lo script muore a metà (è successo: `rm` vietato su un
#      filesystem montato in sola scrittura), i sorgenti restano coerenti col
#      pacchetto invece di dichiarare una versione mai impacchettata.

set -euo pipefail

CARTELLA="editing-portfolio-publisher"
PACCHETTO="editing-portfolio-publisher.skill"
SKILLMD="$CARTELLA/SKILL.md"
INIZIO="<!-- INIZIO INVENTARIO: generato da build-skill.sh, non modificare a mano -->"
FINE="<!-- FINE INVENTARIO -->"

cd "$(dirname "$0")"

if [ ! -f "$SKILLMD" ]; then
  echo "Errore: $SKILLMD non trovato. Esegui lo script dalla radice del repository." >&2
  exit 1
fi
if ! grep -qF "$INIZIO" "$SKILLMD" || ! grep -qF "$FINE" "$SKILLMD"; then
  echo "Errore: marcatori dell'inventario non trovati in $SKILLMD." >&2
  echo "Ripristina la sezione 'Versione e integrità' prima di rilanciare." >&2
  exit 1
fi

# --- impronta del contenuto, esclusa la riga di versione ---------------------
# Serve a non incrementare il numero quando non è cambiato niente.
impronta() {
  {
    grep -v '^\*\*Versione 2026' "$SKILLMD"
    find "$CARTELLA/agents" "$CARTELLA/references" "$CARTELLA/scripts" -type f \
         \( -name '*.md' -o -name '*.py' -o -name '*.mjs' -o -name '*.json' -o -name '*.yaml' -o -name '*.html' \) \
      | LC_ALL=C sort | xargs cat
  } | shasum -a 256 | cut -c1-12
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

# --- inventario ---------------------------------------------------------------
INVENTARIO=$(mktemp)
{
  echo "**Versione $VERSIONE.** Oltre a questo SKILL.md, la skill è composta dai file"
  echo "qui sotto, e li vuole tutti."
  echo
  echo "| File | Byte |"
  echo "|---|---|"
  find "$CARTELLA/agents" "$CARTELLA/references" "$CARTELLA/scripts" -type f \
       \( -name '*.md' -o -name '*.py' -o -name '*.mjs' -o -name '*.json' -o -name '*.yaml' -o -name '*.html' \) \
    | LC_ALL=C sort \
    | while read -r f; do
        printf "| \`%s\` | %s |\n" "${f#"$CARTELLA"/}" "$(wc -c < "$f" | tr -d ' ')"
      done
} > "$INVENTARIO"
N_FILE=$(grep -c '^| `' "$INVENTARIO")

# --- si scrive su una copia, si sostituisce solo alla fine --------------------
TEMP_SKILLMD=$(mktemp)
python3 - "$SKILLMD" "$INVENTARIO" "$TEMP_SKILLMD" "$INIZIO" "$FINE" <<'PY'
import sys, re
sorgente, inventario, destinazione, inizio, fine = sys.argv[1:6]
testo = open(sorgente, encoding="utf-8").read()
nuovo = open(inventario, encoding="utf-8").read().strip()
testo = re.sub(re.escape(inizio) + r".*?" + re.escape(fine),
               inizio + "\n\n" + nuovo + "\n\n" + fine, testo, flags=re.S)
open(destinazione, "w", encoding="utf-8").write(testo)
PY

TEMP_PACCHETTO=$(mktemp -u).zip
cp "$TEMP_SKILLMD" "$SKILLMD"
if ! zip -q -r -X "$TEMP_PACCHETTO" "$CARTELLA" \
        -x '*.DS_Store' -x '*__pycache__*' -x '*.pyc'; then
  echo "Errore: creazione del pacchetto fallita. VERSIONE non aggiornata." >&2
  exit 1
fi

mv -f "$TEMP_PACCHETTO" "$PACCHETTO"
printf '%s\n%s\n' "$VERSIONE" "$IMPRONTA" > VERSIONE
rm -f "$INVENTARIO" "$TEMP_SKILLMD"

echo "Versione:  $VERSIONE  (contenuto cambiato: $CAMBIATO)"
echo "Impronta:  $IMPRONTA"
echo "File:      $N_FILE oltre a SKILL.md"
echo "Pacchetto: $PACCHETTO ($(wc -c < "$PACCHETTO" | tr -d ' ') byte)"

if [ "$CAMBIATO" = "no" ]; then
  echo
  echo "Niente è cambiato dai sorgenti: versione e pacchetto restano quelli."
  exit 0
fi

echo
echo "Ora, nell'ordine:"
echo "  1. git add -A && git commit -m \"...\""
echo "  2. installa la cartella $CARTELLA nella directory delle skill di Codex"
echo
echo "Il push del repository resta separato e richiede conferma esplicita."
