import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "editing-portfolio-publisher"
    / "scripts"
    / "genera_dummy_pdf.py"
)
SPEC = importlib.util.spec_from_file_location("dummy", SCRIPT)
DUMMY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DUMMY)


class DummyExifTest(unittest.TestCase):
    def test_reports_only_equipment_used_by_selected_plates(self):
        metrics = {
            "immagini": [
                {
                    "file": "selected.jpg",
                    "corpo": "RICOH GR III",
                    "ottica": "GR LENS 18.3mm F2.8",
                    "focale": 18.3,
                    "focale_equivalente": 28.0,
                },
                {"file": "excluded.jpg", "corpo": "OTHER CAMERA", "ottica": "OTHER LENS"},
            ]
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "metriche.json"
            path.write_text(json.dumps(metrics), encoding="utf-8")
            text = DUMMY.attrezzatura_exif(str(path), [{"file": "selected.jpg"}])
            sections = dict(DUMMY.attrezzatura_sezioni(str(path), [{"file": "selected.jpg"}]))
        self.assertIn("RICOH GR III", text)
        self.assertIn("GR LENS 18.3mm F2.8", text)
        self.assertIn("18.3 mm", text)
        self.assertIn("28 mm", text)
        self.assertIn("- RICOH GR III (1 tavola).", text)
        self.assertNotIn("OTHER CAMERA", text)

        self.assertIn("Copertura EXIF", sections)
        self.assertIn("Corpi macchina", sections)
        self.assertIn("Obiettivi", sections)
        self.assertIn("Focali utilizzate", sections)
        self.assertIn("Focali equivalenti", sections)

    def test_missing_metrics_is_declared_without_inventing_data(self):
        text = DUMMY.attrezzatura_exif("/path/that/does/not/exist.json", [])
        self.assertIn("non disponibile", text)

    def test_long_bullet_section_continues_without_losing_items(self):
        libro = DUMMY.Libro(21, 26, 72)
        voci = ["Elemento numerato %02d" % n for n in range(60)]
        disegnati = []
        originale = DUMMY.ImageDraw.ImageDraw.text

        def registra(disegno, xy, testo, *args, **kwargs):
            disegnati.append(str(testo))
            return originale(disegno, xy, testo, *args, **kwargs)

        with patch.object(DUMMY.ImageDraw.ImageDraw, "text", new=registra):
            libro.sezioni_puntate("Attrezzatura", [("Obiettivi", voci)])

        self.assertGreater(len(libro.pagine), 1)
        self.assertEqual(disegnati.count("•"), len(voci))
        for voce in voci:
            self.assertIn(voce, disegnati)
        self.assertIn("Attrezzatura (continua)", disegnati)
        self.assertIn("Obiettivi (continua)", disegnati)

    def test_qa_manifest_reports_only_changed_pdf_pages(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            thumbs = root / "thumbs"
            thumbs.mkdir()
            DUMMY.Image.new("RGB", (120, 80), "white").save(thumbs / "P001_one.jpg")
            analysis = {
                "progetto": {"titolo": "Prova", "autore": "Autore", "copertina": "P001"},
                "immagini": [{
                    "id": "P001", "file": "one.jpg", "thumb": "thumbs/P001_one.jpg",
                    "descrizione": "Una descrizione breve.", "didascalia": "Una didascalia.",
                }],
                "sequenza": {"spread": [[None, "P001"]]},
            }
            analysis_path = root / "analisi.json"
            analysis_path.write_text(json.dumps(analysis), encoding="utf-8")
            metrics_path = root / "metriche.json"
            metrics_path.write_text(json.dumps({"immagini": [{"id": "P001", "file": "one.jpg"}]}), encoding="utf-8")
            output = root / "dummy.pdf"
            argv = [
                "genera_dummy_pdf.py", str(analysis_path), "-o", str(output),
                "--radice", str(root), "--metriche", str(metrics_path), "--dpi", "36", "--qa-strict",
            ]
            with patch("sys.argv", argv):
                DUMMY.main()
            first = json.loads((root / "dummy.qa.json").read_text(encoding="utf-8"))
            self.assertTrue(first["qa_ok"])
            self.assertGreater(first["book_pages"], first["pdf_pages"])
            self.assertTrue(first["changed_pdf_pages"])

            with patch("sys.argv", argv):
                DUMMY.main()
            second = json.loads((root / "dummy.qa.json").read_text(encoding="utf-8"))
            self.assertEqual(second["changed_pdf_pages"], [])
            self.assertEqual(second["changed_sections"], [])


if __name__ == "__main__":
    unittest.main()
