"""Tests for utils/logger.redact — маскирование секретов в логах."""

from __future__ import annotations

import unittest


class TestRedact(unittest.TestCase):
    def setUp(self):
        from tg_exporter.utils.logger import redact
        self.redact = redact

    # --- существующее поведение не должно сломаться ---

    def test_api_hash_masked(self):
        self.assertNotIn("deadbeef", self.redact("api_hash=deadbeef0123"))

    def test_phone_masked(self):
        self.assertNotIn("+79991112233", self.redact("phone +79991112233 ok"))

    # --- прокси-креды (новое) ---

    def test_proxy_url_password_masked(self):
        out = self.redact("client: используется прокси socks5://user:s3cr3t@1.2.3.4:1080")
        self.assertNotIn("s3cr3t", out)

    def test_proxy_url_keeps_host(self):
        # host/port не секрет — оставляем для диагностики, прячем только user:pass
        out = self.redact("socks5://user:s3cr3t@1.2.3.4:1080")
        self.assertNotIn("s3cr3t", out)
        self.assertNotIn("user", out)

    def test_http_proxy_password_masked(self):
        out = self.redact("http://admin:p@ssw0rd@proxy.example.com:8080")
        self.assertNotIn("p@ssw0rd", out)

    def test_no_false_positive_on_plain_url(self):
        # URL без user:pass@ не должен пострадать
        out = self.redact("socks5://1.2.3.4:1080")
        self.assertIn("1.2.3.4", out)


if __name__ == "__main__":
    unittest.main()
