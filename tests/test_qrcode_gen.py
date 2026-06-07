"""
Tests for core/qrcode_gen.qr_matrix — самописный QR-генератор.

Главная защита от тонких багов (Reed-Solomon, маски) — сверка бит-в-бит с
эталонными матрицами, сгенерированными проверенной библиотекой `qrcode`
(byte-mode, уровень коррекции L) и закоммиченными в tests/fixtures/
qr_reference.json. Плюс структурные инварианты.
"""

from __future__ import annotations

import json
import os
import unittest

_FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "qr_reference.json")


def _load_fixtures() -> dict:
    with open(_FIXTURES, encoding="utf-8") as f:
        return json.load(f)


# Format-info биты уровня L по номеру маски (для определения маски эталона).
_FORMAT_BITS_L = {
    0: 0b111011111000100, 1: 0b111001011110011, 2: 0b111110110101010,
    3: 0b111100010011101, 4: 0b110011000101111, 5: 0b110001100011000,
    6: 0b110110001000001, 7: 0b110100101110110,
}


def _reference_mask(exp) -> int:
    """Определяет номер маски эталонной матрицы по её format-info битам."""
    coords1 = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
               (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
    fbits = [1 if exp[r][c] else 0 for (r, c) in coords1]
    fval = int("".join(str(b) for b in fbits), 2)
    for mi, v in _FORMAT_BITS_L.items():
        if v == fval:
            return mi
    raise AssertionError("не удалось определить маску эталона")


class TestQrMatrixAgainstReference(unittest.TestCase):
    """
    Бит-в-бит сверка данных/EC/паттернов с эталоном `qrcode` при ТОЙ ЖЕ маске.

    Маску берём из эталона: выбор маски по penalty имеет допуски в ISO 18004
    (разные корректные реализации могут выбрать разную маску — ЛЮБАЯ даёт
    сканируемый QR). Поэтому проверяем именно данные/размещение, форсируя
    эталонную маску. Авто-выбор маски проверяется отдельно (валидность).
    """

    def setUp(self):
        from tg_exporter.core.qrcode_gen import qr_matrix
        self.qr_matrix = qr_matrix
        self.fixtures = _load_fixtures()

    def _check(self, name: str):
        fx = self.fixtures[name]
        expected = [[c == "1" for c in row] for row in fx["matrix"]]
        ref_mask = _reference_mask(expected)
        result = self.qr_matrix(fx["data"], mask=ref_mask)
        self.assertEqual(len(result), fx["size"], f"{name}: размер матрицы")
        for r, (got_row, exp_row) in enumerate(zip(result, expected)):
            self.assertEqual(
                list(got_row), list(exp_row),
                f"{name}: строка {r} не совпала с эталоном (маска {ref_mask})\n"
                f"  ожидалось: {''.join('1' if c else '0' for c in exp_row)}\n"
                f"  получено:  {''.join('1' if c else '0' for c in got_row)}",
            )

    def test_short_byte(self):
        self._check("short_byte")

    def test_url(self):
        self._check("url")

    def test_tg_short(self):
        self._check("tg_short")

    def test_tg_typical(self):
        self._check("tg_typical")

    def test_tg_long(self):
        self._check("tg_long")


class TestQrMatrixStructure(unittest.TestCase):
    def setUp(self):
        from tg_exporter.core.qrcode_gen import qr_matrix
        self.qr_matrix = qr_matrix

    def test_finder_patterns_present(self):
        # Три finder-паттерна 7×7 в углах (кроме правого нижнего).
        m = self.qr_matrix("HELLO")
        n = len(m)
        # верхний левый угол: первая строка finder = 7 чёрных
        self.assertTrue(all(m[0][c] for c in range(7)), "верхний левый finder")
        # верхний правый
        self.assertTrue(all(m[0][c] for c in range(n - 7, n)), "верхний правый finder")
        # нижний левый
        self.assertTrue(all(m[n - 7][c] for c in range(7)), "нижний левый finder")

    def test_size_matches_version(self):
        # size = 4*version + 17. HELLO → version 1 → 21.
        m = self.qr_matrix("HELLO")
        self.assertEqual(len(m), 21)
        # все строки одной длины
        self.assertTrue(all(len(row) == 21 for row in m))

    def test_returns_bools(self):
        m = self.qr_matrix("HELLO")
        self.assertIsInstance(m[0][0], bool)

    def test_auto_mask_produces_valid_format_info(self):
        # Авто-выбор маски (mask=None) должен дать одну из 8 валидных масок —
        # format-info матрицы должна соответствовать какой-то маске 0–7.
        m = self.qr_matrix("tg://login?token=abcDEF123_xyz")
        ref = _reference_mask(m)  # бросит, если format-info не валиден
        self.assertIn(ref, range(8))

    def test_explicit_mask_roundtrips_format_info(self):
        # Если задать маску явно, format-info в матрице должна её отражать.
        for mi in range(8):
            m = self.qr_matrix("HELLOworld", mask=mi)
            self.assertEqual(_reference_mask(m), mi)


if __name__ == "__main__":
    unittest.main()
