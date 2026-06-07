"""
Tests for AuthService QR-login methods (start_qr / poll_qr).

Telethon QRLogin замокан — сеть не трогаем. Проверяем ветки poll_qr:
SUCCESS / WAITING / PASSWORD_REQUIRED / EXPIRED.
"""

from __future__ import annotations

import datetime
import unittest
from unittest import mock


class _FakeQR:
    """
    Замена telethon QRLogin. ВАЖНО: wait/recreate — КОРУТИНЫ (async), как в
    реальном telethon (они НЕ синкифицированы). Это ловит баг, когда poll_qr
    забывает run_until_complete и получает всегда-truthy корутину.
    """
    def __init__(self, url="tg://login?token=abc", expires=None, wait_behavior=None):
        self.url = url
        self.expires = expires
        self._wait_behavior = wait_behavior  # значение-результат или Exception
        self.recreated = False

    async def wait(self, timeout=None):
        b = self._wait_behavior
        if isinstance(b, BaseException):
            raise b
        return b  # True (вошёл) / False / None

    async def recreate(self):
        self.recreated = True
        self.url = "tg://login?token=NEW"


class _FakeLoop:
    """Минимальный loop: реально выполняет корутину (как client.loop)."""
    def run_until_complete(self, coro):
        import asyncio
        return asyncio.new_event_loop().run_until_complete(coro)


class _FakeClient:
    def __init__(self, qr):
        self._qr = qr
        self.loop = _FakeLoop()

    def qr_login(self):
        return self._qr


class _FakeClientMgr:
    def __init__(self, client):
        self._client = client

    def ensure_connected(self):
        return self._client

    def get_client(self):
        return self._client

    def save_session(self):
        pass


def _future(seconds=60):
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)


def _past(seconds=60):
    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=seconds)


class TestAuthQR(unittest.TestCase):
    def setUp(self):
        from tg_exporter.core.auth import AuthService, AuthStep
        self.AuthService = AuthService
        self.AuthStep = AuthStep

    def _service(self, qr):
        return self.AuthService(_FakeClientMgr(_FakeClient(qr)))

    def test_start_qr_returns_url(self):
        qr = _FakeQR(url="tg://login?token=XYZ", expires=_future())
        svc = self._service(qr)
        url = svc.start_qr()
        self.assertEqual(url, "tg://login?token=XYZ")

    def test_recreate_qr_awaits_and_returns_new_url(self):
        # recreate() должен реально выполниться (корутина), url обновиться.
        qr = _FakeQR(url="tg://login?token=OLD", expires=_future())
        svc = self._service(qr)
        svc.start_qr()
        new_url = svc.recreate_qr()
        self.assertTrue(qr.recreated, "recreate() не была выполнена")
        self.assertEqual(new_url, "tg://login?token=NEW")

    def test_poll_success(self):
        qr = _FakeQR(expires=_future(), wait_behavior=True)  # вошёл
        svc = self._service(qr)
        svc.start_qr()
        res = svc.poll_qr(timeout=1)
        self.assertEqual(res.step, self.AuthStep.SUCCESS)

    def test_poll_waiting(self):
        # wait вернул без логина, токен ещё жив → WAITING
        qr = _FakeQR(expires=_future(), wait_behavior=False)
        svc = self._service(qr)
        svc.start_qr()
        res = svc.poll_qr(timeout=1)
        self.assertEqual(res.step, self.AuthStep.WAITING)

    def test_poll_expired(self):
        # wait вернул без логина, токен протух → EXPIRED
        qr = _FakeQR(expires=_past(), wait_behavior=False)
        svc = self._service(qr)
        svc.start_qr()
        res = svc.poll_qr(timeout=1)
        self.assertEqual(res.step, self.AuthStep.EXPIRED)

    def test_poll_2fa(self):
        from telethon.errors import SessionPasswordNeededError
        # SessionPasswordNeededError требует аргумент request — передаём заглушку.
        exc = SessionPasswordNeededError(request=None)
        qr = _FakeQR(expires=_future(), wait_behavior=exc)
        svc = self._service(qr)
        svc.start_qr()
        res = svc.poll_qr(timeout=1)
        self.assertEqual(res.step, self.AuthStep.PASSWORD_REQUIRED)

    def test_poll_timeout_treated_as_waiting(self):
        # wait бросил asyncio.TimeoutError (никто не отсканировал за timeout) —
        # это нормальный «ждём дальше», токен жив → WAITING.
        import asyncio
        qr = _FakeQR(expires=_future(), wait_behavior=asyncio.TimeoutError())
        svc = self._service(qr)
        svc.start_qr()
        res = svc.poll_qr(timeout=1)
        self.assertEqual(res.step, self.AuthStep.WAITING)

    def test_poll_without_start_errors(self):
        qr = _FakeQR()
        svc = self._service(qr)
        res = svc.poll_qr(timeout=1)
        self.assertEqual(res.step, self.AuthStep.ERROR)


if __name__ == "__main__":
    unittest.main()
