"""Tests for export cancellation — частичные файлы должны оставаться валидными.

Баг: при отмене (CancelledError из token.raise_if_cancelled() в середине цикла)
JsonExporter.close() не вызывался → result.json оставался с оборванным массивом
"messages": [ ... без закрывающих ]} → невалидный JSON.

Тест прогоняет реальный _do_run с реальными экспортёрами, мокая только telethon-клиент
(iter_messages) и _count_messages. Отмена срабатывает после N записанных сообщений.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from tg_exporter.core.orchestrator import ExportOrchestrator
from tg_exporter.models.config import AppConfig
from tg_exporter.models.export_task import ExportFormat, ExportTask
from tg_exporter.models.message import ExportMessage
from tg_exporter.utils.cancellation import CancellationToken, CancelledError


def _tl_msg(msg_id: int):
    """Минимальный telethon-подобный message-объект (id для max_msg_id)."""
    m = MagicMock()
    m.id = msg_id
    m.out = False
    return m


def _export_msg(msg) -> ExportMessage:
    """Подмена message_to_export — отдаёт реальный сериализуемый ExportMessage."""
    return ExportMessage(id=msg.id, type="message", date="2026-01-01T00:00:00+00:00",
                         text=f"msg {msg.id}")


class _CancelAfter:
    """iter_messages-генератор: отменяет токен после `after` сообщений."""

    def __init__(self, messages, token, after):
        self._messages = messages
        self._token = token
        self._after = after

    def __call__(self, dialog, **kwargs):
        for i, m in enumerate(self._messages):
            if i == self._after:
                self._token.cancel()
            yield m


class TestExportCancelLeavesValidJson(unittest.TestCase):
    def _make_orchestrator(self, client):
        orch = ExportOrchestrator.__new__(ExportOrchestrator)
        orch._client = client
        orch._config = AppConfig()
        orch._deepgram_key = None
        from tg_exporter.core.orchestrator import MediaDownloader
        orch._media = MediaDownloader()
        # _count_messages не должен лезть в сеть — отдаём фикс.
        orch._count_messages = lambda c, dialog, task: 100
        return orch

    def test_cancel_midway_json_is_valid(self):
        token = CancellationToken()
        messages = [_tl_msg(1000 + i) for i in range(10)]

        client = MagicMock()
        conn = MagicMock()
        conn.iter_messages = _CancelAfter(messages, token, after=4)
        client.ensure_connected.return_value = conn

        orch = self._make_orchestrator(client)

        with tempfile.TemporaryDirectory() as tmp:
            task = ExportTask(
                chat_id=1, chat_name="Chat", output_path=tmp,
                format=ExportFormat.JSON, download_media=False,
            )
            dialog = MagicMock()
            dialog.name = "Chat"
            progress = MagicMock()

            with patch("tg_exporter.core.orchestrator.message_to_export", _export_msg), \
                    self.assertRaises(CancelledError):
                orch._do_run(dialog, task, token, progress, send=lambda *a, **k: None)

            # Найти result.json в созданной подпапке экспорта.
            found = None
            for root, _dirs, files in os.walk(tmp):
                if "result.json" in files:
                    found = os.path.join(root, "result.json")
                    break
            self.assertIsNotNone(found, "result.json не создан")

            # ГЛАВНОЕ: файл должен быть валидным JSON, несмотря на отмену.
            with open(found, encoding="utf-8") as f:
                data = json.load(f)  # бросит JSONDecodeError если оборван
            self.assertEqual(data["name"], "Chat")
            self.assertIsInstance(data["messages"], list)
            # Записаны сообщения до отмены (4), не больше.
            self.assertLessEqual(len(data["messages"]), 5)
            self.assertGreater(len(data["messages"]), 0)


if __name__ == "__main__":
    unittest.main()
