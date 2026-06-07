"""Sidebar — постоянное боковое меню навигации (после логина)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable
import customtkinter as ctk

from ..theme import C, RADIUS, SPACING, WIDGET, SIDEBAR_W, font, font_display

if TYPE_CHECKING:
    from ..app import App

# (page_key, иконка, подпись)
_NAV = [
    ("chats",    "💬", "Чаты"),
    ("accounts", "👤", "Аккаунты"),
    ("settings", "⚙️", "Настройки"),
    ("help",     "📖", "Инструкция"),
]


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, app: "App", on_select: Callable[[str], None]) -> None:
        super().__init__(master, fg_color=C["surface"], corner_radius=0, width=SIDEBAR_W)
        self.pack_propagate(False)
        self._app = app
        self._on_select = on_select
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._active: str = "chats"
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="📤  Telegram Exporter", font=font_display(14, "bold"),
                     text_color=C["text"], anchor="w").pack(
                         fill="x", padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["lg"]))
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=SPACING["sm"])
        for key, icon, label in _NAV:
            btn = ctk.CTkButton(
                nav, text=f"{icon}   {label}", anchor="w",
                font=font(13), height=WIDGET["btn_h"],
                fg_color="transparent", text_color=C["text_sec"],
                hover_color=C["card"], corner_radius=RADIUS["md"],
                command=lambda k=key: self._select(k),
            )
            btn.pack(fill="x", pady=2)
            self._buttons[key] = btn
        ctk.CTkFrame(self, fg_color="transparent").pack(fill="both", expand=True)
        logout = ctk.CTkButton(
            self, text="↩   Выход", anchor="w", font=font(13),
            height=WIDGET["btn_h"], fg_color="transparent", text_color=C["error"],
            hover_color=C["card"], corner_radius=RADIUS["md"],
            command=self._app.logout,
        )
        logout.pack(fill="x", padx=SPACING["sm"], pady=(0, SPACING["md"]))
        self.set_active("chats")

    def _select(self, key: str) -> None:
        self.set_active(key)
        self._on_select(key)

    def set_active(self, key: str) -> None:
        self._active = key
        for k, btn in self._buttons.items():
            if k == key:
                btn.configure(fg_color=C["primary"], text_color=C["primary_text"])
            else:
                btn.configure(fg_color="transparent", text_color=C["text_sec"])
