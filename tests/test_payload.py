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
                    "place": "Napoli, Italia",
                    "lat": 40.8518,
                    "lng": 14.2681,
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
        self.assertEqual(plan["photos"][0]["location_source"], "explicit")
        # Coordinate scritte a mano nel blocco pubblicazione: sono una stima,
        # e la Mappa pubblica non deve mostrarle come rilevamento GPS.
        self.assertEqual(plan["photos"][0]["location_precision"], "approximate")

    def test_handwritten_coordinates_are_not_promoted_to_exact(self):
        data = analysis()
        plan = PAYLOAD.build_plan(data, "test-site", Path("/tmp/photos"))
        self.assertEqual(plan["photos"][0]["location_precision"], "approximate")

    def test_exif_coordinates_are_exact(self):
        data = analysis()
        photo = data["pubblicazione"]["photos"][0]
        for key in ("lat", "lng"):
            del photo[key]
        metrics = {
            "immagini": [
                {"id": "P001", "file": "foto 01.jpg", "lat": 40.85216, "lng": 14.26811}
            ]
        }
        plan = PAYLOAD.build_plan(data, "test-site", Path("/tmp/photos"), metrics)
        self.assertEqual(plan["photos"][0]["location_precision"], "exact")

    def test_explicit_precision_wins_over_the_default(self):
        data = analysis()
        data["pubblicazione"]["photos"][0]["location_precision"] = "exact"
        plan = PAYLOAD.build_plan(data, "test-site", Path("/tmp/photos"))
        self.assertEqual(plan["photos"][0]["location_precision"], "exact")

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

    def test_combines_exif_coordinates_with_confirmed_project_place(self):
        data = analysis()
        photo = data["pubblicazione"]["photos"][0]
        for key in ("place", "lat", "lng"):
            del photo[key]
        data["pubblicazione"]["location_defaults"] = {
            "place": "Napoli, Italia",
            "precision": "approximate",
            "confirmed_by_user": True,
        }
        metrics = {
            "immagini": [
                {
                    "id": "P001",
                    "file": "foto 01.jpg",
                    "lat": 40.85216,
                    "lng": 14.26811,
                    "corpo": "RICOH GR III",
                    "ottica": "GR LENS 18.3mm F2.8",
                }
            ]
        }
        plan = PAYLOAD.build_plan(data, "test-site", Path("/tmp/photos"), metrics)
        published = plan["photos"][0]
        self.assertEqual(published["place"], "Napoli, Italia")
        self.assertEqual(published["lat"], 40.85216)
        self.assertEqual(published["lng"], 14.26811)
        self.assertEqual(published["location_source"], "mixed")
        self.assertEqual(published["location_precision"], "approximate")
        self.assertIn("RICOH GR III", published["camera"])

    def test_missing_location_stops_before_publication(self):
        data = analysis()
        photo = data["pubblicazione"]["photos"][0]
        for key in ("place", "lat", "lng"):
            del photo[key]
        with self.assertRaisesRegex(ValueError, "chiedi all'utente"):
            PAYLOAD.build_plan(data, "test-site", Path("/tmp/photos"))

    def test_unconfirmed_project_default_is_not_used(self):
        data = analysis()
        photo = data["pubblicazione"]["photos"][0]
        for key in ("place", "lat", "lng"):
            del photo[key]
        data["pubblicazione"]["location_defaults"] = {
            "place": "Napoli, Italia",
            "lat": 40.8518,
            "lng": 14.2681,
            "precision": "approximate",
            "confirmed_by_user": False,
        }
        with self.assertRaisesRegex(ValueError, "confirmed_by_user=true"):
            PAYLOAD.build_plan(data, "test-site", Path("/tmp/photos"))


if __name__ == "__main__":
    unittest.main()
