import unittest

from model.plate_ocr import (
    character_error_rate,
    hash_plate_text,
    normalize_plate_text,
)


class PlateOcrTests(unittest.TestCase):
    def test_normalize_plate_text(self) -> None:
        self.assertEqual(normalize_plate_text(" abc-123 "), "ABC123")

    def test_character_error_rate(self) -> None:
        self.assertEqual(character_error_rate("ABC123", "ABC123"), 0.0)
        self.assertAlmostEqual(character_error_rate("ABC123", "ABC124"), 1 / 6)

    def test_hash_is_stable(self) -> None:
        first = hash_plate_text("WPABC1234", salt="demo")
        second = hash_plate_text("WPABC1234", salt="demo")
        self.assertEqual(first, second)
        self.assertNotEqual(first, hash_plate_text("WPABC1234", salt="other"))


if __name__ == "__main__":
    unittest.main()
