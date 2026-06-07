"""
Tests for core/proxy.py — proxy URL parsing, validation, Telethon conversion.

Покрывает все типы (socks5/socks4/http/mtproto), edge cases и формат,
который ожидает Telethon (строковый proxy_type для PySocks-бэкенда,
connection=ConnectionTcpMTProxy* для MTProto).
"""

import unittest


class TestParseProxy(unittest.TestCase):
    def setUp(self):
        from tg_exporter.core.proxy import parse_proxy, ProxyConfig, ProxyValidationError
        self.parse_proxy = parse_proxy
        self.ProxyConfig = ProxyConfig
        self.ProxyValidationError = ProxyValidationError

    # --- пустые / отсутствие прокси ---

    def test_empty_string_returns_none(self):
        self.assertIsNone(self.parse_proxy(""))

    def test_whitespace_only_returns_none(self):
        self.assertIsNone(self.parse_proxy("   "))

    def test_none_returns_none(self):
        self.assertIsNone(self.parse_proxy(None))

    # --- socks5 ---

    def test_socks5_host_port(self):
        cfg = self.parse_proxy("socks5://1.2.3.4:1080")
        self.assertEqual(cfg.kind, "socks5")
        self.assertEqual(cfg.host, "1.2.3.4")
        self.assertEqual(cfg.port, 1080)
        self.assertIsNone(cfg.username)
        self.assertIsNone(cfg.password)

    def test_socks5_with_credentials(self):
        cfg = self.parse_proxy("socks5://user:pass@proxy.example.com:1080")
        self.assertEqual(cfg.kind, "socks5")
        self.assertEqual(cfg.host, "proxy.example.com")
        self.assertEqual(cfg.port, 1080)
        self.assertEqual(cfg.username, "user")
        self.assertEqual(cfg.password, "pass")

    def test_socks5h_normalized_to_socks5(self):
        # socks5h (remote DNS) — частый алиас, нормализуем в socks5 (rdns всегда True)
        cfg = self.parse_proxy("socks5h://1.2.3.4:1080")
        self.assertEqual(cfg.kind, "socks5")

    # --- socks4 ---

    def test_socks4(self):
        cfg = self.parse_proxy("socks4://1.2.3.4:1080")
        self.assertEqual(cfg.kind, "socks4")
        self.assertEqual(cfg.port, 1080)

    # --- http ---

    def test_http_proxy(self):
        cfg = self.parse_proxy("http://1.2.3.4:8080")
        self.assertEqual(cfg.kind, "http")
        self.assertEqual(cfg.port, 8080)

    def test_https_normalized_to_http(self):
        cfg = self.parse_proxy("https://1.2.3.4:8080")
        self.assertEqual(cfg.kind, "http")

    def test_http_with_credentials(self):
        cfg = self.parse_proxy("http://u:p@1.2.3.4:8080")
        self.assertEqual(cfg.username, "u")
        self.assertEqual(cfg.password, "p")

    # --- mtproto ---

    def test_mtproto_with_secret_query(self):
        cfg = self.parse_proxy("mtproto://proxy.example.com:443?secret=dd00112233445566778899aabbccddeeff")
        self.assertEqual(cfg.kind, "mtproto")
        self.assertEqual(cfg.host, "proxy.example.com")
        self.assertEqual(cfg.port, 443)
        self.assertEqual(cfg.secret, "dd00112233445566778899aabbccddeeff")

    def test_mtproxy_scheme_alias(self):
        # tg://proxy и mtproxy:// — оба алиасы mtproto
        cfg = self.parse_proxy("mtproxy://proxy.example.com:443?secret=00112233445566778899aabbccddeeff")
        self.assertEqual(cfg.kind, "mtproto")
        self.assertEqual(cfg.secret, "00112233445566778899aabbccddeeff")

    # --- ошибки валидации ---

    def test_no_scheme_raises(self):
        with self.assertRaises(self.ProxyValidationError):
            self.parse_proxy("1.2.3.4:1080")

    def test_unknown_scheme_raises(self):
        with self.assertRaises(self.ProxyValidationError):
            self.parse_proxy("ftp://1.2.3.4:1080")

    def test_missing_host_raises(self):
        with self.assertRaises(self.ProxyValidationError):
            self.parse_proxy("socks5://:1080")

    def test_missing_port_raises(self):
        with self.assertRaises(self.ProxyValidationError):
            self.parse_proxy("socks5://1.2.3.4")

    def test_non_numeric_port_raises(self):
        with self.assertRaises(self.ProxyValidationError):
            self.parse_proxy("socks5://1.2.3.4:abc")

    def test_port_out_of_range_raises(self):
        with self.assertRaises(self.ProxyValidationError):
            self.parse_proxy("socks5://1.2.3.4:70000")

    def test_mtproto_without_secret_raises(self):
        with self.assertRaises(self.ProxyValidationError):
            self.parse_proxy("mtproto://1.2.3.4:443")

    def test_mtproto_bad_secret_raises(self):
        # секрет не hex и не валидный base64-формат
        with self.assertRaises(self.ProxyValidationError):
            self.parse_proxy("mtproto://1.2.3.4:443?secret=zzzz")


