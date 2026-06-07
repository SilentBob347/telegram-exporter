# Боковое меню + страницы — План реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Заменить шапку-с-кучей-кнопок на постоянное боковое меню слева с четырьмя страницами (Чаты, Аккаунты, Настройки, Инструкция) + Выход, не потеряв ни одной существующей функции.

**Architecture:** Окно делится на `Sidebar` (200px слева) + `PageContainer` (справа). При логине sidebar скрыт, `LoginView` на всё окно. После входа — sidebar + страницы. Страницы переключаются `App._show_page(name)` (pack/pack_forget). Бизнес-логика App (35 методов, ~25 событий) НЕ меняется — переносится только UI-обёртка. Settings+ApiKeys сливаются в одну страницу; Help и список аккаунтов становятся страницами; Export/AddAccount/Proxy остаются модалками.

**Tech Stack:** Python 3.11, CustomTkinter, stdlib unittest. Дизайн-токены — `tg_exporter/ui/theme.py`. Запуск тестов: `.venv/bin/python -m unittest discover tests`. Tk нельзя запускать в фоне (SIGSEGV) — UI проверяется компиляцией + ручным чек-листом.

**Спек:** `docs/superpowers/specs/2026-06-06-sidebar-navigation-design.md`

---

## File Structure

| Файл | Действие | Ответственность |
| --- | --- | --- |
| `ui/components/sidebar.py` | создать | Боковое меню: бренд, nav-кнопки, Выход, `set_active`. |
| `ui/views/help_page.py` | создать (из help_modal.py) | Справка как страница (CTkFrame). |
| `ui/views/settings_page.py` | создать (из settings_modal.py + api_keys_modal.py) | API-ключи + транскрипция, одна прокручиваемая страница. |
| `ui/views/accounts_page.py` | создать | Карточки аккаунтов + действия. |
| `ui/views/chats_page.py` | создать (из chat_list_view.py) | Список чатов + фильтры + экспорт, без глобальных кнопок. |
| `ui/app.py` | изменить | shell (sidebar+container), `_show_page`, навигация login↔shell, перевод `show_settings/api_keys/help` на страницы. |
| `ui/theme.py` | изменить | WINDOW шире; токен ширины sidebar. |
| `ui/views/{help_modal,settings_modal,api_keys_modal,chat_list_view}.py` | удалить | после переноса. |

Порядок задач: сначала независимые страницы-переносы (Help → Settings → Accounts → Chats), затем Sidebar, затем сшивка в App, затем удаление старого и финальная проверка. Каждая страница коммитится отдельно.

---

### Task 1: Расширить окно и добавить токен ширины sidebar

**Files:**
- Modify: `tg_exporter/ui/theme.py:108-114`

- [ ] **Step 1: Обновить WINDOW и добавить SIDEBAR_W**

В `tg_exporter/ui/theme.py` заменить блок `WINDOW`:

```python
# ---- Окно приложения ----

WINDOW = {
    "title":       "Telegram Exporter",
    "size":        "1040x720",
    "min_size":    (860, 600),
}

# Ширина бокового меню
SIDEBAR_W = 200
```

- [ ] **Step 2: Проверить, что тесты и импорт целы**

Run: `.venv/bin/python -c "from tg_exporter.ui.theme import WINDOW, SIDEBAR_W; print(WINDOW['size'], SIDEBAR_W)"`
Expected: `1040x720 200`

- [ ] **Step 3: Commit**

```bash
git add tg_exporter/ui/theme.py
git commit -m "feat(ui): шире окно под боковое меню + токен SIDEBAR_W"
```

---

### Task 2: HelpPage (перенос HelpModal в страницу)

**Files:**
- Read: `tg_exporter/ui/views/help_modal.py` (источник контента)
- Create: `tg_exporter/ui/views/help_page.py`

- [ ] **Step 1: Прочитать help_modal.py**

Run: `cat "tg_exporter/ui/views/help_modal.py"`
Цель: увидеть структуру контента (заголовки разделов + тексты) и helper-методы (`_section`, `_para` или подобные). Контент переносится дословно.

- [ ] **Step 2: Создать help_page.py**

