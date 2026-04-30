"""Tooltip — лёгкая подсказка, всплывающая при наведении курсора."""

from __future__ import annotations

import tkinter as tk
import customtkinter as ctk
from typing import Optional

from ..theme import C, SPACING, font


class Tooltip:
    """
    Показывает подсказку через delay_ms после захода курсора, прячет её при
    уходе курсора, клике или уничтожении виджета-носителя.

    Использование:
        Tooltip(some_label, "Описание поля")
    """

    def __init__(
        self,
        widget,
        text: str,
        delay_ms: int = 400,
        wraplength: int = 280,
    ) -> None:
        self._widget = widget
        self._text = text
        self._delay_ms = delay_ms
        self._wraplength = wraplength
        self._tip: Optional[ctk.CTkToplevel] = None
        self._after_id: Optional[str] = None

        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")
        widget.bind("<Destroy>", self._on_destroy, add="+")

    # ---- Public API ----

    def set_text(self, text: str) -> None:
        self._text = text

    # ---- Handlers ----

    def _on_enter(self, _e=None) -> None:
        self._cancel_pending()
        try:
            self._after_id = self._widget.after(self._delay_ms, self._show)
        except tk.TclError:
            pass

    def _on_leave(self, _e=None) -> None:
        self._cancel_pending()
        self._hide()

    def _on_destroy(self, _e=None) -> None:
        self._cancel_pending()
        self._hide()

    # ---- Internal ----

    def _cancel_pending(self) -> None:
        if self._after_id is not None:
            try:
                self._widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _show(self) -> None:
        if self._tip is not None:
            return
        try:
            x = self._widget.winfo_rootx() + 12
            y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        except tk.TclError:
            return

        tip = ctk.CTkToplevel(self._widget)
        try:
            tip.wm_overrideredirect(True)
        except tk.TclError:
            pass
        try:
            tip.attributes("-topmost", True)
        except tk.TclError:
            pass
        tip.geometry(f"+{x}+{y}")
        tip.configure(fg_color=C["card"])

        ctk.CTkLabel(
            tip,
            text=self._text,
            justify="left",
            wraplength=self._wraplength,
            font=font(11),
            text_color=C["text"],
            fg_color="transparent",
        ).pack(padx=SPACING["sm"], pady=SPACING["xs"])

        self._tip = tip

    def _hide(self) -> None:
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None