class TestToTelethon(unittest.TestCase):
    def setUp(self):
        from tg_exporter.core.proxy import parse_proxy
        self.parse_proxy = parse_proxy

    def test_socks5_telethon_kwargs(self):
        kw = self.parse_proxy("socks5://1.2.3.4:1080").to_telethon()
        # connection не задаётся для socks/http
        self.assertIsNone(kw["connection"])
        proxy = kw["proxy"]
        # строковый тип, чтобы не зависеть от python_socks/PySocks бэкенда
        self.assertEqual(proxy["proxy_type"], "socks5")
        self.assertEqual(proxy["addr"], "1.2.3.4")
        self.assertEqual(proxy["port"], 1080)
        self.assertTrue(proxy["rdns"])

    def test_socks5_credentials_passed(self):
        kw = self.parse_proxy("socks5://user:pass@1.2.3.4:1080").to_telethon()
        proxy = kw["proxy"]
        self.assertEqual(proxy["username"], "user")
        self.assertEqual(proxy["password"], "pass")

    def test_socks5_no_credentials_omits_keys(self):
        kw = self.parse_proxy("socks5://1.2.3.4:1080").to_telethon()
        proxy = kw["proxy"]
        # без логина/пароля ключи username/password не должны протекать как None,
        # чтобы не сломать сигнатуру PySocks set_proxy / python_socks Proxy.create
        self.assertNotIn("username", proxy)
        self.assertNotIn("password", proxy)

    def test_http_telethon_kwargs(self):
        kw = self.parse_proxy("http://1.2.3.4:8080").to_telethon()
        self.assertIsNone(kw["connection"])
        self.assertEqual(kw["proxy"]["proxy_type"], "http")

    def test_mtproto_telethon_kwargs(self):
        kw = self.parse_proxy("mtproto://1.2.3.4:443?secret=00112233445566778899aabbccddeeff").to_telethon()
        # MTProto: задаётся connection-класс + proxy-кортеж (host, port, secret)
        self.assertIsNotNone(kw["connection"])
        from telethon.network import ConnectionTcpMTProxyRandomizedIntermediate
        self.assertIs(kw["connection"], ConnectionTcpMTProxyRandomizedIntermediate)
        self.assertEqual(kw["proxy"], ("1.2.3.4", 443, "00112233445566778899aabbccddeeff"))