Создать `tg_exporter/ui/views/help_page.py` как `ctk.CTkFrame` (не Toplevel). Каркас:

```python
"""HelpPage — пользовательская инструкция как страница (вместо модалки)."""

from __future__ import annotations

from typing import TYPE_CHECKING
import customtkinter as ctk

from ..theme import C, SPACING, font, font_display
from ..modal_utils import setup_smooth_scroll

if TYPE_CHECKING:
    from ..app import App


class HelpPage(ctk.CTkFrame):
    def __init__(self, master, app: "App") -> None:
        super().__init__(master, fg_color="transparent")
        self._app = app
        self._build()
        self.after(100, lambda: setup_smooth_scroll(self, self._scroll))

    def _build(self) -> None:
        pad = SPACING["2xl"]
        ctk.CTkLabel(
            self, text="Инструкция",
            font=font_display(20, "bold"), text_color=C["text"],
        ).pack(anchor="w", padx=pad, pady=(pad, SPACING["lg"]))

        self._scroll = ctk.CTkScrollableFrame(self, fg_color=C["bg"])
        self._scroll.pack(fill="both", expand=True, padx=pad, pady=(0, pad))

        # ВНИМАНИЕ: перенести сюда все разделы из help_modal.py дословно,
        # используя self._scroll как родителя. Ниже helper-методы.
        self._build_content(self._scroll)

    def _section(self, parent, title: str) -> None:
        ctk.CTkLabel(parent, text=title, font=font(14, "bold"),
                     text_color=C["text"], anchor="w",
                     justify="left", wraplength=700).pack(fill="x", pady=(SPACING["md"], SPACING["xs"]))

    def _para(self, parent, text: str) -> None:
        ctk.CTkLabel(parent, text=text, font=font(13),
                     text_color=C["text_sec"], anchor="w",
                     justify="left", wraplength=700).pack(fill="x", pady=(0, SPACING["sm"]))

    def _build_content(self, p) -> None:
        # Заполняется на Step 2b — дословный перенос разделов из help_modal.py.
        ...
```

- [ ] **Step 2b: Перенести контент разделов из help_modal.py (ОБЯЗАТЕЛЬНО, не `...`)**

Открыть `help_modal.py`, найти его `_build` (где создаются разделы справки). Для КАЖДОГО раздела вызвать `self._section(p, "<точный заголовок>")` + `self._para(p, "<точный текст>")`, скопировав строки дословно. Разделы (минимум, сверить с источником): авторизация, главный экран, экспорт чата, экспорт папки, настройки, файловая структура, советы. Заменить `...` в `_build_content` этими вызовами. После — в коде НЕ должно остаться `...` или `pass`.

Run после переноса: `grep -nE "\bpass\b|\.\.\.|TODO" tg_exporter/ui/views/help_page.py || echo "без заглушек"`
Expected: `без заглушек`

- [ ] **Step 3: Проверить компиляцию**

Run: `.venv/bin/python -m py_compile tg_exporter/ui/views/help_page.py && echo OK`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add tg_exporter/ui/views/help_page.py
git commit -m "feat(ui): HelpPage — справка как страница"
```

---

### Task 3: SettingsPage (Settings + ApiKeys в одну страницу)

**Files:**
- Read: `tg_exporter/ui/views/settings_modal.py`, `tg_exporter/ui/views/api_keys_modal.py`
- Create: `tg_exporter/ui/views/settings_page.py`

- [ ] **Step 1: Прочитать оба источника**

Run: `cat tg_exporter/ui/views/settings_modal.py tg_exporter/ui/views/api_keys_modal.py`
Цель: понять поля (api_id/api_hash из ApiKeysModal; provider/model/language/Deepgram из SettingsModal), их `_load`/`_save` логику и вызовы App (`save_config`, `set_transcription_provider`, `set_local_whisper_model`, `credentials.save_deepgram_key`).

- [ ] **Step 2: Создать settings_page.py**

Создать `ctk.CTkFrame` с двумя секциями. Каркас (детали полей перенести из источников):

```python
"""SettingsPage — API-ключи + транскрипция одной страницей (вместо 2 модалок)."""

from __future__ import annotations

import dataclasses
import webbrowser
from typing import TYPE_CHECKING
import customtkinter as ctk

