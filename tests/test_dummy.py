import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


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
        self.assertIn("RICOH GR III", text)
        self.assertIn("GR LENS 18.3mm F2.8", text)
        self.assertIn("18.3 mm", text)
        self.assertIn("28 mm", text)
        self.assertNotIn("OTHER CAMERA", text)

    def test_missing_metrics_is_declared_without_inventing_data(self):
        text = DUMMY.attrezzatura_exif("/path/that/does/not/exist.json", [])
        self.assertIn("non disponibile", text)


if __name__ == "__main__":
    unittest.main()
