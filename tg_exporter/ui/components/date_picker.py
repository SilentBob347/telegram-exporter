"""DatePickerButton — кнопка-календарь рядом с текстовым полем даты."""

from __future__ import annotations

import datetime
import tkinter as tk
import customtkinter as ctk
from typing import Callable, Optional

from .button import AppButton
from ..theme import C, SPACING, pick

try:
    from tkcalendar import Calendar
    _CALENDAR_OK = True
except ImportError:
    Calendar = None  # type: ignore[assignment]
    _CALENDAR_OK = False


class DatePickerButton(AppButton):
    """
    Маленькая кнопка с иконкой календаря. По клику открывает popup с
    tkcalendar.Calendar; выбранная дата записывается в формате YYYY-MM-DD
    в передаваемый StringVar.

    Текстовое поле даты остаётся независимым — пользователь может либо
    набрать дату руками, либо выбрать кнопкой. После выбора дополнительно
    вызывается опциональный on_pick — для случаев, когда родитель
    биндится на FocusOut/Return текстового поля и не получает уведомление
    при программной установке переменной.

    Если tkcalendar по какой-то причине не установлен, кнопка тихо
    становится no-op — текстовый ввод по-прежнему работает.
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

    # ---- Public ----

    def is_available(self) -> bool:
        return _CALENDAR_OK

    # ---- Internal ----

    def _open_picker(self) -> None:
        if not _CALENDAR_OK:
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

        popup = ctk.CTkToplevel(self)
        try:
            popup.wm_overrideredirect(True)
            popup.attributes("-topmost", True)
        except tk.TclError:
            pass
        popup.configure(fg_color=C["card"])

        try:
            x = self.winfo_rootx()
            y = self.winfo_rooty() + self.winfo_height() + 4
            popup.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

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

        # Кнопка закрытия — на случай, когда хочется передумать. Рандомные
        # клики «вне popup» иногда не порождают FocusOut на overrideredirect-
        # окне, поэтому явная кнопка надёжнее.
        AppButton(
            popup, text="Закрыть", variant="ghost", size="sm",
            command=lambda: self._close_popup(),
        ).pack(padx=4, pady=(2, 4), fill="x")

        cal.bind("<<CalendarSelected>>", lambda _e: self._commit(cal.get_date()))
        popup.bind("<Escape>", lambda _e: self._close_popup())
        popup.bind("<FocusOut>", lambda _e: self._close_popup())
        popup.after(50, popup.focus_set)
        self._popup = popup

    def _commit(self, value: str) -> None:
        self._target.set(value)
        if self._on_pick is not None:
            try:
                self._on_pick()
            except Exception:
                pass
        self._close_popup()

    def _close_popup(self) -> None:
        if self._popup is not None:
            try:
                if self._popup.winfo_exists():
                    self._popup.destroy()
            except tk.TclError:
                pass
            self._popup = None