from ..theme import C, SPACING, WIDGET, font, font_display
from ..components.button import AppButton
from ..components.entry import AppEntry
from ..modal_utils import setup_smooth_scroll

if TYPE_CHECKING:
    from ..app import App

_PROVIDER_LABELS = {"local": "Локальный Whisper", "deepgram": "Deepgram (облако)"}
_LANG_LABELS = {
    "multi": "Авто (несколько языков)", "ru": "Русский", "en": "Английский",
    "de": "Немецкий", "fr": "Французский", "es": "Испанский",
    "zh": "Китайский", "ja": "Японский",
}
_MODEL_LABELS = {
    "tiny": "Tiny (быстро, ниже качество)", "base": "Base (баланс)",
    "small": "Small", "medium": "Medium",
    "large": "Large (медленно, высокое качество)",
}


class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, app: "App") -> None:
        super().__init__(master, fg_color="transparent")
        self._app = app
        self._build()
        self.after(100, lambda: setup_smooth_scroll(self, self._scroll))

    def refresh(self) -> None:
        """Перечитать значения из config/credentials (вызывать при показе страницы)."""
        self._load()

    def _build(self) -> None:
        pad = SPACING["2xl"]
        ctk.CTkLabel(self, text="Настройки", font=font_display(20, "bold"),
                     text_color=C["text"]).pack(anchor="w", padx=pad, pady=(pad, SPACING["lg"]))
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=C["bg"])
        self._scroll.pack(fill="both", expand=True, padx=pad, pady=(0, pad))
        s = self._scroll
        # --- секция API (из api_keys_modal.py): поля _api_id_entry, _api_hash_entry ---
        # --- секция Транскрипция (из settings_modal.py): provider/model/deepgram/lang ---
        # Кнопка «Сохранить» → self._save()
        # ВАЖНО при реализации: перенести оба блока полей дословно из источников,
        # включая show="•" для api_hash и deepgram, ссылку my.telegram.org,
        # provider-переключение блоков (whisper/deepgram).
        self._build_api_section(s)
        ctk.CTkFrame(s, height=1, fg_color=C["border"]).pack(fill="x", pady=SPACING["lg"])
        self._build_transcription_section(s)
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=pad, pady=(0, pad))
        self._status_lbl = ctk.CTkLabel(btn_row, text="", font=font(12),
                                        text_color=C["success"])
        self._status_lbl.pack(side="left")
        AppButton(btn_row, text="Сохранить", variant="primary",
                  command=self._save).pack(side="right")
        self._load()

    # _build_api_section / _build_transcription_section / _load / _save —
    # перенести логику из api_keys_modal.py и settings_modal.py.
    # _save: вызывает self._app.save_config(api_id, api_hash) +
    #        self._app.set_transcription_provider/set_local_whisper_model +
    #        self._app.credentials.save_deepgram_key(...) — как в источниках.
```

- [ ] **Step 2b: Реализовать 4 метода переносом из источников (ОБЯЗАТЕЛЬНО)**

Реализовать (НЕ оставлять заглушек):
- `_build_api_section(self, s)` — из `api_keys_modal.py`: поля `_api_id_entry` (AppEntry) и `_api_hash_entry` (AppEntry, `show="•"`), подпись/ссылка `my.telegram.org`. Лейблы и плейсхолдеры скопировать дословно.
- `_build_transcription_section(self, s)` — из `settings_modal.py`: CTkOptionMenu провайдера (`_PROVIDER_LABELS`), блоки Whisper-модели (`_MODEL_LABELS`) и Deepgram-ключа (AppEntry `show="•"` + ссылка console.deepgram.com), CTkOptionMenu языка (`_LANG_LABELS`), переключение блоков по провайдеру (`_on_provider_change`). Скопировать дословно, заменив `self` родителя на переданный `s`.
- `_load(self)` — из обоих модалок: подставить текущие `self._app.config.api_id`, api_hash из `self._app.credentials.load_api_hash(...)`, provider/model/lang из config, deepgram-ключ из `credentials.load_deepgram_key()`.
- `_save(self)` — вызвать `self._app.save_config(api_id, api_hash)`, `self._app.set_transcription_provider(provider)`, `self._app.set_local_whisper_model(model)`, при deepgram — `self._app.credentials.save_deepgram_key(key)`, язык — через `dataclasses.replace(config, transcription_language=lang)` + `config.save()`. НЕ вызывать `self.destroy()` (это страница). Показать короткий статус «Сохранено ✓» в лейбле `self._status_lbl`.

После реализации проверить отсутствие заглушек:
Run: `grep -nE "\bpass\b|TODO|заглушк" tg_exporter/ui/views/settings_page.py || echo "без заглушек"`
Expected: `без заглушек`

- [ ] **Step 3: Проверить компиляцию**

Run: `.venv/bin/python -m py_compile tg_exporter/ui/views/settings_page.py && echo OK`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add tg_exporter/ui/views/settings_page.py
git commit -m "feat(ui): SettingsPage — API-ключи + транскрипция одной страницей"
```

