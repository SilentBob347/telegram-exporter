"""HelpPage — пользовательская инструкция (two-pane: оглавление + контент)."""

from __future__ import annotations

from typing import TYPE_CHECKING
import customtkinter as ctk

from ..theme import C, RADIUS, SPACING, WIDGET, font, font_display
from ..modal_utils import setup_smooth_scroll

if TYPE_CHECKING:
    from ..app import App


# ---- Контент инструкции ----
# Структура данных: список из 7 разделов. Каждый раздел —
# {"icon": эмодзи, "title": заголовок, "items": [(название_подпункта, текст), ...]}.
# Рендер идёт циклом, дублирование текста исключено.

_SECTIONS: list[dict] = [
    {
        "icon": "🔑",
        "title": "1. Авторизация",
        "items": [
            ("API ключи",
             "При первом запуске нажмите «Настроить API ключи». Получите api_id и api_hash "
             "на https://my.telegram.org → API development tools. Введите их в окне настроек."),
            ("Вход",
             "Введите номер телефона в международном формате (например, +79991234567), "
             "получите код в Telegram, при необходимости введите 2FA-пароль."),
            ("Хранение секретов",
             "Все ключи и сессия сохраняются в системном Keyring (Связка ключей на macOS, "
             "Credential Manager на Windows). В файлах конфигурации секреты не хранятся."),
        ],
    },
    {
        "icon": "💬",
        "title": "2. Главный экран — список чатов",
        "items": [
            ("Папка",
             "Выпадающий список ваших папок Telegram. Выберите «Все чаты» или конкретную папку — "
             "список ниже отфильтруется."),
            ("Период",
             "Период, за который брать сообщения: Неделя, Месяц, 3 месяца, Год, Всё время. "
             "Опция «Свой период» открывает поля для ввода дат вручную (формат ГГГГ-ММ-ДД, "
             "локальное время)."),
            ("Поиск",
             "Поле поиска фильтрует список чатов по имени в реальном времени."),
            ("Обновить",
             "Перезагружает список диалогов и папок из Telegram."),
        ],
    },
    {
        "icon": "📤",
        "title": "3. Экспорт одного чата",
        "items": [
            ("Запуск",
             "Двойной клик по чату или выделить + кнопка «Экспортировать выбранный чат» внизу. "
             "Откроется окно экспорта с параметрами."),
            ("Формат",
             "JSON — машинно-читаемый формат, удобен для дальнейшей обработки. "
             "Markdown — человеко-читаемый, разбивается на части по количеству слов."),
            ("Медиа",
             "Включите чекбокс «Скачивать медиа» — фото, видео, документы будут сохранены "
             "в подпапки внутри директории экспорта."),
            ("Транскрипция",
             "Если включено, голосовые сообщения и видеокружки переводятся в текст. "
             "Провайдер выбирается в Настройках (локальный Whisper или облачный Deepgram). "
             "Лимит — 15 минут на сообщение."),
            ("Аналитика",
             "Дополнительно создаёт файлы top_authors.md (топ авторов) и activity.md "
             "(активность по датам)."),
            ("Фильтр по автору",
             "Опционально — экспортировать только сообщения от конкретного пользователя "
             "(по username или ID)."),
            ("Инкрементальный экспорт",
             "При повторном запуске экспортируются только новые сообщения с момента "
             "предыдущего экспорта (история хранится в ~/.tg_exporter/export_history.json)."),
        ],
    },
    {
        "icon": "📁",
        "title": "4. Экспорт целой папки",
        "items": [
            ("Запуск",
             "На главном экране выберите папку и нажмите «Экспортировать папку». "
             "Все чаты из папки добавятся в очередь экспорта."),
            ("Режим",
             "По чатам — каждый чат в свою подпапку (как обычный экспорт). "
             "Один .md на чат — каждый чат в один Markdown без разбивки. "
             "Один .md на папку — все чаты в один общий Markdown-файл."),
            ("Транскрипция",
             "Чекбокс рядом с кнопкой включает транскрипцию для всех чатов папки."),
        ],
    },
    {
        "icon": "⚙️",
        "title": "5. Настройки приложения",
        "items": [
            ("Транскрипция → Провайдер",
             "Локальный Whisper — работает офлайн, требует загрузки модели при первом "
             "использовании (от 75 МБ для tiny до 3 ГБ для large). "
             "Deepgram — облачный, требует API-ключ (получить на console.deepgram.com)."),
            ("Модель Whisper",
             "Tiny / Base — быстро, но ниже качество. Medium / Large — медленно, "
             "но высокое качество. Базовый выбор: Base — оптимальный баланс."),
            ("Язык",
             "«Авто» — определяется автоматически, медленнее. Указание конкретного языка "
             "ускоряет распознавание."),
            ("Экспорт по умолчанию",
             "Включать ли автора и временные метки в Markdown-файлы по умолчанию. "
             "Изменения применяются к новым экспортам."),
        ],
    },
    {
        "icon": "📂",
        "title": "6. Где находятся файлы",
        "items": [
            ("Результат экспорта",
             "В выбранной вами папке создаётся подпапка вида «Имя чата_2026-04-15_18-30-00» "
             "со всеми файлами внутри."),
            ("Конфигурация и логи",
             "Папка ~/.tg_exporter/ — config.json (несекретные настройки), app.log (лог), "
             "export_history.json (история инкрементальных экспортов)."),
        ],
    },
    {
        "icon": "💡",
        "title": "7. Полезные советы",
        "items": [
            ("Отмена экспорта",
             "Кнопка «Отмена» в окне экспорта останавливает процесс. Уже скачанные файлы "
             "и записанные сообщения сохраняются."),
            ("Большие чаты",
             "Для каналов с десятками тысяч сообщений рекомендуется указывать период "
             "(месяц/год) и использовать инкрементальный экспорт при повторных запусках."),
            ("Только одна сессия",
             "Параллельно запустить две копии приложения нельзя (используется один файл "
             "сессии). Закройте предыдущую копию перед запуском новой."),
        ],
    },
]

