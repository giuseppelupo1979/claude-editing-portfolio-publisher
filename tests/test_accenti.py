import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "editing-portfolio-publisher" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from lib.accenti import accenti_apostrofati, correggi  # noqa: E402

SPEC = importlib.util.spec_from_file_location("payload", SCRIPTS / "genera_payload_pubblicazione.py")
PAYLOAD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PAYLOAD)


def analysis(**override):
    photo = {
        "id": "P001", "title_it": "Occhi bassi", "title_en": "Eyes Down",
        "alt_it": "Uomo anziano davanti a un banco.", "alt_en": "Elderly man in front of a stall.",
        "place": "Ballarò, Palermo", "lat": 38.1105, "lng": 13.3598,
    }
    photo.update(override.pop("photo", {}))
    gallery = {
        "action": "create", "slug": "ballaro-occhi-bassi",
        "title_it": "Ballarò, occhi bassi", "title_en": "Ballarò, Eyes Down",
        "description_it": "Sedici minuti al mercato.", "description_en": "Sixteen minutes at the market.",
        "cover_file": "uno.jpg",
    }
    gallery.update(override.pop("gallery", {}))
    return {
        "immagini": [{"id": "P001", "file": "uno.jpg", "descrizione": "Una descrizione."}],
        "pubblicazione": {"gallery": gallery, "photos": [photo]},
    }


class AccentiTest(unittest.TestCase):
    def test_riconosce_apostrofo_al_posto_dell_accento(self):
        trovati = dict(accenti_apostrofati("perche' e' cosi'"))
        self.assertEqual(trovati["perche'"], "perché")
        self.assertEqual(trovati["e'"], "è")
        self.assertEqual(trovati["cosi'"], "così")

    def test_non_scompone_una_parola_in_due_errori(self):
        # "perche'" contiene "e'": senza confine si segnalerebbe due volte
        self.assertEqual([s for s, _ in accenti_apostrofati("perche'")], ["perche'"])

    def test_testo_corretto_non_produce_falsi_positivi(self):
        for testo in ("Ballarò, occhi bassi", "è più così che perché",
                      "Elderly man in a cable-knit cardigan", "Eyes Down"):
            self.assertEqual(accenti_apostrofati(testo), [], testo)

    def test_riconosce_i_nomi_propri_senza_accento(self):
        self.assertEqual(accenti_apostrofati("Ballaro, Palermo"), [("Ballaro", "Ballarò")])

    def test_correggi_ripara_il_testo(self):
        self.assertEqual(correggi("a Ballaro e' piu' cosi'"), "a Ballarò è più così")

    def test_il_piano_si_rifiuta_di_uscire_con_gli_apostrofi(self):
        for dove in ({"gallery": {"title_it": "Ballaro, occhi bassi"}},
                     {"photo": {"place": "Ballaro, Palermo"}},
                     {"photo": {"alt_it": "L'uomo e' davanti al banco."}}):
            with self.assertRaisesRegex(ValueError, "Accenti scritti con l'apostrofo"):
                PAYLOAD.build_plan(analysis(**dove), "test-site", Path("/tmp/foto"))

    def test_il_piano_corretto_passa(self):
        piano = PAYLOAD.build_plan(analysis(), "test-site", Path("/tmp/foto"))
        self.assertEqual(piano["gallery"]["title_it"], "Ballarò, occhi bassi")
        self.assertEqual(piano["photos"][0]["place"], "Ballarò, Palermo")


if __name__ == "__main__":
    unittest.main()
