"""
Tests for ui/modal_utils.setup_smooth_scroll — регрессия на bind_all.

CustomTkinter запрещает bind_all/unbind_all на своих виджетах (бросает
AttributeError). Раньше setup_smooth_scroll звал modal.bind_all(...) на
<Enter>, что ломало скролл на страницах (CTkFrame). Эти тесты фиксируют, что
функция больше НЕ использует bind_all/unbind_all и не падает.
"""

from __future__ import annotations

import sys
import unittest
from unittest import mock


class _FakeCanvas:
    def __init__(self):
        self.binds = []

    def bind(self, seq, fn, add=None):
        self.binds.append(seq)

    def bind_all(self, *a, **k):
        raise AssertionError("bind_all не должен вызываться!")

    def unbind_all(self, *a, **k):
        raise AssertionError("unbind_all не должен вызываться!")

    def yview_scroll(self, *a, **k):
        pass


class _FakeScrollFrame:
    def __init__(self, canvas=None):
        if canvas is not None:
            self._parent_canvas = canvas

    def bind_all(self, *a, **k):
        raise AssertionError("bind_all не должен вызываться на frame!")

    def unbind_all(self, *a, **k):
        raise AssertionError("unbind_all не должен вызываться на frame!")


class _FakeModal:
    """modal-аргумент: если кто-то позовёт bind_all на нём — тест упадёт."""
    def bind_all(self, *a, **k):
        raise AssertionError("bind_all не должен вызываться на modal!")

    def unbind_all(self, *a, **k):
        raise AssertionError("unbind_all не должен вызываться на modal!")


class TestSetupSmoothScroll(unittest.TestCase):
    def setUp(self):
        from tg_exporter.ui.modal_utils import setup_smooth_scroll
        self.setup = setup_smooth_scroll

    def test_no_bind_all_on_macos(self):
        # На macOS биндим на canvas, но НИКОГДА bind_all (иначе AssertionError).
        canvas = _FakeCanvas()
        frame = _FakeScrollFrame(canvas)
        with mock.patch.object(sys, "platform", "darwin"):
            self.setup(_FakeModal(), frame)
        # должен забиндить колесо на canvas
        self.assertIn("<MouseWheel>", canvas.binds)

    def test_noop_on_non_macos(self):
        # На Win/Linux — no-op (встроенный скролл CTk достаточен).
        canvas = _FakeCanvas()
        frame = _FakeScrollFrame(canvas)
        with mock.patch.object(sys, "platform", "win32"):
            self.setup(_FakeModal(), frame)
        self.assertEqual(canvas.binds, [])

    def test_no_crash_without_parent_canvas(self):
        # Объект без _parent_canvas не должен ронять функцию.
        frame = _FakeScrollFrame(canvas=None)
        with mock.patch.object(sys, "platform", "darwin"):
            self.setup(_FakeModal(), frame)  # не должно бросить


if __name__ == "__main__":
    unittest.main()
