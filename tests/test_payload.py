import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "editing-portfolio-publisher"
    / "scripts"
    / "genera_payload_pubblicazione.py"
)
SPEC = importlib.util.spec_from_file_location("payload", SCRIPT)
PAYLOAD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PAYLOAD)


def analysis():
    return {
        "immagini": [
            {
                "id": "P001",
                "file": "foto 01.jpg",
                "descrizione": "Una figura davanti a una porta.",
                "didascalia": "La porta trattiene la figura.",
            }
        ],
        "pubblicazione": {
            "gallery": {
                "action": "create",
                "slug": "napoli-sulla-soglia",
                "title_it": "Napoli, sulla soglia",
                "title_en": "Naples, on the Threshold",
                "description_it": "Una serie sulle soglie.",
                "description_en": "A series about thresholds.",
                "cover_file": "foto 01.jpg",
            },
            "photos": [
                {
                    "id": "P001",
                    "title_it": "La soglia",
                    "title_en": "The Threshold",
                    "alt_it": "Una figura davanti a una porta.",
                    "alt_en": "A figure in front of a door.",
                }
            ],
        },
    }


class PublicationPayloadTest(unittest.TestCase):
    def test_builds_unapproved_plan_and_resolves_image_file(self):
        with tempfile.TemporaryDirectory(prefix="Napoli 2023 ") as folder:
            plan = PAYLOAD.build_plan(analysis(), "test-site", Path(folder))
        self.assertFalse(plan["approval"]["approved"])
        self.assertEqual(plan["photos"][0]["file"], "foto 01.jpg")
        self.assertEqual(plan["photos"][0]["caption"], "La porta trattiene la figura.")

    def test_requires_all_bilingual_text(self):
        data = analysis()
        del data["pubblicazione"]["photos"][0]["alt_en"]
        with self.assertRaisesRegex(ValueError, "alt_en"):
            PAYLOAD.build_plan(data, "test-site", Path("/tmp/photos"))

    def test_cover_must_be_in_selection(self):
        data = analysis()
        data["pubblicazione"]["gallery"]["cover_file"] = "altra.jpg"
        with self.assertRaisesRegex(ValueError, "cover_file"):
            PAYLOAD.build_plan(data, "test-site", Path("/tmp/photos"))


if __name__ == "__main__":
    unittest.main()
