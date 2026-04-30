"""DatePickerButton — кнопка-календарь рядом с текстовым полем даты."""

from __future__ import annotations

import datetime
import tkinter as tk
import customtkinter as ctk
from typing import Callable, Optional

from .button import AppButton
from ..modal_utils import make_anchored_popup
from ..theme import C, pick


class DatePickerButton(AppButton):
    """
    Маленькая кнопка с иконкой календаря. По клику открывает popup с
    tkcalendar.Calendar; выбранная дата записывается в формате YYYY-MM-DD
    в передаваемый StringVar.

    Текстовое поле даты остаётся независимым — пользователь может либо
    набрать дату руками, либо выбрать кликом. После выбора дополнительно
    вызывается опциональный on_pick — для случаев, когда родитель
    биндится на FocusOut/Return текстового поля и не получает уведомление
    при программной установке переменной.

    tkcalendar импортируется лениво: его babel-зависимость на старте
    приложения сканирует locale-данные (~50 ms), а календарь нужен
    только при клике на кнопку.
    """

    def __init__(
        self,
        master,
        target_var: tk.StringVar,
        on_pick: Optional[Callable[[], None]] = None,
        size: str = "sm",
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            text="📅",
            variant="ghost",
            size=size,
            command=self._open_picker,
            width=30,
            **kwargs,
        )
        self._target = target_var
        self._on_pick = on_pick
        self._popup: Optional[ctk.CTkToplevel] = None
        # Если кнопку уничтожают, пока popup открыт, popup останется висеть
        # отдельным окном.
        self.bind("<Destroy>", lambda _e: self._close_popup(), add="+")

    # ---- Internal ----

    def _open_picker(self) -> None:
        try:
            from tkcalendar import Calendar
        except ImportError:
            # tkcalendar не установлен — кнопка тихо no-op, текстовый
            # ввод остаётся доступным.
            return

        if self._popup is not None and self._popup.winfo_exists():
            try:
                self._popup.lift()
                self._popup.focus_set()
            except tk.TclError:
                pass
            return

        cur = datetime.date.today()
        raw = (self._target.get() or "").strip()
        if raw:
            try:
                cur = datetime.date.fromisoformat(raw[:10])
            except ValueError:
                pass

        try:
            x = self.winfo_rootx()
            y = self.winfo_rooty() + self.winfo_height() + 4
        except tk.TclError:
            return

        popup = make_anchored_popup(self, x, y, fg_color=C["card"])

        cal = Calendar(
            popup,
            year=cur.year,
            month=cur.month,
            day=cur.day,
            date_pattern="yyyy-mm-dd",
            firstweekday="monday",
            showweeknumbers=False,
            background=pick("card"),
            foreground=pick("text"),
            selectbackground=pick("primary"),
            selectforeground="#FFFFFF",
            normalbackground=pick("card"),
            weekendbackground=pick("card"),
            othermonthbackground=pick("bg"),
            othermonthforeground=pick("text_dim"),
            headersbackground=pick("surface"),
            headersforeground=pick("text_sec"),
            bordercolor=pick("border"),
            font=("", 11),
        )
        cal.pack(padx=4, pady=(4, 0))

        # Кнопка закрытия — на overrideredirect-окне FocusOut срабатывает
        # ненадёжно (особенно на Windows), поэтому явный путь к закрытию
        # обязателен на случай «передумал».
        AppButton(
            popup, text="Закрыть", variant="ghost", size="sm",
            command=self._close_popup,
        ).pack(padx=4, pady=(2, 4), fill="x")

        cal.bind("<<CalendarSelected>>", lambda _e: self._commit(cal.get_date()))
        popup.bind("<Escape>", lambda _e: self._close_popup())
        popup.bind("<FocusOut>", lambda _e: self._close_popup())
        popup.after(50, popup.focus_set)
        self._popup = popup

    def _commit(self, value: str) -> None:
        self._target.set(value)
        if self._on_pick is not None:
            self._on_pick()
        self._close_popup()

    def _close_popup(self) -> None:
        if self._popup is not None:
            try:
                if self._popup.winfo_exists():
                    self._popup.destroy()
            except tk.TclError:
                pass
            self._popup = None
