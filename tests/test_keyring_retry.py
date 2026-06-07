"""
Tests for keyring_set_with_retry — устойчивость записи в Keyring.

macOS Keychain периодически бросает (-25244 Unknown Error); backend делает
set = delete+add, поэтому сбой на add может СТЕРЕТЬ сессию. Retry + read-back
проверка закрывают это окно.
"""

from __future__ import annotations

import unittest
from unittest import mock


class _FlakyKeyring:
    """Падает N раз, потом пишет. Хранит значения для read-back."""
    def __init__(self, fail_times=0, mismatch_times=0):
        self.store = {}
        self._fail = fail_times
        self._mismatch = mismatch_times
        self.set_calls = 0

    def set_password(self, service, key, value):
        self.set_calls += 1
        if self._fail > 0:
            self._fail -= 1
            raise RuntimeError("(-25244, 'Unknown Error')")
        if self._mismatch > 0:
            self._mismatch -= 1
            # имитируем delete-then-failed-add: значение не легло
            self.store.pop((service, key), None)
            return
        self.store[(service, key)] = value

    def get_password(self, service, key):
        return self.store.get((service, key))


class TestKeyringRetry(unittest.TestCase):
    def _run(self, fake, **kw):
        import sys
        from tg_exporter.core import credentials
        old = sys.modules.get("keyring")
        sys.modules["keyring"] = fake  # уважается локальным import внутри функции
        try:
            with mock.patch("time.sleep", lambda *_: None):
                credentials.keyring_set_with_retry("tg_exporter", "k", "v", **kw)
        finally:
            if old is not None:
                sys.modules["keyring"] = old
            else:
                sys.modules.pop("keyring", None)

    def test_succeeds_first_try(self):
        fake = _FlakyKeyring()
        self._run(fake)
        self.assertEqual(fake.get_password("tg_exporter", "k"), "v")
        self.assertEqual(fake.set_calls, 1)

    def test_retries_on_error_then_succeeds(self):
        fake = _FlakyKeyring(fail_times=2)
        self._run(fake, attempts=3)
        self.assertEqual(fake.get_password("tg_exporter", "k"), "v")
        self.assertEqual(fake.set_calls, 3)

    def test_retries_on_readback_mismatch(self):
        # set «прошёл» но значение не легло (half-write) → read-back ловит, retry
        fake = _FlakyKeyring(mismatch_times=1)
        self._run(fake, attempts=3)
        self.assertEqual(fake.get_password("tg_exporter", "k"), "v")
        self.assertGreaterEqual(fake.set_calls, 2)

    def test_raises_after_all_attempts(self):
        fake = _FlakyKeyring(fail_times=10)
        with self.assertRaises(Exception):
            self._run(fake, attempts=3)


if __name__ == "__main__":
    unittest.main()
