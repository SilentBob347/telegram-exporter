"""
QRCodeWidget — отрисовка QR-кода (например, для входа в Telegram через QR)
на нативный tkinter.Canvas без внешних зависимостей.

Матрица берётся из самописного генератора `core.qrcode_gen.qr_matrix`
(True = чёрный модуль). Канва принудительно ЧЁРНО-БЕЛАЯ независимо от темы
приложения: сканеры читают QR только при реальном контрасте, QR-код на тёмном
фоне темы просто не считается. Поэтому фон канвы — белый (#FFFFFF),
модули — чёрные (#000000).

Вокруг кода обязательна «тихая зона» (quiet zone, белая рамка ~4 модуля),
без неё многие сканеры не распознают код.
"""

from __future__ import annotations

import tkinter as tk
import customtkinter as ctk

from ...core.qrcode_gen import qr_matrix
from ..theme import C, SPACING

# Реальные цвета QR — не из темы (нужен жёсткий чёрно-белый контраст).
_QR_BG = "#FFFFFF"     # фон (тихая зона + светлые модули)
_QR_FG = "#000000"     # чёрные модули


class QRCodeWidget(ctk.CTkFrame):
    """
    Карточка-контейнер с белой канвой, на которой рисуется QR-матрица.

    Использование:
        w = QRCodeWidget(parent, size_px=240)
        w.set_data("tg://login?token=...")   # перерисовать под новые данные
        w.clear()                            # очистить (пустая белая область)
    """

    def __init__(self, master, size_px: int = 240, **kwargs) -> None:
        kwargs.setdefault("fg_color", C["card"])
        super().__init__(master, **kwargs)

        self._size_px = int(size_px)

        # Белая канва внутри карточки — собственно область QR.
        # highlightthickness=0 убирает фокусную рамку Tk вокруг канвы.
        self._canvas = tk.Canvas(
            self,
            width=self._size_px,
            height=self._size_px,
            background=_QR_BG,
            highlightthickness=0,
            borderwidth=0,
        )
        self._canvas.pack(padx=SPACING["md"], pady=SPACING["md"])

    # ---- Публичный API ----

    def set_data(self, data: str) -> None:
        """Строит QR-матрицу для `data` и рисует её на канве (с тихой зоной)."""
        matrix = qr_matrix(data)
        self._draw_matrix(matrix)

    def clear(self) -> None:
        """Очищает канву — остаётся пустая белая область (плейсхолдер)."""
        self._canvas.delete("all")

    # ---- Внутреннее ----

    def _draw_matrix(self, matrix: list[list[bool]]) -> None:
        """Отрисовывает матрицу модулей; каждый модуль — закрашенный прямоугольник."""
        # Очищаем предыдущую отрисовку (set_data может вызываться много раз).
        self._canvas.delete("all")

        n = len(matrix)
        if n == 0:
            return

        # Целочисленный размер модуля → чёткие пиксели без сглаживания.
        # Тихая зона = 4 модуля с каждой стороны, т.е. матрица + 8 модулей.
        module_px = self._size_px // (n + 8)
        if module_px < 1:
            module_px = 1  # на совсем маленькой канве модуль минимум 1px

        quiet_px = 4 * module_px
        # Фактический размер кода (без тихой зоны) и общий размер рисунка.
        draw_px = n * module_px
        total_px = draw_px + 2 * quiet_px

        # Центрируем рисунок в size_px (с учётом возможного остатка от деления).
        offset = (self._size_px - total_px) // 2
        if offset < 0:
            offset = 0
        origin = offset + quiet_px  # левый/верхний угол первого модуля

        # Фон-подложка (белая) под весь код вместе с тихой зоной — на случай,
        # если канва шире рисунка, гарантируем белую рамку вокруг QR.
        self._canvas.create_rectangle(
            offset, offset,
            offset + total_px, offset + total_px,
            fill=_QR_BG, outline="",
        )

        # Чёрные модули — прямоугольниками.
        for r in range(n):
            y0 = origin + r * module_px
            y1 = y0 + module_px
            for c in range(n):
                if matrix[r][c]:
                    x0 = origin + c * module_px
                    x1 = x0 + module_px
                    self._canvas.create_rectangle(
                        x0, y0, x1, y1,
                        fill=_QR_FG, outline="",
                    )
