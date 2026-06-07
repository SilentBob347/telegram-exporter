"""AccountsPage — управление аккаунтами карточками (вместо popup «Аккаунт ▾»)."""

from __future__ import annotations

import tkinter.messagebox as mb
from typing import TYPE_CHECKING
import customtkinter as ctk

from ..theme import C, RADIUS, SPACING, font, font_display
from ..components.button import AppButton
from ..modal_utils import setup_smooth_scroll

if TYPE_CHECKING:
    from ..app import App


class AccountsPage(ctk.CTkFrame):
    def __init__(self, master, app: "App") -> None:
        super().__init__(master, fg_color="transparent")
        self._app = app
        self._build()
        self.after(100, lambda: setup_smooth_scroll(self, self._scroll))

    def refresh(self) -> None:
        for w in self._scroll.winfo_children():
            w.destroy()
        self._render_cards()

    def _build(self) -> None:
        pad = SPACING["2xl"]
        ctk.CTkLabel(self, text="Аккаунты", font=font_display(20, "bold"),
                     text_color=C["text"]).pack(anchor="w", padx=pad, pady=(pad, SPACING["lg"]))
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=C["bg"])
        self._scroll.pack(fill="both", expand=True, padx=pad, pady=(0, SPACING["md"]))
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=pad, pady=(0, pad))
        AppButton(actions, text="+ Добавить аккаунт", variant="primary",
                  command=self._app.show_add_account).pack(side="left")
        AppButton(actions, text="📷 Войти по QR-коду", variant="secondary",
                  command=self._app.show_add_account).pack(side="left", padx=(SPACING["sm"], 0))
        self._render_cards()

    def _render_cards(self) -> None:
        profiles = self._app.profiles()
        active = self._app.active_profile()
        active_phone = active.phone if active else None
        if not profiles:
            ctk.CTkLabel(self._scroll, text="Аккаунтов пока нет. Добавьте первый.",
                         font=font(13), text_color=C["text_sec"]).pack(anchor="w", pady=SPACING["md"])
            return
        for p in profiles:
            self._card(p, p.phone == active_phone)

    def _card(self, profile, is_active: bool) -> None:
        card = ctk.CTkFrame(self._scroll, fg_color=C["surface"], corner_radius=RADIUS["lg"],
                            border_width=1, border_color=C["primary"] if is_active else C["border"])
        card.pack(fill="x", pady=(0, SPACING["sm"]))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=SPACING["lg"], pady=SPACING["md"])
        name = (profile.display_name or profile.phone or "").strip() or profile.phone
        title = name + ("   ● активный" if is_active else "")
        ctk.CTkLabel(inner, text=title, font=font(14, "bold"),
                     text_color=C["text"], anchor="w").pack(side="left")
        proxy_mark = " ✓" if (self._app._profiles.load_proxy(profile) or "").strip() else ""
        AppButton(inner, text="Удалить", variant="ghost", size="sm",
                  command=lambda ph=profile.phone: self._remove(ph)).pack(side="right")
        AppButton(inner, text=f"🌐 Прокси{proxy_mark}", variant="secondary", size="sm",
                  command=lambda ph=profile.phone: self._app.show_proxy_settings(ph)).pack(side="right", padx=(0, SPACING["sm"]))
        if not is_active:
            AppButton(inner, text="Сделать активным", variant="secondary", size="sm",
                      command=lambda ph=profile.phone: self._app.switch_profile(ph)).pack(side="right", padx=(0, SPACING["sm"]))

    def _remove(self, phone: str) -> None:
        if not mb.askyesno("Удалить аккаунт", f"Удалить профиль {phone} и его сессию?"):
            return
        self._app.remove_profile(phone)
        self.refresh()
