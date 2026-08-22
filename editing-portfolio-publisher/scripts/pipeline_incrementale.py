#!/usr/bin/env python3
"""Preflight, approvazione e build incrementale dei deliverable editoriali.

Il file di stato conserva SHA-256 degli input e il grafo delle dipendenze. Un
file invariato per dimensione e mtime riusa l'hash gia' calcolato; ``--rehash``
forza una verifica completa. Nessun comando pubblica sul CMS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


VERSION = 1
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp",
    ".heic", ".heif", ".dng", ".nef", ".cr2", ".cr3", ".arw",
    ".raf", ".rw2", ".orf", ".pef",
}
SCRIPT_DIR = Path(__file__).resolve().parent


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def file_sha(path: Path, cache: dict[str, Any], rehash: bool = False) -> str:
    stat = path.stat()
    key = str(path.resolve())
    previous = cache.get(key) or {}
    if (
        not rehash
        and previous.get("size") == stat.st_size
        and previous.get("mtime_ns") == stat.st_mtime_ns
        and previous.get("sha256")
    ):
        return str(previous["sha256"])
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    result = digest.hexdigest()
    cache[key] = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": result}
    return result


def path_signature(path: Path, cache: dict[str, Any], rehash: bool = False) -> Any:
    if not path.exists():
        return None
    if path.is_file():
        return {"file": path.name, "sha256": file_sha(path, cache, rehash)}
    files = []
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        files.append({
            "file": child.relative_to(path).as_posix(),
            "sha256": file_sha(child, cache, rehash),
        })
    return files


def selected_images(source: Path) -> list[Path]:
    groups: dict[str, list[Path]] = {}
    for path in source.iterdir():
        if path.name.startswith(".") or not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        groups.setdefault(path.stem.lower(), []).append(path)
    selected = []
    for group in groups.values():
        preferred = sorted(p for p in group if p.suffix.lower() in {".jpg", ".jpeg"})
        selected.append((preferred or sorted(group))[0])
    return sorted(selected, key=lambda p: p.name.lower())


def source_inventory(source: Path, cache: dict[str, Any], rehash: bool) -> dict[str, Any]:
    files = []
    for path in selected_images(source):
        stat = path.stat()
        files.append({
            "file": path.name,
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": file_sha(path, cache, rehash),
        })
    content = [{"file": item["file"], "sha256": item["sha256"]} for item in files]
    return {"hash": canonical_hash(content), "count": len(files), "files": files}


def image_projection(analysis: dict[str, Any], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    result = []
    for image in analysis.get("immagini") or []:
        if not isinstance(image, dict):
            continue
        result.append({key: image.get(key) for key in keys if key in image})
    return result


def projections(analysis: dict[str, Any]) -> dict[str, Any]:
    project = analysis.get("progetto") or {}
    text_project = {
        key: project.get(key) for key in (
            "titolo", "sottotitolo", "autore", "titoli_candidati", "introduzione",
            "introduzione_posizione", "registro_introduzione", "statement",
            "nota_autore", "registro_didascalie",
        ) if key in project
    }
    text_images = image_projection(
        analysis, ("id", "file", "titolo", "descrizione", "didascalia", "place", "lat", "lng")
    )
    return {
        "texts": {
            "project": text_project,
            "images": text_images,
            "sequence": analysis.get("sequenza"),
            "galleries": analysis.get("gallerie"),
        },
        "table": {
            "destination": project.get("destinazione"),
            "images": image_projection(
                analysis,
                ("id", "file", "titolo", "genere", "voti", "verdetto", "ruolo", "cluster",
                 "cieco", "registro_tonale", "densita", "forza_principale", "limite_principale",
                 "didascalia"),
            ),
            "sequence": analysis.get("sequenza"),
            "clusters": analysis.get("cluster"),
            "galleries": analysis.get("gallerie"),
            "discarded": analysis.get("scarti"),
        },
        "preview": {
            "project": text_project | {
                "modalita": project.get("modalita"),
                "destinazione": project.get("destinazione"),
                "fil_rouge": project.get("fil_rouge"),
                "copertina": project.get("copertina"),
                "copertina_motivazione": project.get("copertina_motivazione"),
                "copertina_alternative": project.get("copertina_alternative"),
            },
            "images": image_projection(
                analysis,
                ("id", "file", "thumb", "titolo", "genere", "voti", "verdetto", "ruolo",
                 "cluster", "didascalia", "descrizione", "cieco", "note", "forza_principale",
                 "limite_principale"),
            ),
            "clusters": analysis.get("cluster"),
            "sequence": analysis.get("sequenza"),
            "discarded": analysis.get("scarti"),
        },
        "dummy": {
            "project": text_project | {
                "copertina": project.get("copertina"),
                "colophon": project.get("colophon"),
            },
            "images": image_projection(
                analysis, ("id", "file", "thumb", "titolo", "descrizione", "didascalia", "place", "lat", "lng")
            ),
            "sequence": analysis.get("sequenza"),
        },
        "publication": {
            "publication": analysis.get("pubblicazione"),
            "images": image_projection(
                analysis,
                ("id", "file", "descrizione", "didascalia", "camera", "taken_at", "place",
                 "lat", "lng", "location_source", "location_precision"),
            ),
        },
    }


def referenced_thumbs(analysis: dict[str, Any], root: Path, cache: dict[str, Any], rehash: bool) -> Any:
    result = []
    for image in analysis.get("immagini") or []:
        rel = image.get("thumb") or image.get("file")
        if not rel:
            continue
        path = Path(rel)
        path = path if path.is_absolute() else root / path
        result.append({"path": str(rel), "sha256": file_sha(path, cache, rehash) if path.is_file() else None})
    return result


def script_hash(name: str, cache: dict[str, Any], rehash: bool) -> str:
    return file_sha(SCRIPT_DIR / name, cache, rehash)


def artifact_specs(
    source: Path,
    out: Path,
    inventory: dict[str, Any],
    analysis: dict[str, Any] | None,
    profile_id: str | None,
    cache: dict[str, Any],
    rehash: bool,
) -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {
        "ingest": {
            "input": canonical_hash({
                "source": inventory["hash"],
                "script": script_hash("prepara_provino.py", cache, rehash),
                "options": {"lato_thumb": 1024, "per_griglia": 12, "lato_griglia": 2000},
            }),
            "outputs": [out / "metriche.json", out / "metriche.csv", out / "firma.json",
                        out / "coppie_simili.csv", out / "saltati.csv", out / "thumbs", out / "griglie"],
        }
    }
    if not analysis:
        return specs
    parts = projections(analysis)
    metrics_sha = file_sha(out / "metriche.json", cache, rehash) if (out / "metriche.json").is_file() else None
    thumbs = referenced_thumbs(analysis, out, cache, rehash)
    common = {"source": inventory["hash"]}
    specs.update({
        "texts": {
            "input": canonical_hash(common | {"data": parts["texts"], "script": script_hash("genera_testi.py", cache, rehash)}),
            "outputs": [out / "testi.md"],
        },
        "table": {
            "input": canonical_hash(common | {"data": parts["table"], "script": script_hash("esporta_tabella.py", cache, rehash)}),
            "outputs": [out / "tabella.csv"],
        },
        "preview": {
            "input": canonical_hash(common | {"data": parts["preview"], "thumbs": thumbs,
                                                "script": script_hash("genera_provino_html.py", cache, rehash)}),
            "outputs": [out / "provino.html"],
        },
        "dummy": {
            "input": canonical_hash(common | {"data": parts["dummy"], "metrics": metrics_sha,
                                                "thumbs": thumbs,
                                                "script": script_hash("genera_dummy_pdf.py", cache, rehash)}),
            "outputs": [out / "dummy.pdf", out / "dummy.qa.json"],
        },
    })
    if analysis.get("pubblicazione") is not None:
        specs["publication"] = {
            "input": canonical_hash(common | {"data": parts["publication"], "metrics": metrics_sha,
                                                "profile_id": profile_id,
                                                "script": script_hash("genera_payload_pubblicazione.py", cache, rehash)}),
            "outputs": [out / "publication-plan.json"],
        }
    return specs


def output_hash(paths: list[Path], cache: dict[str, Any], rehash: bool) -> str | None:
    signatures = []
    for path in paths:
        signature = path_signature(path, cache, rehash)
        if signature is None or (path.is_dir() and not signature):
            return None
        signatures.append({"path": str(path), "content": signature})
    return canonical_hash(signatures)


def statuses(specs: dict[str, dict[str, Any]], state: dict[str, Any], cache: dict[str, Any], rehash: bool) -> dict[str, Any]:
    result = {}
    previous = state.get("artifacts") or {}
    for name, spec in specs.items():
        current_output = output_hash(spec["outputs"], cache, rehash)
        old = previous.get(name) or {}
        reasons = []
        if old.get("input_hash") != spec["input"]:
            reasons.append("input modificato")
        if current_output is None:
            reasons.append("output mancante")
        elif old.get("output_hash") != current_output:
            reasons.append("output non registrato o modificato")
        result[name] = {
            "status": "stale" if reasons else "current",
            "reasons": reasons,
            "input_hash": spec["input"],
            "output_hash": current_output,
            "outputs": [str(path) for path in spec["outputs"]],
        }
    return result


def approval_document(analysis: dict[str, Any], source_hash: str, profile_id: str | None) -> dict[str, Any]:
    return {
        "source_hash": source_hash,
        "analysis_hash": canonical_hash(analysis),
        "profile_id": profile_id,
        "proposal": {
            "project": analysis.get("progetto"),
            "sequence": analysis.get("sequenza"),
            "galleries": analysis.get("gallerie"),
            "publication": analysis.get("pubblicazione"),
            "images": image_projection(
                analysis,
                ("id", "file", "titolo", "descrizione", "didascalia", "place", "lat", "lng",
                 "location_source", "location_precision"),
            ),
        },
    }


def base_context(args: argparse.Namespace) -> tuple[Path, Path, Path, dict[str, Any], dict[str, Any], dict[str, Any] | None, dict[str, Any]]:
    source = Path(args.cartella).expanduser().resolve()
    if not source.is_dir():
        raise ValueError(f"Cartella non trovata: {source}")
    out = Path(args.uscita).expanduser().resolve() if args.uscita else source / "_analisi"
    state_path = out / ".pipeline-incrementale.json"
    state = load_json(state_path, {"version": VERSION, "file_cache": {}, "artifacts": {}})
    if not isinstance(state, dict) or state.get("version") != VERSION:
        state = {"version": VERSION, "file_cache": {}, "artifacts": {}}
    cache = state.setdefault("file_cache", {})
    inventory = source_inventory(source, cache, args.rehash)
    analysis_path = Path(args.analisi).expanduser().resolve() if args.analisi else out / "analisi.json"
    analysis = load_json(analysis_path) if analysis_path.exists() else None
    return source, out, state_path, state, inventory, analysis, cache


def local_profile(profile_path: str | None) -> tuple[str | None, list[str]]:
    if not profile_path:
        return None, []
    path = Path(profile_path).expanduser().resolve()
    issues = []
    if not path.is_file():
        return None, [f"profilo sito non trovato: {path}"]
    try:
        profile = load_json(path)
    except (OSError, json.JSONDecodeError) as error:
        return None, [f"profilo sito non leggibile: {error}"]
    profile_id = profile.get("id") if isinstance(profile, dict) else None
    if not profile_id:
        issues.append("profilo sito senza id")
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        issues.append(f"profilo sito con permessi {mode:o}, richiesto 600")
    return profile_id, issues


def run_doctor(profile: str) -> dict[str, Any]:
    command = ["node", str(SCRIPT_DIR / "publish_directus.mjs"), "doctor", "--profile", profile]
    result = subprocess.run(command, text=True, capture_output=True)
    return {"ok": result.returncode == 0, "returncode": result.returncode,
            "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def command_preflight(args: argparse.Namespace) -> int:
    source, out, state_path, state, inventory, analysis, cache = base_context(args)
    profile_id, issues = local_profile(args.profile)
    profile_id = args.profile_id or profile_id
    specs = artifact_specs(source, out, inventory, analysis, profile_id, cache, args.rehash)
    artifact_status = statuses(specs, state, cache, args.rehash)
    blockers = list(issues)
    if not inventory["count"]:
        blockers.append("nessuna immagine supportata")
    if analysis is None:
        blockers.append("analisi.json non ancora disponibile: completa l'analisi e la proposta unica")
    approval = None
    if analysis is not None:
        document = approval_document(analysis, inventory["hash"], profile_id)
        approval_hash = canonical_hash(document)
        recorded = state.get("approval") or {}
        approval = {"hash": approval_hash, "approved": recorded.get("hash") == approval_hash}
        if not approval["approved"]:
            blockers.append("proposta editoriale non approvata o modificata")
        if analysis.get("pubblicazione") is not None:
            if not profile_id:
                blockers.append("pubblicazione richiesta ma profile_id non disponibile")
            try:
                from genera_payload_pubblicazione import build_plan
                metrics = load_json(out / "metriche.json") if (out / "metriche.json").exists() else None
                build_plan(analysis, profile_id or "preflight", source, metrics)
            except (OSError, ValueError) as error:
                blockers.append(str(error))
    site_doctor = None
    if args.doctor_site:
        if not args.profile:
            blockers.append("--doctor-site richiede --profile")
        else:
            site_doctor = run_doctor(args.profile)
            if not site_doctor["ok"]:
                blockers.append("doctor Directus non superato")
    state["source"] = inventory
    save_json(state_path, state)
    report = {
        "ok": not blockers,
        "mode": "preflight",
        "source": str(source),
        "analysis_dir": str(out),
        "source_inventory": inventory,
        "approval": approval,
        "artifacts": artifact_status,
        "site_doctor": site_doctor,
        "blockers": blockers,
        "next": "prepare" if artifact_status["ingest"]["status"] == "stale" else (
            "approval" if approval and not approval["approved"] else "build"
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not blockers else 2


def command_approve(args: argparse.Namespace) -> int:
    _, _, state_path, state, inventory, analysis, _ = base_context(args)
    if analysis is None:
        raise ValueError("analisi.json non trovato")
    profile_id, issues = local_profile(args.profile)
    if issues:
        raise ValueError("; ".join(issues))
    profile_id = args.profile_id or profile_id
    document = approval_document(analysis, inventory["hash"], profile_id)
    approval_hash = canonical_hash(document)
    response = {"ok": True, "mode": "approval-preflight", "document": document,
                "authorization_hash": approval_hash, "recorded": False}
    if args.confirm:
        if args.authorization_hash != approval_hash:
            raise ValueError("authorization_hash non coincide con la proposta corrente")
        state["source"] = inventory
        state["approval"] = {"hash": approval_hash, "source_hash": inventory["hash"],
                             "analysis_hash": document["analysis_hash"]}
        save_json(state_path, state)
        response["mode"] = "approval-recorded"
        response["recorded"] = True
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0


def run_checked(command: list[str]) -> None:
    print("Eseguo:", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def record_artifact(name: str, spec: dict[str, Any], state: dict[str, Any], cache: dict[str, Any]) -> None:
    out_hash = output_hash(spec["outputs"], cache, True)
    if out_hash is None:
        raise RuntimeError(f"{name}: output atteso non prodotto")
    state.setdefault("artifacts", {})[name] = {
        "input_hash": spec["input"], "output_hash": out_hash,
        "outputs": [str(path) for path in spec["outputs"]],
    }


def command_build(args: argparse.Namespace) -> int:
    if not args.confirm:
        raise ValueError("build richiede --confirm")
    source, out, state_path, state, inventory, analysis, cache = base_context(args)
    profile_id, issues = local_profile(args.profile)
    if issues:
        raise ValueError("; ".join(issues))
    profile_id = args.profile_id or profile_id
    out.mkdir(parents=True, exist_ok=True)
    specs = artifact_specs(source, out, inventory, analysis, profile_id, cache, args.rehash)
    current = statuses(specs, state, cache, args.rehash)
    wanted = {item.strip() for item in args.only.split(",") if item.strip()} if args.only else set(specs)
    unknown = wanted - set(specs)
    if unknown:
        raise ValueError("artifact non disponibili: " + ", ".join(sorted(unknown)))

    if "ingest" not in wanted and current["ingest"]["status"] == "stale" and wanted - {"ingest"}:
        raise ValueError("ingestione scaduta: esegui prima --only ingest; gli output dipendenti non sono affidabili")

    built = []
    if "ingest" in wanted and current["ingest"]["status"] == "stale":
        run_checked([sys.executable, str(SCRIPT_DIR / "prepara_provino.py"), str(source), "-o", str(out)])
        record_artifact("ingest", specs["ingest"], state, cache)
        state["source"] = inventory
        save_json(state_path, state)
        built.append("ingest")

    if analysis is None:
        print(json.dumps({"ok": True, "built": built,
                          "next": "crea analisi.json, mostra la proposta unica e registra l'approvazione"},
                         ensure_ascii=False, indent=2))
        return 0

    if wanted == {"ingest"}:
        print(json.dumps({"ok": True, "built": built,
                          "skipped_current": ["ingest"] if not built else [],
                          "next": "mostra la proposta editoriale unica e registra l'approvazione"},
                         ensure_ascii=False, indent=2))
        return 0

    document = approval_document(analysis, inventory["hash"], profile_id)
    approval_hash = canonical_hash(document)
    if (state.get("approval") or {}).get("hash") != approval_hash:
        raise ValueError(
            "proposta editoriale non approvata o cambiata: esegui approve senza --confirm, "
            "mostra il documento all'utente, poi registra lo stesso hash"
        )

    # L'ingest puo' avere aggiornato metriche e thumbnail: ricalcola il grafo.
    specs = artifact_specs(source, out, inventory, analysis, profile_id, cache, True)
    current = statuses(specs, state, cache, True)
    analysis_path = Path(args.analisi).expanduser().resolve() if args.analisi else out / "analisi.json"
    commands = {
        "texts": [sys.executable, str(SCRIPT_DIR / "genera_testi.py"), str(analysis_path), "-o", str(out / "testi.md")],
        "table": [sys.executable, str(SCRIPT_DIR / "esporta_tabella.py"), str(analysis_path), "-o", str(out)],
        "preview": [sys.executable, str(SCRIPT_DIR / "genera_provino_html.py"), str(analysis_path),
                    "-o", str(out / "provino.html"), "--radice", str(out)],
        "dummy": [sys.executable, str(SCRIPT_DIR / "genera_dummy_pdf.py"), str(analysis_path),
                  "-o", str(out / "dummy.pdf"), "--radice", str(out),
                  "--metriche", str(out / "metriche.json"), "--qa-strict"],
    }
    if "publication" in specs:
        if not profile_id:
            raise ValueError("publication richiede --profile oppure --profile-id")
        commands["publication"] = [
            sys.executable, str(SCRIPT_DIR / "genera_payload_pubblicazione.py"), str(analysis_path),
            "--profile-id", profile_id, "--source-dir", str(source),
            "--metriche", str(out / "metriche.json"), "-o", str(out / "publication-plan.json"),
        ]
    for name in ("texts", "table", "preview", "dummy", "publication"):
        if name not in wanted or name not in specs or current[name]["status"] == "current":
            continue
        run_checked(commands[name])
        record_artifact(name, specs[name], state, cache)
        save_json(state_path, state)
        built.append(name)
    print(json.dumps({"ok": True, "built": built,
                      "skipped_current": sorted(name for name in wanted if name in current and current[name]["status"] == "current")},
                     ensure_ascii=False, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Pipeline editoriale incrementale basata su SHA-256")
    sub = root.add_subparsers(dest="command", required=True)
    for name in ("preflight", "approve", "build"):
        command = sub.add_parser(name)
        command.add_argument("cartella")
        command.add_argument("-o", "--uscita")
        command.add_argument("--analisi")
        command.add_argument("--profile")
        command.add_argument("--profile-id")
        command.add_argument("--rehash", action="store_true")
        if name == "preflight":
            command.add_argument("--doctor-site", action="store_true")
        if name == "approve":
            command.add_argument("--confirm", action="store_true")
            command.add_argument("--authorization-hash")
        if name == "build":
            command.add_argument("--confirm", action="store_true")
            command.add_argument("--only", help="artifact separati da virgola: ingest,texts,table,preview,dummy,publication")
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "preflight":
        return command_preflight(args)
    if args.command == "approve":
        return command_approve(args)
    return command_build(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Errore: {error}", file=sys.stderr)
        raise SystemExit(2)
