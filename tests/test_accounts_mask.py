"""Tests for accounts_page._mask_phone — маскировка номера для карточек."""

from __future__ import annotations

import unittest


class TestMaskPhone(unittest.TestCase):
    def setUp(self):
        from tg_exporter.ui.views.accounts_page import _mask_phone
        self.mask = _mask_phone

    def test_ru_number(self):
        self.assertEqual(self.mask("+79051234567"), "+7 905 ***-**-67")

    def test_keeps_country_and_last2(self):
        out = self.mask("+12015550123")
        self.assertTrue(out.startswith("+1 201"))
        self.assertTrue(out.endswith("23"))
        self.assertIn("***", out)  # середина скрыта

    def test_no_plus(self):
        self.assertEqual(self.mask("79051234567"), "7 905 ***-**-67")

    def test_full_number_not_shown(self):
        # средние цифры не должны протекать
        out = self.mask("+79051234567")
        self.assertNotIn("123", out)
        self.assertNotIn("345", out)

    def test_short_returned_asis(self):
        self.assertEqual(self.mask("12345"), "12345")

    def test_empty(self):
        self.assertEqual(self.mask(""), "")


if __name__ == "__main__":
    unittest.main()
