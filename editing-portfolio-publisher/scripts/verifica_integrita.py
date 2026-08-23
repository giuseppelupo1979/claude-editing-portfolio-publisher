#!/usr/bin/env python3
"""Controllo di integrita' della skill: un comando, una riga di risposta.

Confronta ogni file della skill con byte e SHA-256 registrati in
``references/integrita.json``, generato da ``build-skill.sh``.

Perche' non basta un ``ls``. Il controllo che c'era prima elencava le cartelle e
lasciava il confronto all'occhio: vedeva sparire un file, non vedeva un file
troncato a meta', e non vedeva affatto le sottocartelle, quindi
``scripts/lib/publisher-core.mjs`` non veniva mai controllato. Un editing intero
puo' dipendere da uno script che c'e' ma e' incompleto.

Uso::

    python3 scripts/verifica_integrita.py
    python3 scripts/verifica_integrita.py --json

Uscita 0 se la copia e' integra, 1 se non lo e', 2 se manca il manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
MANIFEST = SKILL_DIR / "references" / "integrita.json"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(manifest: dict) -> list[str]:
    problems: list[str] = []
    for entry in manifest.get("file", []):
        relative = entry["path"]
        path = SKILL_DIR / relative
        if not path.is_file():
            problems.append(f"{relative}: mancante")
            continue
        size = path.stat().st_size
        if size != entry["byte"]:
            problems.append(f"{relative}: {entry['byte']} byte attesi, {size} trovati")
            continue
        if sha256_of(path) != entry["sha256"]:
            problems.append(f"{relative}: contenuto diverso da quello pacchettizzato")
    declared = {entry["path"] for entry in manifest.get("file", [])}
    for path in sorted(SKILL_DIR.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(SKILL_DIR).as_posix()
        if relative == "references/integrita.json" or relative in declared:
            continue
        if path.suffix in {".md", ".py", ".mjs", ".json", ".yaml", ".html"}:
            problems.append(f"{relative}: presente ma non dichiarato nel manifest")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica byte e SHA-256 dei file della skill")
    parser.add_argument("--json", action="store_true", dest="as_json", help="referto in JSON")
    args = parser.parse_args()

    if not MANIFEST.is_file():
        message = (
            "Integrita: MANIFEST ASSENTE. references/integrita.json non c'e': "
            "stai lavorando su una copia vecchia o incompleta della skill. "
            "Fermati e chiedi all'utente di reinstallare editing-portfolio-publisher."
        )
        print(json.dumps({"ok": False, "manifest": False}) if args.as_json else message,
              file=sys.stderr)
        return 2

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    problems = verify(manifest)
    version = manifest.get("versione", "sconosciuta")
    count = len(manifest.get("file", []))

    if args.as_json:
        print(json.dumps({"ok": not problems, "versione": version, "file": count,
                          "problemi": problems}, ensure_ascii=False, indent=2))
        return 0 if not problems else 1

    if not problems:
        print(f"Integrita: OK. Versione {version}, {count} file, byte e SHA-256 attesi.")
        return 0

    print(f"Integrita: FALLITA. Versione dichiarata {version}, {len(problems)} problemi: "
          + "; ".join(problems[:6])
          + ("; e altri" if len(problems) > 6 else "")
          + ". Non proseguire: chiedi all'utente di reinstallare la skill.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
