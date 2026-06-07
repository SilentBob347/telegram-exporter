# Дизайн: Боковое меню + страницы (рефакторинг навигации UI)

**Дата:** 2026-06-06
**Статус:** утверждён, готов к реализации
**Ветка:** `feature/sidebar-navigation`
**Мотивация:** в шапке `ChatListView` накопилась куча кнопок (Аккаунт ▾,
Настройки, Инструкция, Выход, Обновить + панель фильтров) — становится
непонятно. Переходим на постоянное **боковое меню слева** с отдельными
страницами справа.

## Согласованные решения (через визуальный прототип)

1. **Раскладка меню:** вариант A — иконка + текстовая подпись, ширина ~200px.
2. **Пункты меню:** 💬 Чаты · 👤 Аккаунты · ⚙️ Настройки · 📖 Инструкция,
   внизу ↩ Выход. (4 страницы + выход.)
3. **Окно экспорта:** остаётся модалкой поверх (Вариант 1) — минимум переделок,
   логика ExportModal не трогается.

## Архитектура

### Каркас окна

Вместо текущего `_container` с переключением `login_view`/`chats_view`:

```
App (CTk)
│
├── (LOGIN-режим) LoginView на всё окно, sidebar СКРЫТ
│
└── (SHELL-режим, после входа)
    ├── Sidebar (слева, 200px, постоянный)
    └── PageContainer (справа)
        ├── ChatsPage     (из ChatListView, без глобальных кнопок)
        ├── AccountsPage  (новая — карточки аккаунтов)
        ├── SettingsPage  (SettingsModal + ApiKeysModal, объединены)
        └── HelpPage      (из HelpModal)
```

- **Login-режим:** sidebar скрыт, `LoginView` занимает всё окно (как сейчас).
- После успешного входа → показать sidebar + ChatsPage.
- После `logout` → скрыть sidebar, вернуть LoginView.
- **Механизм страниц:** `App._show_page(name)` — pack_forget текущей / pack новой
  (тот же приём, что сейчас `_switch_view`). Страницы создаются один раз.

### Что страница, что модалка

| Было | Стало |
| --- | --- |
| SettingsModal + ApiKeysModal | **SettingsPage** (одна страница, 2 секции) |
| HelpModal | **HelpPage** |
| Меню «Аккаунт ▾» (popup) | **AccountsPage** (карточки) |
| ExportModal | **остаётся модалкой** |
| AddAccountModal, ProxyModal | **остаются модалками** (вызов из AccountsPage/Login) |

## Файлы

