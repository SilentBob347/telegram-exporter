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
        ctk.CTkLabel(self, text="Инструкция", font=font_display(20, "bold"),
                     text_color=C["text"]).pack(anchor="w", padx=pad, pady=(pad, SPACING["lg"]))
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=C["bg"])
        self._scroll.pack(fill="both", expand=True, padx=pad, pady=(0, pad))
        self._build_content(self._scroll)

    def _section(self, parent, title: str) -> None:
        ctk.CTkLabel(parent, text=title, font=font(14, "bold"), text_color=C["text"],
                     anchor="w", justify="left", wraplength=720).pack(fill="x", pady=(SPACING["md"], SPACING["xs"]))

    def _sub(self, parent, text: str) -> None:
        ctk.CTkLabel(parent, text=text, font=font(13, "bold"), text_color=C["text"],
                     anchor="w", justify="left", wraplength=720).pack(fill="x", pady=(SPACING["xs"], 0))

    def _para(self, parent, text: str) -> None:
        ctk.CTkLabel(parent, text=text, font=font(13), text_color=C["text_sec"],
                     anchor="w", justify="left", wraplength=720).pack(fill="x", pady=(0, SPACING["sm"]))

    def _build_content(self, p) -> None:
        # 1. Авторизация
        self._section(p, "1. Авторизация")
        self._sub(p, "API ключи")
        self._para(p, "При первом запуске нажмите «Настроить API ключи». Получите api_id и api_hash на "
                      "https://my.telegram.org → API development tools. Введите их в окне настроек.")
        self._sub(p, "Вход")
        self._para(p, "Введите номер телефона в международном формате (например, +79991234567), "
                      "получите код в Telegram, при необходимости введите 2FA-пароль.")
        self._sub(p, "Хранение секретов")
        self._para(p, "Все ключи и сессия сохраняются в системном Keyring (Связка ключей на macOS, "
                      "Credential Manager на Windows). В файлах конфигурации секреты не хранятся.")

        # 2. Главный экран — список чатов
        self._section(p, "2. Главный экран — список чатов")
        self._sub(p, "Папка")
        self._para(p, "Выпадающий список ваших папок Telegram. Выберите «Все чаты» или конкретную папку — "
                      "список ниже отфильтруется.")
        self._sub(p, "Период")
        self._para(p, "Период, за который брать сообщения: Неделя, Месяц, 3 месяца, Год, Всё время. "
                      "Опция «Свой период» открывает поля для ввода дат вручную (формат ГГГГ-ММ-ДД, "
                      "локальное время).")
        self._sub(p, "Поиск")
        self._para(p, "Поле поиска фильтрует список чатов по имени в реальном времени.")
        self._sub(p, "Обновить")
        self._para(p, "Перезагружает список диалогов и папок из Telegram.")

        # 3. Экспорт одного чата
        self._section(p, "3. Экспорт одного чата")
        self._sub(p, "Запуск")
        self._para(p, "Двойной клик по чату или выделить + кнопка «Экспортировать выбранный чат» внизу. "
                      "Откроется окно экспорта с параметрами.")
        self._sub(p, "Формат")
        self._para(p, "JSON — машинно-читаемый формат, удобен для дальнейшей обработки. "
                      "Markdown — человеко-читаемый, разбивается на части по количеству слов.")
        self._sub(p, "Медиа")
        self._para(p, "Включите чекбокс «Скачивать медиа» — фото, видео, документы будут сохранены "
                      "в подпапки внутри директории экспорта.")
        self._sub(p, "Транскрипция")
        self._para(p, "Если включено, голосовые сообщения и видеокружки переводятся в текст. "
                      "Провайдер выбирается в Настройках (локальный Whisper или облачный Deepgram). "
                      "Лимит — 15 минут на сообщение.")
        self._sub(p, "Аналитика")
        self._para(p, "Дополнительно создаёт файлы top_authors.md (топ авторов) и activity.md "
                      "(активность по датам).")
        self._sub(p, "Фильтр по автору")
        self._para(p, "Опционально — экспортировать только сообщения от конкретного пользователя "
                      "(по username или ID).")
        self._sub(p, "Инкрементальный экспорт")
        self._para(p, "При повторном запуске экспортируются только новые сообщения с момента "
                      "предыдущего экспорта (история хранится в ~/.tg_exporter/export_history.json).")

        # 4. Экспорт целой папки
        self._section(p, "4. Экспорт целой папки")
        self._sub(p, "Запуск")
        self._para(p, "На главном экране выберите папку и нажмите «Экспортировать папку». "
                      "Все чаты из папки добавятся в очередь экспорта.")
        self._sub(p, "Режим")
        self._para(p, "По чатам — каждый чат в свою подпапку (как обычный экспорт). "
                      "Один .md на чат — каждый чат в один Markdown без разбивки. "
                      "Один .md на папку — все чаты в один общий Markdown-файл.")
        self._sub(p, "Транскрипция")
        self._para(p, "Чекбокс рядом с кнопкой включает транскрипцию для всех чатов папки.")

        # 5. Настройки приложения
        self._section(p, "5. Настройки приложения")
        self._sub(p, "Транскрипция → Провайдер")
        self._para(p, "Локальный Whisper — работает офлайн, требует загрузки модели при первом "
                      "использовании (от 75 МБ для tiny до 3 ГБ для large). "
                      "Deepgram — облачный, требует API-ключ (получить на console.deepgram.com).")
        self._sub(p, "Модель Whisper")
        self._para(p, "Tiny / Base — быстро, но ниже качество. Medium / Large — медленно, "
                      "но высокое качество. Базовый выбор: Base — оптимальный баланс.")
        self._sub(p, "Язык")
        self._para(p, "«Авто» — определяется автоматически, медленнее. Указание конкретного языка "
                      "ускоряет распознавание.")
        self._sub(p, "Экспорт по умолчанию")
        self._para(p, "Включать ли автора и временные метки в Markdown-файлы по умолчанию. "
                      "Изменения применяются к новым экспортам.")

        # 6. Где находятся файлы
        self._section(p, "6. Где находятся файлы")
        self._sub(p, "Результат экспорта")
        self._para(p, "В выбранной вами папке создаётся подпапка вида «Имя чата_2026-04-15_18-30-00» "
                      "со всеми файлами внутри.")
        self._sub(p, "Конфигурация и логи")
        self._para(p, "Папка ~/.tg_exporter/ — config.json (несекретные настройки), app.log (лог), "
                      "export_history.json (история инкрементальных экспортов).")

        # 7. Полезные советы
        self._section(p, "7. Полезные советы")
        self._sub(p, "Отмена экспорта")
        self._para(p, "Кнопка «Отмена» в окне экспорта останавливает процесс. Уже скачанные файлы "
                      "и записанные сообщения сохраняются.")
        self._sub(p, "Большие чаты")
        self._para(p, "Для каналов с десятками тысяч сообщений рекомендуется указывать период "
                      "(месяц/год) и использовать инкрементальный экспорт при повторных запусках.")
        self._sub(p, "Только одна сессия")
        self._para(p, "Параллельно запустить две копии приложения нельзя (используется один файл "
                      "сессии). Закройте предыдущую копию перед запуском новой.")