---

### Task 4: AccountsPage (карточки аккаунтов вместо popup-меню)

**Files:**
- Read: `tg_exporter/ui/views/chat_list_view.py:284-324` (логика account-menu)
- Create: `tg_exporter/ui/views/accounts_page.py`

- [ ] **Step 1: Изучить account-menu логику**

Run: `sed -n '269,325p' tg_exporter/ui/views/chat_list_view.py`
Цель: понять вызовы App — `profiles()`, `active_profile()`, `switch_profile(phone)`, `remove_profile(phone)`, `show_add_account()`, `show_proxy_settings(phone)`, `load_proxy` для пометки «✓».

- [ ] **Step 2: Создать accounts_page.py**

```python
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
        """Перерисовать карточки (вызывать при показе и после изменений профилей)."""
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
        card = ctk.CTkFrame(self._scroll, fg_color=C["surface"],
                            corner_radius=RADIUS["lg"], border_width=1,
                            border_color=C["primary"] if is_active else C["border"])
        card.pack(fill="x", pady=(0, SPACING["sm"]))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=SPACING["lg"], pady=SPACING["md"])
        name = (profile.display_name or profile.phone or "").strip() or profile.phone
        title = name + ("   ● активный" if is_active else "")
        ctk.CTkLabel(inner, text=title, font=font(14, "bold"),
                     text_color=C["text"], anchor="w").pack(side="left")
        # Кнопки действий справа
        proxy_mark = " ✓" if (self._app._profiles.load_proxy(profile) or "").strip() else ""
        AppButton(inner, text="Удалить", variant="ghost", size="sm",
                  command=lambda ph=profile.phone: self._remove(ph)).pack(side="right")
        AppButton(inner, text=f"🌐 Прокси{proxy_mark}", variant="secondary", size="sm",
                  command=lambda ph=profile.phone: self._app.show_proxy_settings(ph)).pack(
                      side="right", padx=(0, SPACING["sm"]))
        if not is_active:
            AppButton(inner, text="Сделать активным", variant="secondary", size="sm",
                      command=lambda ph=profile.phone: self._app.switch_profile(ph)).pack(
                          side="right", padx=(0, SPACING["sm"]))

    def _remove(self, phone: str) -> None:
        if not mb.askyesno("Удалить аккаунт", f"Удалить профиль {phone} и его сессию?"):
            return
        self._app.remove_profile(phone)
        self.refresh()
```

- [ ] **Step 3: Проверить компиляцию**

Run: `.venv/bin/python -m py_compile tg_exporter/ui/views/accounts_page.py && echo OK`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add tg_exporter/ui/views/accounts_page.py
git commit -m "feat(ui): AccountsPage — карточки аккаунтов вместо popup-меню"
```

---

### Task 5: ChatsPage (из ChatListView, без глобальных кнопок)

**Files:**
- Read: `tg_exporter/ui/views/chat_list_view.py` (целиком)
- Create: `tg_exporter/ui/views/chats_page.py`

- [ ] **Step 1: Прочитать chat_list_view.py целиком**

Run: `cat tg_exporter/ui/views/chat_list_view.py`
Цель: перенести ВСЁ кроме header-кнопок и account-menu.

- [ ] **Step 2: Создать chats_page.py копией ChatListView с правками**

Скопировать `chat_list_view.py` → `chats_page.py`, переименовать класс `ChatListView` → `ChatsPage`, и:
- Удалить из `_build` секцию HEADER целиком (кнопки Инструкция/Выход/Настройки/Обновить/Аккаунт ▾ — строки ~59-83) — они теперь в sidebar.
- Вместо неё оставить компактный заголовок страницы + кнопку «Обновить» (Обновить специфична для списка чатов, оставляем на странице):

```python
        # === HEADER страницы (только заголовок + Обновить) ===
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=SPACING["xl"], pady=(SPACING["2xl"], SPACING["md"]))
        ctk.CTkLabel(header, text="Чаты", font=font_display(20, "bold"),
                     text_color=C["text"]).pack(side="left")
        AppButton(header, text="Обновить", variant="secondary", size="sm",
                  command=self._app.load_chats).pack(side="right")