# Короткая подпись пункта оглавления (без длинного хвоста заголовка раздела).
_NAV_LABELS = [
    "Авторизация",
    "Главный экран",
    "Экспорт чата",
    "Экспорт папки",
    "Настройки",
    "Файлы",
    "Советы",
]

# Ширина левого оглавления.
_NAV_W = 220
# Перенос текста в карточках правой колонки.
_CARD_WRAP = 640


class HelpPage(ctk.CTkFrame):
    def __init__(self, master, app: "App") -> None:
        super().__init__(master, fg_color="transparent")
        self._app = app
        self._nav_buttons: list[ctk.CTkButton] = []
        self._active: int = 0
        self._build()
        # Один постоянный CTkScrollableFrame на всю жизнь страницы — скролл-бинд
        # ставим один раз, при переключении разделов меняем только содержимое.
        self.after(100, lambda: setup_smooth_scroll(self, self._scroll))

    def _build(self) -> None:
        pad = SPACING["2xl"]

        # Заголовок страницы.
        ctk.CTkLabel(self, text="Инструкция", font=font_display(20, "bold"),
                     text_color=C["text"]).pack(
                         anchor="w", padx=pad, pady=(pad, SPACING["lg"]))

        # Двухпанельный контейнер на grid (фиксированный layout — без морганий
        # при переключении разделов: колонки и строки не пересчитываются).
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=pad, pady=(0, pad))
        body.grid_columnconfigure(0, weight=0, minsize=_NAV_W)  # оглавление
        body.grid_columnconfigure(1, weight=1)                  # контент
        body.grid_rowconfigure(0, weight=1)

        # ---- ЛЕВО: оглавление (паттерн sidebar.py — CTkButton с подсветкой) ----
        nav = ctk.CTkFrame(body, fg_color=C["surface"], corner_radius=RADIUS["lg"],
                           width=_NAV_W)
        nav.grid(row=0, column=0, sticky="nsw", padx=(0, SPACING["lg"]))
        nav.grid_propagate(False)

        nav_inner = ctk.CTkFrame(nav, fg_color="transparent")
        nav_inner.pack(fill="x", padx=SPACING["sm"], pady=SPACING["sm"])

        for idx, section in enumerate(_SECTIONS):
            label = f"{section['icon']}   {idx + 1}. {_NAV_LABELS[idx]}"
            btn = ctk.CTkButton(
                nav_inner, text=label, anchor="w",
                font=font(13), height=WIDGET["btn_h"],
                fg_color="transparent", text_color=C["text_sec"],
                hover_color=C["card"], corner_radius=RADIUS["md"],
                command=lambda i=idx: self._select(i),
            )
            btn.pack(fill="x", pady=2)
            self._nav_buttons.append(btn)

        # ---- ПРАВО: постоянный скролл-фрейм с контентом раздела ----
        self._scroll = ctk.CTkScrollableFrame(body, fg_color=C["bg"])
        self._scroll.grid(row=0, column=1, sticky="nsew")

        # По умолчанию открыт раздел 1.
        self._select(0)

    def _select(self, idx: int) -> None:
        """Подсвечивает пункт оглавления и перестраивает правую колонку."""
        self._active = idx
        for i, btn in enumerate(self._nav_buttons):
            if i == idx:
                btn.configure(fg_color=C["primary"], text_color=C["primary_text"])
            else:
                btn.configure(fg_color="transparent", text_color=C["text_sec"])
        self._render_section(idx)

    def _render_section(self, idx: int) -> None:
        """Очищает содержимое постоянного скролл-фрейма и строит выбранный раздел.

        Скролл-бинд НЕ переустанавливаем: сам CTkScrollableFrame (и его
        внутренний _parent_canvas) живут всё время — пересоздаются только
        дочерние карточки. Это исключает повторные bind и моргание скролла.
        """
        section = _SECTIONS[idx]

        # Сброс прокрутки наверх при смене раздела.
        try:
            self._scroll._parent_canvas.yview_moveto(0.0)
        except Exception:
            pass

        for child in self._scroll.winfo_children():
            child.destroy()

        # Заголовок раздела.
        ctk.CTkLabel(self._scroll, text=section["title"], font=font(18, "bold"),
                     text_color=C["text"], anchor="w", justify="left",
                     wraplength=_CARD_WRAP).pack(
                         fill="x", pady=(SPACING["xs"], SPACING["md"]))

        # Подпункты — карточки-плашки.
        for name, text in section["items"]:
            card = ctk.CTkFrame(self._scroll, fg_color=C["card"],
                                corner_radius=RADIUS["md"])
            card.pack(fill="x", pady=(0, SPACING["sm"]))

            ctk.CTkLabel(card, text=name, font=font(13, "bold"),
                         text_color=C["text"], anchor="w", justify="left",
                         wraplength=_CARD_WRAP).pack(
                             fill="x", padx=SPACING["lg"],
                             pady=(SPACING["md"], SPACING["xs"]))
            ctk.CTkLabel(card, text=text, font=font(13),
                         text_color=C["text_sec"], anchor="w", justify="left",
                         wraplength=_CARD_WRAP).pack(
                             fill="x", padx=SPACING["lg"],
                             pady=(0, SPACING["md"]))
