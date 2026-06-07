"""
ProxyModal — настройка прокси для активного аккаунта.

Прокси применяется ко ВСЕМУ трафику аккаунта (вход + экспорт). Несекретная
часть (тип/host/port/username) хранится в profiles.json (Profile.proxy),
полная строка с паролем/секретом — в Keyring (см. ProfileManager.load_proxy/
set_proxy). Модалка собирает строку из полей, предзаполняет из сохранённого
значения и проверяет связь кнопкой «Тест связи» (через App →
TelegramClientManager.test_proxy в фоне).

UI не импортирует Telethon: парсинг/сборка URL берётся из core/proxy.py
(чистый модуль; Telethon там грузится лениво только внутри to_telethon()).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import customtkinter as ctk

from ..theme import C, SPACING, WIDGET, font, font_display
from ..components.button import AppButton
from ..components.entry import AppEntry
from ..modal_utils import prepare_modal, show_modal

if TYPE_CHECKING:
    from ..app import App

# display-метка ↔ kind ядра. «Без прокси» = пустая строка proxy у профиля.
_KIND_LABELS = {
    "":        "Без прокси (прямое соединение)",
    "socks5":  "SOCKS5",
    "http":    "HTTP",
    "mtproto": "MTProto",
}


class ProxyModal(ctk.CTkToplevel):

    def __init__(self, app: "App", phone: Optional[str] = None) -> None:
        super().__init__(app)
        prepare_modal(self, app, 480, 560, "Прокси аккаунта")
        self._app = app
        # phone=None — режим «временный прокси для входа» (профиля ещё нет):
        # значение хранится в App.pending_proxy и применяется к клиенту до логина.
        self._phone = phone
        self._build()
        self._load()
        show_modal(self, app)

    # ------------------------------------------------------------------ build

    def _build(self) -> None:
        pad = SPACING["2xl"]

        ctk.CTkLabel(
            self, text="Прокси для аккаунта",
            font=font_display(16, "bold"), text_color=C["text"],
        ).pack(pady=(pad, SPACING["xs"]))
        ctk.CTkLabel(
            self,
            text="Позволяет входить и экспортировать без системного VPN — "
                 "через прокси идёт только трафик Telegram.",
            font=font(11), text_color=C["text_sec"],
            wraplength=400, justify="center",
        ).pack(pady=(0, SPACING["md"]))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="x", padx=pad)

        # Тип
        self._row_label(body, "Тип прокси")
        self._kind_var = ctk.StringVar(value="")
        self._kind_menu = ctk.CTkOptionMenu(
            body, values=list(_KIND_LABELS.values()),
            command=self._on_kind_change,
            height=WIDGET["entry_h_sm"], font=font(13),
        )
        self._kind_menu.pack(fill="x", pady=(SPACING["xs"], SPACING["md"]))

        # Контейнер полей (скрывается целиком при «Без прокси»)
        self._fields = ctk.CTkFrame(body, fg_color="transparent")
        self._fields.pack(fill="x")

        # host + port в одном ряду
        self._row_label(self._fields, "Адрес и порт")
        hp = ctk.CTkFrame(self._fields, fg_color="transparent")
        hp.pack(fill="x", pady=(SPACING["xs"], SPACING["sm"]))
        self._host_entry = AppEntry(hp, placeholder_text="proxy.example.com", size="md")
        self._host_entry.pack(side="left", expand=True, fill="x", padx=(0, SPACING["sm"]))
        self._port_entry = AppEntry(hp, placeholder_text="порт", size="md", width=90)
        self._port_entry.pack(side="left")

        # auth-блок (socks5/http): логин/пароль
        self._auth_block = ctk.CTkFrame(self._fields, fg_color="transparent")
        self._row_label(self._auth_block, "Логин (если нужен)")
        self._user_entry = AppEntry(self._auth_block, placeholder_text="необязательно", size="md")
        self._user_entry.pack(fill="x", pady=(SPACING["xs"], SPACING["sm"]))
        self._row_label(self._auth_block, "Пароль (если нужен)")
        self._pass_entry = AppEntry(
            self._auth_block, placeholder_text="необязательно", show="•", size="md",
        )
        self._pass_entry.pack(fill="x", pady=(SPACING["xs"], 0))

        # secret-блок (mtproto)
        self._secret_block = ctk.CTkFrame(self._fields, fg_color="transparent")
        self._row_label(self._secret_block, "Секрет MTProto")
        self._secret_entry = AppEntry(
            self._secret_block, placeholder_text="hex или base64", size="md",
        )
        self._secret_entry.pack(fill="x", pady=(SPACING["xs"], 0))

        # Статус (результат теста / ошибки)
        self._status_lbl = ctk.CTkLabel(
            self, text="", font=font(11),
            text_color=C["text_sec"], wraplength=400, justify="left", anchor="w",
        )
        self._status_lbl.pack(fill="x", padx=pad, pady=(SPACING["sm"], 0))

        # Кнопки: «Тест связи» сверху отдельной строкой, ниже Отмена/Сохранить
        self._test_btn = AppButton(
            self, text="Проверить связь", variant="secondary", size="md",
            command=self._on_test,
        )
        self._test_btn.pack(fill="x", padx=pad, pady=(SPACING["md"], SPACING["sm"]))

        btn_row = ctk.CTkFrame(self, fg_color="transparent", height=WIDGET["btn_h"])
        btn_row.pack(side="bottom", fill="x", padx=pad, pady=(0, pad))
        btn_row.pack_propagate(False)
        AppButton(btn_row, text="Отмена", variant="secondary", size="md",
                  command=self.destroy).pack(
            side="left", expand=True, fill="both", padx=(0, SPACING["sm"]),
        )
        AppButton(btn_row, text="Сохранить", variant="primary", size="md",
                  command=self._on_save).pack(side="left", expand=True, fill="both")

    # ------------------------------------------------------------------ helpers

    def _row_label(self, parent, text: str) -> None:
        ctk.CTkLabel(
            parent, text=text, font=font(12),
            text_color=C["text_sec"], anchor="w",
        ).pack(fill="x")

    def _on_kind_change(self, display_val: str) -> None:
        kind = next((k for k, v in _KIND_LABELS.items() if v == display_val), "")
        self._kind_var.set(kind)
        self._apply_kind_visibility(kind)

    def _apply_kind_visibility(self, kind: str) -> None:
        # Прячем всё, затем показываем нужное
        self._fields.pack_forget()
        self._auth_block.pack_forget()
        self._secret_block.pack_forget()
        self._test_btn.configure(state="normal" if kind else "disabled")
        if not kind:
            return
        self._fields.pack(fill="x")
        if kind == "mtproto":
            self._secret_block.pack(fill="x", pady=(SPACING["sm"], 0))
        else:  # socks5 / http
            self._auth_block.pack(fill="x", pady=(SPACING["sm"], 0))

    # ------------------------------------------------------------------ load/save

    def _load(self) -> None:
        if self._phone is None:
            # Режим входа: временный прокси из App.
            raw = self._app.pending_proxy
        else:
            profile = self._app._profiles.get(self._phone)
            # Полная строка (с паролем/секретом) из Keyring — чтобы предзаполнить
            # все поля. В profile.proxy лежит только public-часть.
            raw = self._app._profiles.load_proxy(profile) if profile else ""
        kind = ""
        unparsable = False
        if raw:
            # Разбираем сохранённую строку в поля. Парс из core/proxy (без Telethon).
            from ...core.proxy import parse_proxy, ProxyValidationError
            try:
                cfg = parse_proxy(raw)
            except ProxyValidationError:
                cfg = None
            if cfg is not None:
                kind = cfg.kind
                self._host_entry.set_text(cfg.host)
                self._port_entry.set_text(str(cfg.port))
                if cfg.username:
                    self._user_entry.set_text(cfg.username)
                if cfg.password:
                    self._pass_entry.set_text(cfg.password)
                if cfg.secret:
                    self._secret_entry.set_text(cfg.secret)
            else:
                # Сохранённая строка не распарсилась. НЕ обнуляем молча —
                # предупреждаем, чтобы пользователь не потерял прокси при Save.
                unparsable = True
        self._kind_var.set(kind)
        self._kind_menu.set(_KIND_LABELS.get(kind, _KIND_LABELS[""]))
        self._apply_kind_visibility(kind)
        if unparsable:
            self._set_status(
                "Сохранённый прокси не распознан — заполните поля заново "
                "и сохраните, иначе он останется без изменений.",
                error=True,
            )

    def _build_url(self) -> str:
        """Собирает URL-строку из полей. "" — без прокси."""
        from ...core.proxy import build_proxy_url
        return build_proxy_url(
            self._kind_var.get(),
            self._host_entry.get(),
            self._port_entry.get(),
            self._user_entry.get(),
            self._pass_entry.get(),
            self._secret_entry.get(),
        )

    def _validate(self) -> tuple[bool, str]:
        """Проверяет, что строка парсится. Возвращает (ok, url_or_error)."""
        url = self._build_url()
        if not url:
            return True, ""  # «без прокси» — валидно
        from ...core.proxy import parse_proxy, ProxyValidationError
        try:
            parse_proxy(url)
        except ProxyValidationError as exc:
            return False, str(exc)
        return True, url

    def _on_test(self) -> None:
        ok, url_or_err = self._validate()
        if not ok:
            self._set_status(url_or_err, error=True)
            return
        if not url_or_err:
            self._set_status("Выбран режим без прокси — проверять нечего.", error=False)
            return
        self._test_btn.set_loading(True, "Проверка...")
        self._set_status("Подключаюсь через прокси…", error=False)
        self._app.test_account_proxy(self, url_or_err)

    def _on_save(self) -> None:
        ok, url_or_err = self._validate()
        if not ok:
            self._set_status(url_or_err, error=True)
            return
        if self._phone is None:
            # Режим входа: сохраняем как временный прокси и применяем к клиенту,
            # чтобы первый вход (send_code) пошёл через него.
            self._app.set_pending_proxy(url_or_err)
        else:
            self._app._profiles.set_proxy(self._phone, url_or_err)
            # Если правим активный профиль — применим прокси немедленно к клиенту.
            active = self._app.active_profile()
            if active and active.phone == self._phone:
                self._app.apply_active_proxy(url_or_err)
        self.destroy()

    # ------------------------------------------------------------------ ui updates (из App)

    def on_test_result(self, ok: bool, message: str) -> None:
        try:
            self._test_btn.set_loading(False)
        except Exception:
            pass
        self._set_status(message, error=not ok)

    def _set_status(self, text: str, error: bool) -> None:
        self._status_lbl.configure(text=text, text_color=C["error"] if error else C["text_sec"])
