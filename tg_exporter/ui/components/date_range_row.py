"""DateRangeRow — строка ввода диапазона дат с пикерами и хинтом."""

from __future__ import annotations

import tkinter as tk
import customtkinter as ctk
from typing import Callable, Optional

from .date_picker import DatePickerButton
from .entry import AppEntry
from ..theme import C, SPACING, font


_DEFAULT_HINT = "Формат: YYYY-MM-DD, локальное время"


class DateRangeRow(ctk.CTkFrame):
    """Связка двух полей дат: «От [..] 📅 До [..] 📅» + хинт о формате.

    Хинт всегда на отдельной строке под полями — раньше был вариант
    inline-строки, но при узком окне он обрезался горизонтально и
    пользователь не видел напоминания о формате. Стабильнее всегда
    показывать ниже полей.

    on_change вызывается без аргументов на:
      - FocusOut/Return текстовых полей,
      - выборе даты в popup-календаре.

    Парсинг строки в datetime — забота вызывающего; компонент только
    собирает StringVar'ы и триггерит on_change. См. utils.parse_local_date.
    """

    def __init__(
        self,
        master,
        var_from: tk.StringVar,
        var_to: tk.StringVar,
        on_change: Optional[Callable[[], None]] = None,
        hint: str = _DEFAULT_HINT,
        leading_pad: int = 0,
    ) -> None:
        super().__init__(master, fg_color="transparent")

        inputs = ctk.CTkFrame(self, fg_color="transparent")
        inputs.pack(fill="x")

        ctk.CTkLabel(
            inputs, text="От",
            text_color=C["text_sec"], font=font(12),
        ).pack(side="left", padx=(leading_pad, SPACING["xs"]))

        e_from = AppEntry(
            inputs, placeholder_text="ГГГГ-ММ-ДД",
            width=120, size="sm", textvariable=var_from,
        )
        e_from.pack(side="left")
        DatePickerButton(
            inputs, target_var=var_from, on_pick=on_change,
        ).pack(side="left", padx=(SPACING["xs"], 0))

        ctk.CTkLabel(
            inputs, text="До",
            text_color=C["text_sec"], font=font(12),
        ).pack(side="left", padx=(SPACING["md"], SPACING["xs"]))

        e_to = AppEntry(
            inputs, placeholder_text="ГГГГ-ММ-ДД",
            width=120, size="sm", textvariable=var_to,
        )
        e_to.pack(side="left")
        DatePickerButton(
            inputs, target_var=var_to, on_pick=on_change,
        ).pack(side="left", padx=(SPACING["xs"], 0))

        ctk.CTkLabel(
            self, text=hint,
            text_color=C["text_dim"], font=font(11),
        ).pack(anchor="w", padx=(leading_pad, 0), pady=(SPACING["xs"], 0))

        if on_change is not None:
            for e in (e_from, e_to):
                e.bind("<FocusOut>", lambda _e: on_change())
                e.bind("<Return>", lambda _e: on_change())