```

- Удалить методы `_show_account_menu`, `_on_switch_profile`, `_on_remove_profile`, `refresh_account_switcher`, `_account_btn` (переехали в AccountsPage). Удалить импорт `tkinter as tk`? — НЕТ, `tk.StringVar`/`tk.Listbox` ещё используются, оставить.
- Метод `render_chats` больше не вызывает `refresh_account_switcher()` — убрать эту строку.
- Сохранить публичные методы: `show_loading`, `show_refreshing`, `render_chats`, `set_folders`, `set_status`, `selected_dialog` (они вызываются из App).

- [ ] **Step 3: Проверить компиляцию**

Run: `.venv/bin/python -m py_compile tg_exporter/ui/views/chats_page.py && echo OK`
Expected: `OK`

- [ ] **Step 4: Grep — не осталось ли ссылок на удалённые методы внутри chats_page**

Run: `grep -nE "refresh_account_switcher|_show_account_menu|_account_btn" tg_exporter/ui/views/chats_page.py || echo "чисто"`
Expected: `чисто`

- [ ] **Step 5: Commit**

```bash
git add tg_exporter/ui/views/chats_page.py
git commit -m "feat(ui): ChatsPage — список чатов без глобальных кнопок шапки"
```

---

### Task 6: Sidebar-компонент

**Files:**
- Create: `tg_exporter/ui/components/sidebar.py`

- [ ] **Step 1: Создать sidebar.py**

```python
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
        # Выход внизу
        spacer = ctk.CTkFrame(self, fg_color="transparent")
        spacer.pack(fill="both", expand=True)
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
```

- [ ] **Step 2: Проверить компиляцию**

Run: `.venv/bin/python -m py_compile tg_exporter/ui/components/sidebar.py && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add tg_exporter/ui/components/sidebar.py
git commit -m "feat(ui): Sidebar — боковое меню навигации"
```

---

### Task 7: Сшивка в App — shell, _show_page, навигация

**Files:**
- Modify: `tg_exporter/ui/app.py` (imports, __init__ views, _setup_window, show_* методы)

- [ ] **Step 1: Обновить импорты views в app.py**

Найти текущие импорты (`from .views.chat_list_view import ChatListView` и др.) и заменить на новые страницы:

```python
from .views.login_view import LoginView
from .views.chats_page import ChatsPage
from .views.accounts_page import AccountsPage
from .views.settings_page import SettingsPage
from .views.help_page import HelpPage
from .components.sidebar import Sidebar
```

Удалить импорты `SettingsModal`, `HelpModal`, `ChatListView` (если есть на уровне модуля).

- [ ] **Step 2: Переписать создание views в __init__ на shell-каркас**

Заменить блок (текущие строки ~106-110, где `_container`, `login_view`, `chats_view`):

```python
        # Views / Shell
        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True)

        # LOGIN-режим: login_view на всё окно
        self.login_view = LoginView(self._container, self)

        # SHELL-режим: sidebar + page_container
        self._shell = ctk.CTkFrame(self._container, fg_color="transparent")
        self.sidebar = Sidebar(self._shell, self, on_select=self._show_page)
        self.sidebar.pack(side="left", fill="y")
        self._page_container = ctk.CTkFrame(self._shell, fg_color="transparent")
        self._page_container.pack(side="left", fill="both", expand=True)

        self.chats_page = ChatsPage(self._page_container, self)
        self.accounts_page = AccountsPage(self._page_container, self)
        self.settings_page = SettingsPage(self._page_container, self)
        self.help_page = HelpPage(self._page_container, self)
        self._pages = {
            "chats": self.chats_page, "accounts": self.accounts_page,
            "settings": self.settings_page, "help": self.help_page,
        }
        self._current_page = None
        self._current_view = None
