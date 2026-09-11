import unittest

from app import ForgatokonyvIro


class ProjektAdatTeszt(unittest.TestCase):
    def test_uj_projekt_alapertelmezett_adatok(self):
        adat = ForgatokonyvIro.uj_projekt_adat()
        self.assertEqual(adat["napi_cel"], 500)
        self.assertEqual(adat["referenciak"], [])

    def test_fountain_import_jeleneteket_olvas(self):
        jelenetek = ForgatokonyvIro.fountain_jelenetek(
            "Title: Teszt\n\nINT. SZOBA - NAPPAL\n\nANNA\nSzia!"
        )
        self.assertEqual(len(jelenetek), 1)
        self.assertEqual(jelenetek[0]["blokkok"]["1"], "Karakter")
        self.assertEqual(jelenetek[0]["blokkok"]["2"], "Párbeszéd")


if __name__ == "__main__":
    unittest.main()
