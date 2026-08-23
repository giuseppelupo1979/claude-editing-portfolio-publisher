import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "editing-portfolio-publisher"
    / "scripts"
    / "pipeline_incrementale.py"
)
SPEC = importlib.util.spec_from_file_location("incremental", SCRIPT)
INCREMENTAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INCREMENTAL)


def analysis():
    return {
        "progetto": {
            "titolo": "Soglie",
            "introduzione": "Una introduzione.",
            "statement": "Uno statement.",
        },
        "immagini": [
            {
                "id": "P001",
                "file": "one.jpg",
                "thumb": "thumbs/P001_one.jpg",
                "titolo": "La soglia",
                "descrizione": "Una figura davanti a una porta.",
                "didascalia": "La porta trattiene la figura.",
                "place": "Napoli, Italia",
                "lat": 40.8518,
                "lng": 14.2681,
            }
        ],
        "sequenza": {"spread": [[None, "P001"]]},
        "gallerie": [{"nome": "Soglie", "ordine": ["P001"], "esca": "P001"}],
        "pubblicazione": {
            "gallery": {"slug": "soglie"},
            "photos": [{"id": "P001", "place": "Napoli, Italia", "lat": 40.8518, "lng": 14.2681}],
        },
    }


class IncrementalPipelineTest(unittest.TestCase):
    def test_colophon_invalidates_only_dummy_projection(self):
        before = INCREMENTAL.projections(analysis())
        changed = analysis()
        changed["progetto"]["colophon"] = {"Edizione": ["Prima prova."]}
        after = INCREMENTAL.projections(changed)

        self.assertNotEqual(before["dummy"], after["dummy"])
        for name in ("texts", "table", "preview", "publication"):
            self.assertEqual(before[name], after[name], name)

    def test_publication_change_invalidates_only_publication_projection(self):
        before = INCREMENTAL.projections(analysis())
        changed = analysis()
        changed["pubblicazione"]["gallery"]["slug"] = "nuove-soglie"
        after = INCREMENTAL.projections(changed)

        self.assertNotEqual(before["publication"], after["publication"])
        for name in ("texts", "table", "preview", "dummy"):
            self.assertEqual(before[name], after[name], name)

    def test_image_location_change_invalidates_texts_dummy_and_publication(self):
        before = INCREMENTAL.projections(analysis())
        changed = analysis()
        changed["immagini"][0].update({"place": "Tokyo, Giappone", "lat": 35.6764, "lng": 139.6500})
        after = INCREMENTAL.projections(changed)

        for name in ("texts", "dummy", "publication"):
            self.assertNotEqual(before[name], after[name], name)
        self.assertEqual(before["table"], after["table"])

    def test_approval_hash_binds_source_and_complete_editorial_proposal(self):
        first = INCREMENTAL.approval_document(analysis(), "source-a", "site-a")
        changed = analysis()
        changed["immagini"][0]["place"] = "Tokyo, Giappone"
        second = INCREMENTAL.approval_document(changed, "source-a", "site-a")
        third = INCREMENTAL.approval_document(analysis(), "source-b", "site-a")

        self.assertNotEqual(INCREMENTAL.canonical_hash(first), INCREMENTAL.canonical_hash(second))
        self.assertNotEqual(INCREMENTAL.canonical_hash(first), INCREMENTAL.canonical_hash(third))

    def test_approval_covers_publication_only_and_ignores_local_deliverables(self):
        base = INCREMENTAL.approval_document(analysis(), "source-a", "site-a")
        for field, value in (("titolo", "Altre soglie"), ("statement", "Un altro statement.")):
            changed = analysis()
            changed["progetto"][field] = value
            other = INCREMENTAL.approval_document(changed, "source-a", "site-a")
            self.assertEqual(
                INCREMENTAL.canonical_hash(base), INCREMENTAL.canonical_hash(other),
                f"un cambio a progetto.{field} non deve invalidare l'autorizzazione",
            )
        with_colophon = analysis()
        with_colophon["progetto"]["colophon"] = {"Edizione": ["Prima prova."]}
        self.assertEqual(
            INCREMENTAL.canonical_hash(base),
            INCREMENTAL.canonical_hash(
                INCREMENTAL.approval_document(with_colophon, "source-a", "site-a")
            ),
        )

    def test_publication_block_still_binds_the_approval(self):
        base = INCREMENTAL.approval_document(analysis(), "source-a", "site-a")
        changed = analysis()
        changed["pubblicazione"]["gallery"]["slug"] = "nuove-soglie"
        self.assertNotEqual(
            INCREMENTAL.canonical_hash(base),
            INCREMENTAL.canonical_hash(
                INCREMENTAL.approval_document(changed, "source-a", "site-a")
            ),
        )

    def test_approval_is_required_only_when_publication_is_planned(self):
        self.assertTrue(INCREMENTAL.needs_publication_approval(analysis()))
        without = analysis()
        del without["pubblicazione"]
        self.assertFalse(INCREMENTAL.needs_publication_approval(without))
        self.assertFalse(INCREMENTAL.needs_publication_approval(None))

    def test_local_artifacts_build_without_any_recorded_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "one.jpg").write_bytes(b"finto jpeg")
            out = root / "_analisi"
            out.mkdir()
            data = analysis()
            del data["pubblicazione"]
            (out / "analisi.json").write_text(json.dumps(data), encoding="utf-8")
            command = [sys.executable, str(SCRIPT), "build", str(root), "--confirm",
                       "--only", "texts"]
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertNotIn("non approvata", result.stdout + result.stderr)

    def test_publication_still_refuses_to_build_without_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / "one.jpg").write_bytes(b"finto jpeg")
            out = root / "_analisi"
            out.mkdir()
            (out / "analisi.json").write_text(json.dumps(analysis()), encoding="utf-8")

            # L'ingestione va dichiarata corrente, altrimenti e' il suo guardiano
            # a fermare la build e la firma non viene mai interrogata.
            for name in ("metriche.json", "firma.json"):
                (out / name).write_text("{}", encoding="utf-8")
            for name in ("metriche.csv", "coppie_simili.csv", "saltati.csv"):
                (out / name).write_text("id\n", encoding="utf-8")
            for name in ("thumbs", "griglie"):
                (out / name).mkdir()
                (out / name / "P001_one.jpg").write_bytes(b"finta miniatura")
            cache: dict = {}
            inventory = INCREMENTAL.source_inventory(root, cache, True)
            specs = INCREMENTAL.artifact_specs(root, out, inventory, analysis(), "site-a", cache, True)
            state = {"version": INCREMENTAL.VERSION, "file_cache": cache, "artifacts": {}}
            INCREMENTAL.record_artifact("ingest", specs["ingest"], state, cache)
            INCREMENTAL.save_json(out / ".pipeline-incrementale.json", state)

            command = [sys.executable, str(SCRIPT), "build", str(root), "--confirm",
                       "--only", "publication", "--profile-id", "site-a"]
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("non approvata", result.stderr)

    def test_xlsx_is_tracked_only_when_openpyxl_can_produce_it(self):
        outputs = [path.name for path in INCREMENTAL.table_outputs(Path("/tmp/out"))]
        self.assertIn("tabella.csv", outputs)
        self.assertEqual("tabella.xlsx" in outputs, INCREMENTAL.xlsx_available())

    def test_cache_drops_entries_of_files_that_no_longer_exist(self):
        with tempfile.TemporaryDirectory() as folder:
            alive = Path(folder) / "alive.jpg"
            alive.write_bytes(b"x")
            cache = {str(alive): {"sha256": "a"}, "/percorso/sparito.jpg": {"sha256": "b"}}
            removed = INCREMENTAL.prune_cache(cache)
            self.assertEqual(removed, 1)
            self.assertEqual(list(cache), [str(alive)])

    def test_malformed_analysis_reports_a_sentence_not_a_traceback(self):
        broken = analysis()
        broken["immagini"] = {"P001": {}}
        with self.assertRaisesRegex(ValueError, "immagini"):
            INCREMENTAL.check_analysis_shape(broken, Path("analisi.json"))

    def test_doctor_output_is_redacted_before_it_reaches_the_report(self):
        cleaned = INCREMENTAL.redact("Authorization: Bearer abcdefghijklmnopqrstuvwxyz e --token segretissimo")
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz", cleaned)
        self.assertNotIn("segretissimo", cleaned)
        self.assertIn("[REDACTED]", cleaned)

    def test_rehash_detects_content_change_even_with_same_size_and_mtime(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            photo = root / "one.jpg"
            photo.write_bytes(b"AAAA")
            cache = {}
            first = INCREMENTAL.source_inventory(root, cache, True)
            stat = photo.stat()
            photo.write_bytes(b"BBBB")
            os.utime(photo, ns=(stat.st_atime_ns, stat.st_mtime_ns))

            cached = INCREMENTAL.source_inventory(root, cache, False)
            verified = INCREMENTAL.source_inventory(root, cache, True)
            self.assertEqual(first["hash"], cached["hash"])
            self.assertNotEqual(first["hash"], verified["hash"])

    def test_state_file_never_contains_source_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            state_path = Path(folder) / "state.json"
            state = {"version": 1, "file_cache": {}, "source": {"hash": "abc"}}
            INCREMENTAL.save_json(state_path, state)
            loaded = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, state)

    def test_cli_preflight_is_single_pass_and_writes_reusable_hash_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "one.jpg").write_bytes(b"not decoded during preflight")
            command = [sys.executable, str(SCRIPT), "preflight", str(root)]
            first = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(first.returncode, 2)
            report = json.loads(first.stdout)
            self.assertEqual(report["source_inventory"]["count"], 1)
            self.assertEqual(report["next"], "prepare")
            state_path = root / "_analisi" / ".pipeline-incrementale.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertTrue(state["file_cache"])

            second = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(second.returncode, 2)
            report_again = json.loads(second.stdout)
            self.assertEqual(report["source_inventory"]["hash"], report_again["source_inventory"]["hash"])


if __name__ == "__main__":
    unittest.main()