```

ВАЖНО: если в коде ниже есть ссылки `self.chats_view` — заменить все на `self.chats_page` (см. Step 6).

- [ ] **Step 3: Добавить методы навигации (рядом с show_login)**

Заменить тела `show_login`, `show_chats` и добавить `_show_shell`, `_show_page`:

```python
    def show_login(self) -> None:
        if hasattr(self, "_shell"):
            self._shell.pack_forget()
        self.login_view.pack(fill="both", expand=True)
        self._current_view = self.login_view
        self.login_view.refresh_state()
        if self.has_api_creds() and self._has_any_session():
            self._worker.submit(self._bg_check_session)

    def _show_shell(self) -> None:
        self.login_view.pack_forget()
        self._shell.pack(fill="both", expand=True)
        self._current_view = self._shell

    def show_chats(self) -> None:
        self._show_shell()
        self._show_page("chats")
        self.load_chats()

    def _show_page(self, name: str) -> None:
        page = self._pages.get(name)
        if page is None:
            return
        if self._current_page is not None:
            self._current_page.pack_forget()
        page.pack(fill="both", expand=True)
        self._current_page = page
        self.sidebar.set_active(name)
        # обновить данные страницы при показе
        if name == "accounts":
            page.refresh()
        elif name == "settings":
            page.refresh()
```

- [ ] **Step 4: Перевести show_settings/show_api_keys/show_help на страницы**

Заменить тела:

```python
    def show_settings(self) -> None:
        self._show_shell()
        self._show_page("settings")

    def show_api_keys(self) -> None:
        # API-ключи теперь часть страницы настроек
        self._show_shell()
        self._show_page("settings")

    def show_help(self) -> None:
        self._show_shell()
        self._show_page("help")
```

(`show_add_account`, `show_proxy_settings`, `show_login_proxy`, `show_export_dialog` — НЕ трогать, остаются модалками.)

- [ ] **Step 5: Обновить _setup_window (если нужно)**

Проверить, что `_setup_window` использует `WINDOW["size"]`/`WINDOW["min_size"]` из theme — они уже обновлены в Task 1, менять не нужно. Убедиться визуально:

Run: `sed -n '/def _setup_window/,/configure/p' tg_exporter/ui/app.py`
Expected: использует `WINDOW[...]`, без хардкода.

- [ ] **Step 6: Заменить все self.chats_view → self.chats_page**

Run: `grep -n "chats_view" tg_exporter/ui/app.py`
Для каждого вхождения заменить `self.chats_view` на `self.chats_page`. Затем проверить:
Run: `grep -n "chats_view" tg_exporter/ui/app.py || echo "не осталось"`
Expected: `не осталось`

- [ ] **Step 7: Обновить _on_profile_switched — перейти на Чаты**

Найти `_on_profile_switched` и убедиться, что после переключения показывается страница Чаты и обновляются карточки аккаунтов. Добавить в конец метода:

```python
        self.accounts_page.refresh()
        self._show_page("chats")
```

(Перед этим в методе уже есть перезагрузка чатов — не дублировать load_chats, только навигация + refresh карточек.)

- [ ] **Step 8: Проверить компиляцию app.py**

Run: `.venv/bin/python -m py_compile tg_exporter/ui/app.py && echo OK`
Expected: `OK`

- [ ] **Step 9: Прогнать все тесты**

Run: `.venv/bin/python -m unittest discover tests 2>&1 | tail -3`
Expected: `OK`, 232 теста.

- [ ] **Step 10: Commit**

```bash
git add tg_exporter/ui/app.py
git commit -m "feat(ui): сшивка shell — sidebar + страницы, навигация login↔shell"
```

---

### Task 8: Удалить старые модалки-источники и почистить ссылки

**Files:**
- Delete: `tg_exporter/ui/views/chat_list_view.py`, `settings_modal.py`, `api_keys_modal.py`, `help_modal.py`

- [ ] **Step 1: Найти все ссылки на удаляемые модули**

Run: `grep -rnE "chat_list_view|ChatListView|settings_modal|SettingsModal|api_keys_modal|ApiKeysModal|help_modal|HelpModal" tg_exporter/ --include=*.py`
Цель: убедиться, что вне удаляемых файлов ссылок не осталось (кроме, возможно, .spec hiddenimports). Если есть в app.py — исправить (должно быть уже сделано в Task 7).

- [ ] **Step 2: Удалить файлы**

```bash
git rm tg_exporter/ui/views/chat_list_view.py \
       tg_exporter/ui/views/settings_modal.py \
       tg_exporter/ui/views/api_keys_modal.py \
       tg_exporter/ui/views/help_modal.py