| Файл | Действие | Содержание |
| --- | --- | --- |
| `ui/components/sidebar.py` | новый | `Sidebar(master, app)`: бренд + nav-кнопки + Выход. `set_active(page)` подсветка. Использует AppButton/theme. |
| `ui/views/chats_page.py` | новый (из chat_list_view.py) | Список чатов + папка/период/поиск/обновить + экспорт. БЕЗ глобальных кнопок (ушли в sidebar). Без account-switcher в шапке. |
| `ui/views/accounts_page.py` | новый | Карточки аккаунтов: активный отмечен; «Сделать активным»/«🌐 Прокси»/«Удалить»; «+ Добавить аккаунт»; «📷 Войти по QR» (пока → AddAccountModal; полноценный QR — отдельная фича #1). |
| `ui/views/settings_page.py` | новый (из settings_modal.py + api_keys_modal.py) | API-ключи (id/hash) + транскрипция (провайдер/модель/язык/Deepgram) одной прокручиваемой страницей. |
| `ui/views/help_page.py` | новый (из help_modal.py) | Контент справки как страница. |
| `ui/app.py` | правка | `_setup_window` (шире окно), `_build_shell` (sidebar+container), `_show_page`, навигация login↔shell. `show_settings/show_api_keys/show_help` → `_show_page`. |
| `ui/theme.py` | правка | WINDOW size шире под меню; токены sidebar при необходимости. |
| `ui/views/settings_modal.py`, `api_keys_modal.py`, `help_modal.py`, `chat_list_view.py` | удалить | после переноса и проверки. |

**Принцип:** существующая бизнес-логика (методы App, события, worker) НЕ
меняется — только UI-обёртка. Это снижает риск регрессий.

## Карта переноса функционала (НИЧЕГО не теряем)

Полная инвентаризация 35 публичных методов App + все show_*.

### Навигация (механизм меняется, функция сохраняется)

| Метод App | Было | Стало |
| --- | --- | --- |
| `show_settings` | модалка | `_show_page("settings")` |
| `show_api_keys` | модалка | сливается в SettingsPage (секция API) |
| `show_help` | модалка | `_show_page("help")` |
| `show_chats` | view | `_show_page("chats")` |
| `show_login` | view | login-режим (sidebar скрыт) |
| *(новое)* | — | `_show_page("accounts")` |
| `show_add_account`, `show_proxy_settings`, `show_login_proxy`, `show_export_dialog` | модалки | остаются модалками, вызов из страниц |

### Действия (логика не трогается, меняется только точка вызова)

| Группа | Методы App | Вызывается из |
| --- | --- | --- |
| Аутентификация | send_code, verify_code, logout, has_api_creds | LoginView; logout — из Sidebar |
| API-конфиг | save_config, clear_api_creds | SettingsPage |
| Чаты | load_chats, filter_chats, set_current_folder, set_date_period, set_custom_date_range | ChatsPage |
| Экспорт | start_export, cancel_export, export_current_folder | ChatsPage + ExportModal |
| Профили | profiles, active_profile, switch_profile, remove_profile, save_active_profile_session | AccountsPage |
| Прокси | pending_proxy, set_pending_proxy, test_account_proxy, apply_active_proxy | AccountsPage + ProxyModal + LoginView |
| Транскрипция | set_transcription_provider, set_local_whisper_model | SettingsPage |

### События (`_register_handlers`) — НЕ меняются

Все ~25 событий сохраняются (login_*, add_account_*, proxy_test_result,
chats_loaded/failed, folders_loaded, error/info, export_* (start/progress/
status/done/error/cancelled), model_download_progress, folder_progress/done,
profile_switched). Меняются только адресаты обновлений в обработчиках:
`self.chats_view` → `self.chats_page` и т.п.

### Гарантия полноты

- Ни один из 35 методов App не удаляется. `show_settings/api_keys/help` лишь
  меняют тело на `_show_page`.
- Каждый контрол из текущей шапки ChatListView имеет адрес: глобальные
  (Настройки/Инструкция/Выход/Аккаунт) → sidebar/страницы; фильтры/экспорт
  (папка/период/поиск/обновить/экспорт) → ChatsPage.
- account-switcher popup-меню (switch/add/remove/proxy) → AccountsPage карточки.

## Обработка состояний и edge-кейсы

| Случай | Поведение |
| --- | --- |
| Нет API-ключей | LoginView показывает форму; sidebar скрыт до входа. Кнопка «Настройки» в sidebar доступна только в shell-режиме. |
| Logout | Скрыть sidebar, очистить страницы-состояние при необходимости, показать LoginView. |
| Переключение аккаунта (AccountsPage) | `switch_profile` (фон) → по `profile_switched` обновить ChatsPage И автоматически перейти на страницу «Чаты» (наглядно: видно, что аккаунт сменился и чаты перезагрузились). Карточки AccountsPage обновляют пометку «активный». |
| Окно уже узкое | min_size увеличить так, чтобы 200px меню + список помещались (≥ 860×600). |
| Активная вкладка при старте | После входа активна «Чаты». |

## Тестирование / верификация (КРИТИЧНО — ничего не потерять)

1. Все 232 существующих unit-теста проходят (логика не менялась).
2. Tk нельзя в фоне (SIGSEGV) → ручная проверка по чек-листу каждого пункта:
   - Чаты: список грузится, папка/период/поиск/обновить работают, экспорт
     чата (модалка) и папки запускаются, прогресс идёт.
   - Аккаунты: список карточек, переключение, добавить, прокси (модалка),
     удалить, вход по QR (→ AddAccountModal).
   - Настройки: API-ключи сохраняются, транскрипция-настройки сохраняются.
   - Инструкция: контент виден.
   - Выход: возврат на логин, повторный вход.
3. Компиляция всего пакета (`compileall`) без ошибок импорта.

## Вне scope (YAGNI)

- Узкое меню «только иконки» (выбран вариант A).
- Экспорт как панель справа (выбрана модалка).
- Полноценный вход по QR (отдельная фича #1 — кнопка пока ведёт в
  AddAccountModal).
- Анимации переходов между страницами (простой show/hide).
- Сворачивание/collapse сайдбара.
