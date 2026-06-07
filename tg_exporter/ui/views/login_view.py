"""
LoginView — экран авторизации.

Состояния: phone → code (+2fa) → loading → (переход к чатам через App)
Inline ошибки под полем вместо messagebox.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import customtkinter as ctk

from ..theme import C, RADIUS, SPACING, font, font_display
from ..components.button import AppButton
from ..components.entry import AppEntry
from ..components.qr_widget import QRCodeWidget

if TYPE_CHECKING:
    from ..app import App


class LoginView(ctk.CTkFrame):
    """Центральная карточка авторизации."""

    def __init__(self, master, app: "App") -> None:
        super().__init__(master, fg_color="transparent")
        self._app = app
        self._state = "phone"  # "phone" | "code" | "loading"
        self._build()

    # ---- Build ----

    def _build(self) -> None:
        # Карточка по центру
        self._card = ctk.CTkFrame(
            self,
            fg_color=C["card"],
            corner_radius=RADIUS["2xl"],
            border_width=1,
            border_color=C["border"],
        )
        self._card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.42, relheight=0.72)

        pad = SPACING["3xl"]

        # Заголовок
        ctk.CTkLabel(
            self._card,
            text="Telegram Exporter",
            font=font_display(22, "bold"),
            text_color=C["text"],
        ).pack(pady=(pad, SPACING["xs"]))

        ctk.CTkLabel(
            self._card,
            text="Авторизуйтесь через свой аккаунт",
            font=font(13),
            text_color=C["text_sec"],
        ).pack(pady=(0, SPACING["xl"]))

        # Переключатель режима входа: по номеру / QR-код
        self._mode_var = ctk.StringVar(value="По номеру")
        self._mode_seg = ctk.CTkSegmentedButton(
            self._card,
            values=["По номеру", "QR-код"],
            variable=self._mode_var,
            command=self._on_mode_change,
        )
        self._mode_seg.pack(pady=(0, SPACING["md"]))

        # Статус API-ключей
        self._api_lbl = ctk.CTkLabel(
            self._card, text="", font=font(12), text_color=C["error"],
        )
        self._api_lbl.pack(pady=(0, SPACING["sm"]))

        # Кнопки настройки API
        self._settings_btn = AppButton(
            self._card, text="Настроить API ключи", variant="secondary",
            command=self._app.show_api_keys,
        )
        self._settings_btn.pack(padx=pad, fill="x", pady=(0, SPACING["xs"]))

        self._clear_api_btn = AppButton(
            self._card, text="Сбросить API ключи", variant="ghost",
            command=self._on_clear_api,
        )
        # не показываем пока нет ключей

        # Прокси для входа (для РФ-юзеров без VPN). Применяется к первому входу.
        self._proxy_btn = AppButton(
            self._card, text="🌐 Прокси (если нет VPN)", variant="ghost",
            command=self._app.show_login_proxy,
        )
        self._proxy_btn.pack(padx=pad, fill="x", pady=(0, SPACING["sm"]))

        # Телефон
        self._phone_entry = AppEntry(self._card, placeholder_text="+7 900 000-00-00")
        self._phone_entry.pack(padx=pad, fill="x", pady=(0, SPACING["xs"]))
        self._phone_entry.bind("<Return>", lambda _: self._on_action())

        # Код (скрыт)
        self._code_entry = AppEntry(self._card, placeholder_text="Код из Telegram")
        self._code_entry.bind("<Return>", lambda _: self._on_action())

        # 2FA пароль (скрыт) + кнопка показа
        self._pwd_frame = ctk.CTkFrame(
            self._card,
            fg_color=C["surface"],
            border_width=1,
            border_color=C["border"],
            corner_radius=RADIUS["md"],
        )
        self._pwd_entry = AppEntry(
            self._pwd_frame, placeholder_text="Пароль 2FA", show="•",
            border_width=0, fg_color="transparent",
        )
        self._pwd_entry.pack(side="left", fill="x", expand=True, padx=(SPACING["xs"], 0))
        self._pwd_entry.bind("<Return>", lambda _: self._on_action())
        self._pwd_visible = False
        self._eye_btn = ctk.CTkButton(
            self._pwd_frame, text="👁", width=28, height=28,
            fg_color="transparent", hover_color=C["border"],
            text_color=C["text_sec"], font=font(13),
            corner_radius=RADIUS["sm"],
            command=self._toggle_pwd_visibility,
        )
        self._eye_btn.pack(side="left", padx=(0, SPACING["xs"]))

        # Inline ошибка
        self._error_lbl = ctk.CTkLabel(
            self._card, text="", font=font(12), text_color=C["error"],
            wraplength=300,
        )
        self._error_lbl.pack(padx=pad, pady=(0, SPACING["sm"]))

        # Главная кнопка действия
        self._action_btn = AppButton(
            self._card, text="Получить код", command=self._on_action,
        )
        self._action_btn.pack(padx=pad, fill="x", pady=(0, SPACING["2xl"]))

        # ---- QR-режим (скрыт по умолчанию, не пакуется) ----
        self._qr_frame = ctk.CTkFrame(self._card, fg_color="transparent")
        self._qr_widget = QRCodeWidget(self._qr_frame, size_px=220)
        self._qr_widget.pack(pady=(0, SPACING["sm"]))
        self._qr_status = ctk.CTkLabel(
            self._qr_frame,
            text="Отсканируйте код в приложении Telegram",
            font=font(12),
            text_color=C["text_sec"],
            wraplength=300,
        )
        self._qr_status.pack(pady=(0, SPACING["sm"]))
        # Кнопка обновления кода — показывается только после истечения/ошибки.
        self._qr_refresh_btn = AppButton(
            self._qr_frame, text="Обновить код", variant="secondary", size="sm",
            command=self._app.refresh_qr,
        )
        # Кнопка подтверждения пароля 2FA в QR-режиме — показывается по on_qr_2fa.
        self._qr_2fa_btn = AppButton(
            self._qr_frame, text="Войти", size="sm",
            command=self._on_qr_2fa_submit,
        )

    # ---- Public API ----

    def reset_to_phone_mode(self) -> None:
        """
        Сбрасывает экран входа в режим «По номеру» (вызывать при показе login,
        напр. после logout из QR-режима — иначе остаётся залипший QR-вид).
        """
        if self._mode_var.get() != "По номеру":
            self._mode_var.set("По номеру")
            self._on_mode_change("По номеру")

    def refresh_state(self) -> None:
        """Вызывается App после изменения config / credentials."""
        has_creds = self._app.has_api_creds()
        if has_creds:
            self._api_lbl.configure(text="API ключи настроены ✓", text_color=C["success"])
            self._settings_btn.configure(text="Изменить API ключи")
            # before=_phone_entry только если он в packing-порядке (в QR-режиме
            # или когда login скрыт он может быть unpacked → TclError на before=).
            pk = dict(padx=SPACING["3xl"], fill="x", pady=(0, SPACING["xl"]))
            if self._phone_entry.winfo_ismapped():
                pk["before"] = self._phone_entry
            self._show_widget(self._clear_api_btn, **pk)
            self._phone_entry.configure(state="normal")
            self._action_btn.configure(state="normal")
        else:
            self._api_lbl.configure(text="Укажите API ID и API Hash", text_color=C["error"])
            self._settings_btn.configure(text="Настроить API ключи")
            self._hide_widget(self._clear_api_btn)
            self._phone_entry.configure(state="disabled")
            self._action_btn.configure(state="disabled")
        self.clear_error()

    def show_code_input(self) -> None:
        """Переключается в состояние ввода кода."""
        self._state = "code"
        self._phone_entry.configure(state="disabled")
        self._show_widget(self._code_entry, padx=SPACING["3xl"], fill="x",
                          pady=(0, SPACING["xs"]), before=self._error_lbl)
        self._show_widget(self._pwd_frame, padx=SPACING["3xl"], fill="x",
                          pady=(0, SPACING["xs"]), before=self._error_lbl)
        self._action_btn.set_idle_text("Войти")
        self._action_btn.set_loading(False)
        self._card.place_configure(relheight=0.80)
        self._code_entry.focus()

    def set_loading(self, loading: bool) -> None:
        self._state = "loading" if loading else self._state
        self._action_btn.set_loading(loading, "Подключение...")
        self._phone_entry.configure(state="disabled" if loading else "normal")

    def set_error(self, msg: str) -> None:
        self._error_lbl.configure(text=msg)
        self._action_btn.set_loading(False)
        self._state = "phone" if self._state == "loading" else self._state

    def clear_error(self) -> None:
        self._error_lbl.configure(text="")

    @property
    def phone(self) -> str:
        return self._phone_entry.get().strip()

    @property
    def code(self) -> str:
        return self._code_entry.get().strip()

    @property
    def password(self) -> str:
        return self._pwd_entry.get().strip()

    # ---- QR-события (вызываются App через EventDispatcher) ----

    def on_qr_ready(self, url: str) -> None:
        """Получен токен входа — рисуем QR и просим отсканировать."""
        self._qr_widget.set_data(url)
        self._qr_status.configure(
            text="Отсканируйте код в приложении Telegram",
            text_color=C["text_sec"],
        )
        self._hide_widget(self._qr_refresh_btn)

    def on_qr_2fa(self) -> None:
        """QR-вход требует пароль 2FA — показываем поле пароля и кнопку «Войти»."""
        self._hide_widget(self._qr_refresh_btn)
        self._qr_status.configure(text="Введите пароль 2FA", text_color=C["text_sec"])
        # _pwd_frame — ребёнок карточки; показываем его перед строкой ошибки.
        self._show_widget(self._pwd_frame, padx=SPACING["3xl"], fill="x",
                          pady=(0, SPACING["sm"]), before=self._error_lbl)
        # Кнопка «Войти» — ребёнок _qr_frame, под статусом.
        self._show_widget(self._qr_2fa_btn, pady=(0, SPACING["sm"]))
        self._pwd_entry.focus()

    def on_qr_expired(self) -> None:
        """Токен устарел — предлагаем обновить код."""
        self._qr_status.configure(
            text="Код устарел. Нажмите «Обновить».",
            text_color=C["warning"],
        )
        self._show_widget(self._qr_refresh_btn, pady=(0, SPACING["sm"]))

    def on_qr_error(self, msg: str) -> None:
        """Ошибка QR-входа — показываем сообщение и кнопку обновления."""
        self._qr_status.configure(text=msg, text_color=C["error"])
        self._show_widget(self._qr_refresh_btn, pady=(0, SPACING["sm"]))

    # ---- Handlers ----

    def _on_mode_change(self, value: str) -> None:
        if value == "QR-код":
            # QR-вход требует API-кредов (как и вход по номеру).
            if not self._app.has_api_creds():
                self.set_error("Сначала укажите API ID и API Hash")
                self._mode_var.set("По номеру")
                return
            # Скрываем виджеты входа по номеру.
            self._hide_widget(self._phone_entry)
            self._hide_widget(self._code_entry)
            self._hide_widget(self._pwd_frame)
            self._hide_widget(self._action_btn)
            self._hide_widget(self._clear_api_btn)
            # Показываем QR-блок.
            self.clear_error()
            self._hide_widget(self._qr_refresh_btn)
            self._hide_widget(self._qr_2fa_btn)
            self._qr_status.configure(text="Запрашиваю код…", text_color=C["text_sec"])
            self._show_widget(self._qr_frame, pady=(0, SPACING["md"]),
                              before=self._error_lbl)
            self._card.place_configure(relheight=0.86)
            self._app.start_qr_login()
        else:
            # Возврат в режим входа по номеру.
            self._app.stop_qr_login()
            self._hide_widget(self._qr_frame)
            self._hide_widget(self._qr_refresh_btn)
            self._hide_widget(self._qr_2fa_btn)
            self._hide_widget(self._pwd_frame)  # мог остаться от QR-2FA
            self._code_entry.clear()
            self._pwd_entry.clear()
            self._qr_widget.clear()
            self._state = "phone"
            # Сначала возвращаем поле телефона в packing-порядок (до refresh_state,
            # который ссылается на него через before=), затем кнопку действия.
            self._show_widget(self._phone_entry, padx=SPACING["3xl"], fill="x",
                              pady=(0, SPACING["xs"]), before=self._error_lbl)
            self._show_widget(self._action_btn, padx=SPACING["3xl"], fill="x",
                              pady=(0, SPACING["2xl"]))
            self._action_btn.set_idle_text("Получить код")
            self.refresh_state()
            self._card.place_configure(relheight=0.72)

    def _on_qr_2fa_submit(self) -> None:
        self.clear_error()
        pwd = self._pwd_entry.get().strip()
        if not pwd:
            self._qr_status.configure(text="Введите пароль 2FA", text_color=C["error"])
            return
        self._qr_status.configure(text="Проверяю пароль…", text_color=C["text_sec"])
        self._app.verify_qr_password(pwd)

    def _on_action(self) -> None:
        self.clear_error()
        if self._state == "phone":
            phone = self.phone
            if not phone:
                self.set_error("Введите номер телефона")
                return
            self.set_loading(True)
            self._app.send_code(phone)
        elif self._state in ("code", "loading"):
            code = self.code
            if not code:
                self.set_error("Введите код из Telegram")
                return
            self.set_loading(True)
            self._app.verify_code(code, self.password)

    def _toggle_pwd_visibility(self) -> None:
        self._pwd_visible = not self._pwd_visible
        self._pwd_entry.set_show("" if self._pwd_visible else "•")
        self._eye_btn.configure(text="🙈" if self._pwd_visible else "👁")

    def _on_clear_api(self) -> None:
        import tkinter.messagebox as mb
        if mb.askyesno(
            "Сбросить API ключи",
            "Удалить API ID/Hash и сессию? После этого нужно будет ввести ключи заново.",
        ):
            self._app.clear_api_creds()

    # ---- Layout helpers ----

    def _show_widget(self, widget, **pack_kw) -> None:
        if not widget.winfo_ismapped():
            widget.pack(**pack_kw)

    def _hide_widget(self, widget) -> None:
        if widget.winfo_ismapped():
            widget.pack_forget()