```

- [ ] **Step 3: Проверить компиляцию всего пакета**

Run: `.venv/bin/python -m compileall -q tg_exporter && echo "compileall OK"`
Expected: `compileall OK` (без ошибок импорта).

- [ ] **Step 4: Прогнать все тесты**

Run: `.venv/bin/python -m unittest discover tests 2>&1 | tail -3`
Expected: `OK`.

- [ ] **Step 5: Проверить .spec на ссылки на удалённые модули**

Run: `grep -nE "chat_list_view|settings_modal|api_keys_modal|help_modal" "Telegram Exporter.spec" || echo "spec чист"`
Expected: `spec чист` (если есть — удалить эти hiddenimports).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(ui): удалить старые модалки (перенесены в страницы)"
```

---

### Task 9: Финальная проверка и обновление CLAUDE.md

**Files:**
- Modify: `CLAUDE.md` (§4.6 UI, журнал изменений)

- [ ] **Step 1: Прогнать полный набор тестов**

Run: `.venv/bin/python -m unittest discover tests 2>&1 | tail -3`
Expected: `Ran 232 tests ... OK`

- [ ] **Step 2: Обновить §4.6 CLAUDE.md**

В разделе `### 4.6. tg_exporter/ui/` обновить описание `app.py` и `views/`:
- App теперь shell с Sidebar + страницами (chats/accounts/settings/help), `_show_page(name)`.
- views: ChatsPage, AccountsPage, SettingsPage, HelpPage (вместо ChatListView/SettingsModal/ApiKeysModal/HelpModal).
- components: добавлен Sidebar.

- [ ] **Step 3: Добавить запись в журнал CLAUDE.md**

Дописать в конец «Журнала изменений» запись формата `2026-06-06 — Рефакторинг UI: боковое меню + страницы — затронутые файлы — суть` со списком: новые sidebar.py/chats_page/accounts_page/settings_page/help_page, удалены 4 модалки, app.py shell+_show_page, theme WINDOW шире.

- [ ] **Step 4: Ручной чек-лист (пользователь запускает приложение)**

Запросить у пользователя ручную проверку (Tk нельзя в фоне): `! .venv/bin/python main.py`
Проверить каждый пункт:
- Логин → после входа появилось боковое меню, активна «Чаты».
- Чаты: список грузится, папка/период/поиск/Обновить, экспорт чата (модалка), экспорт папки.
- Аккаунты: карточки, «Сделать активным» переключает + переходит на Чаты, «🌐 Прокси» (модалка), «Удалить», «+ Добавить»/«QR» (модалка).
- Настройки: API-ключи и транскрипция сохраняются.
- Инструкция: контент виден, скроллится.
- Выход: возврат на логин, повторный вход работает.

- [ ] **Step 5: Commit (после подтверждения пользователя)**

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md — боковое меню + страницы (§4.6, журнал)"
```

---

## Verification (по спеку)

- [ ] Все 35 публичных методов App сохранены (только `show_settings/api_keys/help` меняют тело).
- [ ] Все ~25 событий `_register_handlers` работают (адресаты обновлены на `*_page`).
- [ ] 232 unit-теста проходят на каждом коммите, где менялась логика.
- [ ] `compileall tg_exporter` без ошибок.
- [ ] Ручной чек-лист пройден (Task 9 Step 4).
- [ ] 4 старых модалки удалены, ссылок не осталось.