class TestBuildProxyUrl(unittest.TestCase):
    """build_proxy_url — сборка URL из отдельных полей UI (без Tk)."""

    def setUp(self):
        from tg_exporter.core.proxy import build_proxy_url
        self.build = build_proxy_url

    def test_empty_kind_returns_empty(self):
        self.assertEqual(self.build("", "h", "1080", "", "", ""), "")

    def test_socks5_no_auth(self):
        self.assertEqual(
            self.build("socks5", "1.2.3.4", "1080", "", "", ""),
            "socks5://1.2.3.4:1080",
        )

    def test_socks5_with_auth(self):
        self.assertEqual(
            self.build("socks5", "1.2.3.4", "1080", "user", "pass", ""),
            "socks5://user:pass@1.2.3.4:1080",
        )

    def test_http(self):
        self.assertEqual(
            self.build("http", "1.2.3.4", "8080", "", "", ""),
            "http://1.2.3.4:8080",
        )

    def test_mtproto(self):
        self.assertEqual(
            self.build("mtproto", "1.2.3.4", "443", "", "", "00112233445566778899aabbccddeeff"),
            "mtproto://1.2.3.4:443?secret=00112233445566778899aabbccddeeff",
        )

    def test_special_chars_in_credentials_escaped(self):
        # пароль с @ и : должен экранироваться, чтобы URL парсился обратно корректно
        from tg_exporter.core.proxy import parse_proxy
        url = self.build("socks5", "1.2.3.4", "1080", "u@ser", "p:ss@w", "")
        cfg = parse_proxy(url)
        self.assertEqual(cfg.username, "u@ser")
        self.assertEqual(cfg.password, "p:ss@w")
        self.assertEqual(cfg.host, "1.2.3.4")

    def test_strips_whitespace(self):
        self.assertEqual(
            self.build("socks5", "  1.2.3.4 ", " 1080 ", "", "", ""),
            "socks5://1.2.3.4:1080",
        )

    def test_ipv6_host_wrapped_in_brackets(self):
        # IPv6 host должен оборачиваться в [..], иначе host:port неоднозначен
        url = self.build("socks5", "2001:db8::1", "1080", "", "", "")
        self.assertEqual(url, "socks5://[2001:db8::1]:1080")

    def test_ipv6_already_bracketed_not_double_wrapped(self):
        url = self.build("socks5", "[2001:db8::1]", "1080", "", "", "")
        self.assertEqual(url, "socks5://[2001:db8::1]:1080")

    def test_ipv6_roundtrip(self):
        from tg_exporter.core.proxy import parse_proxy
        url = self.build("socks5", "2001:db8::1", "1080", "user", "pass", "")
        cfg = parse_proxy(url)
        self.assertEqual(cfg.host, "2001:db8::1")
        self.assertEqual(cfg.port, 1080)
        self.assertEqual(cfg.username, "user")
        # и обратно
        self.assertEqual(parse_proxy(cfg.to_url()).host, "2001:db8::1")


class TestRoundTripAndDescribe(unittest.TestCase):
    def setUp(self):
        from tg_exporter.core.proxy import parse_proxy
        self.parse_proxy = parse_proxy

    def test_to_url_roundtrip_socks5(self):
        url = "socks5://user:pass@1.2.3.4:1080"
        self.assertEqual(self.parse_proxy(url).to_url(), url)

    def test_to_url_roundtrip_no_creds(self):
        url = "http://1.2.3.4:8080"
        self.assertEqual(self.parse_proxy(url).to_url(), url)

    def test_to_url_roundtrip_mtproto(self):
        url = "mtproto://1.2.3.4:443?secret=00112233445566778899aabbccddeeff"
        self.assertEqual(self.parse_proxy(url).to_url(), url)

    def test_public_url_strips_password(self):
        # public_url() — для записи в profiles.json: host/port/username видны,
        # пароль вырезан (хранится отдельно в Keyring).
        pub = self.parse_proxy("socks5://user:secretpass@1.2.3.4:1080").public_url()
        self.assertNotIn("secretpass", pub)
        self.assertIn("1.2.3.4", pub)
        self.assertIn("1080", pub)
        self.assertIn("user", pub)
        self.assertEqual(pub, "socks5://user@1.2.3.4:1080")

    def test_public_url_strips_mtproto_secret(self):
        pub = self.parse_proxy(
            "mtproto://1.2.3.4:443?secret=00112233445566778899aabbccddeeff"
        ).public_url()
        self.assertNotIn("00112233445566778899aabbccddeeff", pub)
        self.assertIn("1.2.3.4", pub)
        self.assertIn("443", pub)

    def test_public_url_no_creds_equals_to_url(self):
        cfg = self.parse_proxy("socks5://1.2.3.4:1080")
        self.assertEqual(cfg.public_url(), cfg.to_url())

    def test_describe_hides_password(self):
        desc = self.parse_proxy("socks5://user:secretpass@1.2.3.4:1080").describe()
        self.assertIn("1.2.3.4", desc)
        self.assertIn("1080", desc)
        self.assertNotIn("secretpass", desc)

    def test_describe_hides_mtproto_secret(self):
        desc = self.parse_proxy("mtproto://1.2.3.4:443?secret=00112233445566778899aabbccddeeff").describe()
        self.assertNotIn("00112233445566778899aabbccddeeff", desc)


if __name__ == "__main__":
    unittest.main()
