"""Tests for ExportOrchestrator._count_messages — оценка размера диапазона по ID.

Полноценный тест оркестратора потребовал бы поднимать всю транзакцию (telethon-клиент,
конвертер, экспортеры). Здесь _count_messages вызывается как unbound-метод с моком
клиента и фейковым `self`, потому что метод трогает только task и client.get_messages.
"""

import datetime
import unittest
from unittest.mock import MagicMock

from tg_exporter.core.orchestrator import ExportOrchestrator
from tg_exporter.models.export_task import ExportFormat, ExportTask


UTC = datetime.timezone.utc


class _FakeMsgList(list):
    """list с атрибутом .total — telethon возвращает такое из get_messages(limit=0)."""

    def __init__(self, items, total=None):
        super().__init__(items)
        self.total = total if total is not None else len(items)


def _msg(msg_id: int):
    m = MagicMock()
    m.id = msg_id
    return m


def _task(*, date_from=None, date_to=None, topic_id=None) -> ExportTask:
    return ExportTask(
        chat_id=1,
        chat_name="x",
        output_path="/tmp",
        format=ExportFormat.JSON,
        date_from=date_from,
        date_to=date_to,
        topic_id=topic_id,
    )


class TestCountMessagesDateToOnly(unittest.TestCase):
    """Самый интересный случай — раньше first_id=1 переоценивал прогресс."""

    def test_uses_oldest_message_id_as_lower_bound(self):
        # Чат: реальные сообщения id=10000..15000, до date_to укладывается id=12000.
        # Старая логика (first_id=1) дала бы 12000 — переоценка в 6 раз.
        # Новая: first_id из get_messages(limit=1, reverse=True) → 10000.
        client = MagicMock()
        date_to = datetime.datetime(2025, 5, 1, tzinfo=UTC)

        def fake_get_messages(_dialog, **kwargs):
            # «Самое старое сообщение чата» — limit=1 + reverse=True, без offset_date.
            if kwargs.get("limit") == 1 and kwargs.get("reverse") and "offset_date" not in kwargs:
                return _FakeMsgList([_msg(10000)])
            # Правая граница: limit=1 c offset_date=date_to+1d → последнее перед date_to.
            if kwargs.get("limit") == 1 and "offset_date" in kwargs and not kwargs.get("reverse"):
                return _FakeMsgList([_msg(12000)])
            raise AssertionError(f"unexpected get_messages kwargs: {kwargs}")

        client.get_messages.side_effect = fake_get_messages
        result = ExportOrchestrator._count_messages(
            MagicMock(), client, dialog="d", task=_task(date_to=date_to),
        )
        self.assertEqual(result, 12000 - 10000 + 1)

    def test_empty_chat_returns_zero(self):
        # Когда get_messages(limit=1, reverse=True) возвращает [] — чат пуст.
        client = MagicMock()
        client.get_messages.return_value = _FakeMsgList([])
        result = ExportOrchestrator._count_messages(
            MagicMock(), client, dialog="d",
            task=_task(date_to=datetime.datetime(2025, 5, 1, tzinfo=UTC)),
        )
        self.assertEqual(result, 0)


class TestCountMessagesDateFromAndTo(unittest.TestCase):
    """Двусторонний диапазон — оценка по разнице ID граничных сообщений."""

    def test_returns_id_difference(self):
        client = MagicMock()
        date_from = datetime.datetime(2025, 4, 1, tzinfo=UTC)
        date_to = datetime.datetime(2025, 5, 1, tzinfo=UTC)

        def fake_get_messages(_dialog, **kwargs):
            if kwargs.get("reverse") and kwargs.get("offset_date") == date_from:
                return _FakeMsgList([_msg(11000)])  # первое после date_from
            if "offset_date" in kwargs and not kwargs.get("reverse"):
                return _FakeMsgList([_msg(13000)])  # последнее до date_to+1d
            raise AssertionError(f"unexpected get_messages kwargs: {kwargs}")

        client.get_messages.side_effect = fake_get_messages
        result = ExportOrchestrator._count_messages(
            MagicMock(), client, dialog="d",
            task=_task(date_from=date_from, date_to=date_to),
        )
        self.assertEqual(result, 13000 - 11000 + 1)

    def test_empty_window_returns_zero(self):
        # Левый запрос вернул [] — в окне сообщений нет.
        client = MagicMock()
        client.get_messages.return_value = _FakeMsgList([])
        result = ExportOrchestrator._count_messages(
            MagicMock(), client, dialog="d",
            task=_task(date_from=datetime.datetime(2025, 4, 1, tzinfo=UTC)),
        )
        self.assertEqual(result, 0)


class TestCountMessagesEdgeCases(unittest.TestCase):

    def test_no_filters_uses_total_from_get_history(self):
        # Без фильтров — total из getattr(get_messages(limit=0), "total").
        client = MagicMock()
        client.get_messages.return_value = _FakeMsgList([], total=22984)
        result = ExportOrchestrator._count_messages(
            MagicMock(), client, dialog="d", task=_task(),
        )
        self.assertEqual(result, 22984)

    def test_topic_with_dates_returns_none(self):
        # Топики + даты: ID не последовательны, оценка не применима.
        client = MagicMock()
        result = ExportOrchestrator._count_messages(
            MagicMock(), client, dialog="d",
            task=_task(
                date_from=datetime.datetime(2025, 4, 1, tzinfo=UTC),
                topic_id=42,
            ),
        )
        self.assertIsNone(result)

    def test_last_id_below_first_returns_zero(self):
        # Гонка: к моменту правого запроса всё уже устарело.
        client = MagicMock()

        def fake_get_messages(_dialog, **kwargs):
            if kwargs.get("reverse") and "offset_date" in kwargs:
                return _FakeMsgList([_msg(15000)])  # left
            return _FakeMsgList([_msg(10000)])      # right < left

        client.get_messages.side_effect = fake_get_messages
        result = ExportOrchestrator._count_messages(
            MagicMock(), client, dialog="d",
            task=_task(
                date_from=datetime.datetime(2025, 4, 1, tzinfo=UTC),
                date_to=datetime.datetime(2025, 5, 1, tzinfo=UTC),
            ),
        )
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
