import importlib.util
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "editing-portfolio-publisher"
    / "scripts"
    / "prepara_provino.py"
)
SPEC = importlib.util.spec_from_file_location("prepara_provino", SCRIPT)
PROVINO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROVINO)


class ExifGeolocationTest(unittest.TestCase):
    def test_converts_gps_degrees_minutes_seconds(self):
        self.assertAlmostEqual(
            PROVINO.coordinata_gps((40, 51, 7.2), "N"), 40.852, places=6
        )
        self.assertAlmostEqual(
            PROVINO.coordinata_gps((74, 0, 21.6), b"W"), -74.006, places=6
        )

    def test_exif_output_contains_decimal_coordinates(self):
        exif = {
            "GPSLatitude": (40, 51, 7.2),
            "GPSLatitudeRef": "N",
            "GPSLongitude": (14, 16, 5.2),
            "GPSLongitudeRef": "E",
        }
        result = PROVINO.estrai_exif(exif)
        self.assertAlmostEqual(result["lat"], 40.852, places=6)
        self.assertAlmostEqual(result["lng"], 14.2681111, places=6)

    def test_missing_gps_remains_unknown(self):
        result = PROVINO.estrai_exif({})
        self.assertIsNone(result["lat"])
        self.assertIsNone(result["lng"])


if __name__ == "__main__":
    unittest.main()
