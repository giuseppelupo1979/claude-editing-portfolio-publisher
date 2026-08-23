#!/usr/bin/env python3
"""Generate a deterministic publication plan from an editing analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_PHOTO_TEXT = ("title_it", "title_en", "alt_it", "alt_en")
REQUIRED_GALLERY_TEXT = (
    "slug",
    "title_it",
    "title_en",
    "description_it",
    "description_en",
    "cover_file",
)


def fail(message: str) -> None:
    raise ValueError(message)


def nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"Campo obbligatorio mancante o vuoto: {label}")
    return value.strip()


def publication_block(analysis: dict[str, Any]) -> dict[str, Any]:
    block = analysis.get("pubblicazione")
    if not isinstance(block, dict):
        fail(
            "analisi.json non contiene il blocco 'pubblicazione'. "
            "Compila galleria, foto e testi prima di generare il piano."
        )
    return block


def image_lookup(analysis: dict[str, Any]) -> dict[str, dict[str, Any]]:
    images = analysis.get("immagini")
    if not isinstance(images, list):
        fail("analisi.json non contiene una lista 'immagini' valida")
    lookup = {}
    for image in images:
        if not isinstance(image, dict) or not image.get("id"):
            fail("Ogni elemento di 'immagini' deve avere un id")
        lookup[str(image["id"])] = image
    return lookup


def metrics_lookup(metrics: Any) -> dict[str, dict[str, Any]]:
    rows = metrics.get("immagini") if isinstance(metrics, dict) else metrics
    if not isinstance(rows, list):
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in (row.get("id"), row.get("file")):
            if key:
                lookup[str(key)] = row
    return lookup


def first_value(*candidates: tuple[Any, str]) -> tuple[Any, str | None]:
    for value, source in candidates:
        if value is not None and value != "":
            return value, source
    return None, None


def camera_from_metric(metric: dict[str, Any]) -> str | None:
    values = [str(metric.get(key)).strip() for key in ("corpo", "ottica") if metric.get(key)]
    return " - ".join(values) or None


def resolve_location(
    raw: dict[str, Any],
    image: dict[str, Any],
    metric: dict[str, Any],
    defaults: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    confirmed_defaults = defaults if defaults.get("confirmed_by_user") is True else {}
    values: dict[str, Any] = {}
    sources: set[str] = set()
    key_sources: dict[str, str | None] = {}
    raw_source = raw.get("location_source") or "explicit"
    analysis_source = image.get("location_source") or "analysis"
    for key in ("place", "lat", "lng"):
        value, source = first_value(
            (raw.get(key), raw_source),
            (image.get(key), analysis_source),
            (metric.get(key), "exif"),
            (confirmed_defaults.get(key), "project-default"),
        )
        values[key] = value
        key_sources[key] = source
        if source:
            sources.add(source)

    missing = [key for key in ("place", "lat", "lng") if values[key] in (None, "")]
    if missing:
        return values, missing
    try:
        values["lat"] = float(values["lat"])
        values["lng"] = float(values["lng"])
    except (TypeError, ValueError):
        return values, ["lat/lng non numeriche"]
    if not -90 <= values["lat"] <= 90:
        missing.append("lat fuori intervallo")
    if not -180 <= values["lng"] <= 180:
        missing.append("lng fuori intervallo")
    if missing:
        return values, missing

    # "exact" e' il grado massimo di certezza e finisce pubblico sulla pagina
    # Mappa. Lo assegna soltanto il GPS del file, oppure l'autore in modo
    # esplicito: una coordinata scritta a mano resta una stima, e va detto.
    # Conta la provenienza di lat/lng, non quella dell'etichetta "place".
    precision = raw.get("location_precision") or image.get("location_precision")
    if not precision and "project-default" in sources:
        precision = confirmed_defaults.get("precision", "approximate")
    if not precision:
        coordinate_sources = {key_sources["lat"], key_sources["lng"]}
        precision = "exact" if coordinate_sources == {"exif"} else "approximate"
    if precision not in {"exact", "approximate"}:
        return values, ["location_precision non valida"]
    values["location_precision"] = precision
    allowed_sources = {"explicit", "analysis", "exif", "reverse-geocoded", "project-default"}
    if not sources.issubset(allowed_sources):
        return values, ["location_source non valida"]
    values["location_source"] = next(iter(sources)) if len(sources) == 1 else "mixed"
    return values, []


def normalize_gallery(raw: dict[str, Any]) -> dict[str, Any]:
    gallery = {key: nonempty(raw.get(key), f"gallery.{key}") for key in REQUIRED_GALLERY_TEXT}
    action = raw.get("action", "create")
    if action not in {"create", "existing"}:
        fail("gallery.action deve essere 'create' oppure 'existing'")
    existing_id = raw.get("existing_id")
    if action == "existing" and not existing_id:
        fail("gallery.existing_id è obbligatorio quando action='existing'")
    gallery.update(
        {
            "action": action,
            "existing_id": existing_id,
            "sort": raw.get("sort"),
            "filter_flag": raw.get("filter_flag"),
        }
    )
    return {
        "action": gallery["action"],
        "existing_id": gallery["existing_id"],
        "slug": gallery["slug"],
        "title_it": gallery["title_it"],
        "title_en": gallery["title_en"],
        "description_it": gallery["description_it"],
        "description_en": gallery["description_en"],
        "cover_file": gallery["cover_file"],
        "sort": gallery["sort"],
        "filter_flag": gallery["filter_flag"],
    }


def normalize_photos(
    raw_photos: Any,
    images: dict[str, dict[str, Any]],
    metrics: dict[str, dict[str, Any]],
    location_defaults: dict[str, Any],
) -> list[dict[str, Any]]:
    if not isinstance(raw_photos, list) or not raw_photos:
        fail("pubblicazione.photos deve essere una lista non vuota")

    result = []
    seen_files: set[str] = set()
    missing_locations: list[str] = []
    for index, raw in enumerate(raw_photos, start=1):
        if not isinstance(raw, dict):
            fail(f"pubblicazione.photos[{index}] non è un oggetto")
        image_id = raw.get("id")
        image = images.get(str(image_id)) if image_id is not None else None
        image = image or {}
        file_name = raw.get("file") or (image or {}).get("file")
        file_name = nonempty(file_name, f"photos[{index}].file")
        if file_name in seen_files:
            fail(f"File duplicato nel piano: {file_name}")
        seen_files.add(file_name)

        photo = {
            "order": raw.get("order", index),
            "file": file_name,
        }
        if not isinstance(photo["order"], int) or photo["order"] < 1:
            fail(f"Ordine non valido per {file_name}")
        for key in REQUIRED_PHOTO_TEXT:
            photo[key] = nonempty(raw.get(key), f"{file_name}.{key}")
        metric = metrics.get(str(image_id)) or metrics.get(file_name) or {}
        location, missing = resolve_location(raw, image, metric, location_defaults)
        photo.update(location)
        if missing:
            missing_locations.append(f"{file_name} ({', '.join(missing)})")
        photo["camera"] = raw.get("camera") or image.get("camera") or camera_from_metric(metric)
        photo["taken_at"] = raw.get("taken_at") or image.get("taken_at") or metric.get("data")
        for key in ("featured", "street", "portrait"):
            photo[key] = bool(raw.get(key, False))
        photo["description_working"] = raw.get("description_working") or image.get("descrizione")
        photo["caption"] = raw.get("caption") or image.get("didascalia")
        result.append(photo)

    result.sort(key=lambda photo: photo["order"])
    orders = [photo["order"] for photo in result]
    if len(set(orders)) != len(orders):
        fail("Gli ordini delle foto devono essere univoci")
    if missing_locations:
        details = "; ".join(missing_locations)
        fail(
            "Geolocalizzazione incompleta: " + details + ". "
            "Prima della pubblicazione chiedi all'utente luogo e coordinate. "
            "Se tutta la serie condivide il luogo, compila pubblicazione.location_defaults "
            "con place, lat, lng, precision e confirmed_by_user=true."
        )
    return result


def build_plan(
    analysis: dict[str, Any], profile_id: str, source_dir: Path, metrics: Any = None
) -> dict[str, Any]:
    block = publication_block(analysis)
    gallery_raw = block.get("gallery")
    if not isinstance(gallery_raw, dict):
        fail("pubblicazione.gallery deve essere un oggetto")
    gallery = normalize_gallery(gallery_raw)
    defaults = block.get("location_defaults") or {}
    if not isinstance(defaults, dict):
        fail("pubblicazione.location_defaults deve essere un oggetto")
    photos = normalize_photos(
        block.get("photos"), image_lookup(analysis), metrics_lookup(metrics), defaults
    )
    if gallery["cover_file"] not in {photo["file"] for photo in photos}:
        fail("gallery.cover_file deve appartenere alle foto selezionate")

    return {
        "plan_version": 2,
        "profile_id": profile_id,
        "source_dir": str(source_dir.expanduser().resolve()),
        "gallery": gallery,
        "photos": photos,
        "approval": {
            "approved": False,
            "approved_at": None,
            "approved_by": None,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera publication-plan.json dal blocco pubblicazione di analisi.json"
    )
    parser.add_argument("analysis", type=Path, help="Percorso di analisi.json")
    parser.add_argument("--profile-id", required=True, help="ID del profilo sito locale")
    parser.add_argument("--source-dir", type=Path, help="Cartella che contiene gli originali")
    parser.add_argument("--metriche", type=Path, help="metriche.json con EXIF e coordinate GPS")
    parser.add_argument("-o", "--output", type=Path, help="File JSON di destinazione")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    analysis_path = args.analysis.expanduser().resolve()
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    source_dir = args.source_dir or analysis_path.parent.parent
    metrics_path = (args.metriche or analysis_path.with_name("metriche.json")).expanduser().resolve()
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else None
    output = args.output or analysis_path.with_name("publication-plan.json")
    plan = build_plan(analysis, args.profile_id, source_dir, metrics)
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Scritto: {output}")
    print(f"Galleria: {plan['gallery']['slug']} ({len(plan['photos'])} foto)")
    print("Stato: proposta non approvata")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Errore: {error}")
        raise SystemExit(2)
