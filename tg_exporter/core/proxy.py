"""
Парсинг и валидация прокси для Telegram-аккаунтов.

Прокси задаётся одной URL-строкой и хранится в `Profile.proxy`. Поддержаны:
  - socks5://[user:pass@]host:port   (socks5h:// — алиас, rdns всегда включён)
  - socks4://host:port
  - http(s)://[user:pass@]host:port
  - mtproto://host:port?secret=HEX   (mtproxy://, tg://proxy — алиасы)

Этот модуль НЕ импортирует Telethon на верхнем уровне и держит знание о
формате прокси в одном месте: UI (которому нельзя импортировать Telethon —
см. CLAUDE.md §10.2) работает только со строкой/полями, а `to_telethon()`
возвращает готовые kwargs для `TelegramClient(**kwargs)`.

Тип прокси отдаётся СТРОКОЙ ("socks5"/"socks4"/"http") — Telethon сам
сопоставит её с нужным бэкендом (python_socks или PySocks), поэтому здесь не
нужно импортировать ни тот, ни другой. Для MTProto задаётся connection-класс
ConnectionTcpMTProxyRandomizedIntermediate + кортеж (host, port, secret).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlsplit, parse_qs, quote, unquote


class ProxyValidationError(ValueError):
    """Строка прокси задана, но синтаксически/семантически некорректна."""


# scheme в URL → канонический kind
_SCHEME_MAP = {
    "socks5": "socks5",
    "socks5h": "socks5",
    "socks4": "socks4",
    "socks4a": "socks4",
    "http": "http",
    "https": "http",
    "mtproto": "mtproto",
    "mtproxy": "mtproto",
    "tg": "mtproto",
}

_SOCKS_HTTP = {"socks5", "socks4", "http"}


@dataclass
class ProxyConfig:
    kind: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    secret: Optional[str] = None  # только для mtproto

    def to_telethon(self) -> dict:
        """
        Возвращает kwargs для TelegramClient: {"proxy": ..., "connection": ...}.
        connection=None для socks/http (берётся дефолтный ConnectionTcpFull).
        """
        if self.kind in _SOCKS_HTTP:
            proxy: dict = {
                "proxy_type": self.kind,
                "addr": self.host,
                "port": self.port,
                "rdns": True,
            }
            # Ключи username/password добавляем только если заданы — иначе
            # None протёк бы в сигнатуру PySocks/python_socks как валидное значение.
            if self.username:
                proxy["username"] = self.username
            if self.password:
                proxy["password"] = self.password
            return {"proxy": proxy, "connection": None}

        # mtproto
        from telethon.network import ConnectionTcpMTProxyRandomizedIntermediate
        return {
            "proxy": (self.host, self.port, self.secret),
            "connection": ConnectionTcpMTProxyRandomizedIntermediate,
        }

    def to_url(self) -> str:
        """Обратная сериализация в строку (для предзаполнения UI)."""
        return build_proxy_url(
            self.kind, self.host, str(self.port),
            self.username or "", self.password or "", self.secret or "",
        )

    def public_url(self) -> str:
        """
        URL без секретов (пароль/MTProto-секрет вырезаны) — для записи в
        profiles.json. host/port/username несекретны и остаются для UI.
        Полный URL с секретом хранится отдельно в Keyring.
        """
        if self.kind == "mtproto":
            return f"mtproto://{self.host}:{self.port}"
        return build_proxy_url(self.kind, self.host, str(self.port), self.username or "", "", "")

    def describe(self) -> str:
        """Человекочитаемое описание БЕЗ пароля/секрета (для UI и логов)."""
        if self.kind == "mtproto":
            return f"MTProto {self.host}:{self.port}"
        label = {"socks5": "SOCKS5", "socks4": "SOCKS4", "http": "HTTP"}.get(self.kind, self.kind)
        auth = f" (логин {self.username})" if self.username else ""
        return f"{label} {self.host}:{self.port}{auth}"


def _looks_like_hex(s: str) -> bool:
    try:
        bytes.fromhex(s)
        return True
    except ValueError:
        return False


def _validate_mtproto_secret(secret: str) -> str:
    """
    MTProto-секрет: hex (16 байт, опц. dd+16=17 байт) либо base64.

    Особенность Telethon 1.43 (`normalize_secret` в tcpmtproxy.py): он срезает
    ЛЮБОЙ hex-секрет, начинающийся на строку "ee"/"dd", как 1-байтовый префикс.
    Для ровно 16-байтного (32 hex) секрета, первый байт которого 0xEE или 0xDD,
    это даёт 15 байт → telethon падает с «secret must be 16 bytes». Такие
    секреты (часто fake-TLS `ee...`) отбраковываем заранее с понятным текстом,
    а не отдаём в telethon на криптическую ошибку при входе.
    """
    import base64

    raw = secret.strip()

    if _looks_like_hex(raw) and len(raw) % 2 == 0:
        nbytes = len(raw) // 2
        prefix = raw[:2].lower()
        # Ровно 16 байт hex, начинается на ee/dd: telethon в hex-форме сломается
        # (срежет ee/dd как строковый префикс → 15 байт → ValueError). НО тот же
        # секрет в base64 telethon принимает корректно. Конвертируем сами, чтобы
        # пользователь вставлял hex из tg://proxy ссылки как есть.
        if nbytes == 16 and prefix in ("ee", "dd"):
            return base64.b64encode(bytes.fromhex(raw)).decode().rstrip("=")
        # Валидные hex: 16 байт без ee/dd-префикса, либо 17 байт (dd + 16),
        # либо длиннее (fake-TLS с доменом — telethon обрежет до 16).
        if nbytes >= 16:
            return raw
        raise ProxyValidationError(
            "Слишком короткий секрет MTProto: нужно минимум 16 байт (32 hex-символа)."
        )

    # base64-форма (telegram ссылки иногда дают base64url)
    try:
        pad = "=" * (-len(raw) % 4)
        decoded = base64.urlsafe_b64decode(raw + pad)
        if len(decoded) >= 16:
            return raw
    except (ValueError, TypeError):  # невалидный base64 → секрет некорректен
        pass
    raise ProxyValidationError(
        "Некорректный секрет MTProto: ожидается hex (16 байт / 32 символа) или base64."
    )


def parse_proxy(raw: Optional[str]) -> Optional[ProxyConfig]:
    """
    Парсит строку прокси в ProxyConfig.

    Пустая строка / None → None (прокси не задан, это валидно).
    Некорректная строка → ProxyValidationError.
    """
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None

    parts = urlsplit(raw)
    scheme = parts.scheme.lower()
    if not scheme:
        raise ProxyValidationError(
            "Не указан тип прокси. Пример: socks5://1.2.3.4:1080"
        )
    kind = _SCHEME_MAP.get(scheme)
    if kind is None:
        raise ProxyValidationError(
            f"Неизвестный тип прокси «{scheme}». "
            f"Поддерживаются socks5, socks4, http, mtproto."
        )

    host = parts.hostname
    if not host:
        raise ProxyValidationError("Не указан адрес (host) прокси.")

    try:
        port = parts.port
    except ValueError:
        raise ProxyValidationError("Порт прокси должен быть числом.")
    if port is None:
        raise ProxyValidationError("Не указан порт прокси.")
    if not (1 <= port <= 65535):
        raise ProxyValidationError("Порт прокси должен быть в диапазоне 1–65535.")

    if kind == "mtproto":
        qs = parse_qs(parts.query)
        secret_vals = qs.get("secret") or qs.get("s")
        if not secret_vals or not secret_vals[0]:
            raise ProxyValidationError(
                "Для MTProto нужен секрет: mtproto://host:port?secret=…"
            )
        secret = _validate_mtproto_secret(secret_vals[0].strip())
        return ProxyConfig(kind="mtproto", host=host, port=port, secret=secret)

    username = unquote(parts.username) if parts.username else None
    password = unquote(parts.password) if parts.password else None
    return ProxyConfig(
        kind=kind, host=host, port=port, username=username, password=password
    )


def _bracket_ipv6(host: str) -> str:
    """Оборачивает IPv6-адрес в [..] для корректного host:port в URL."""
    if not host or host.startswith("["):
        return host
    # IPv6 содержит ≥2 двоеточий; hostname/IPv4 — ни одного.
    if host.count(":") >= 2:
        return f"[{host}]"
    return host


def build_proxy_url(
    kind: str, host: str, port: str,
    username: str = "", password: str = "", secret: str = "",
) -> str:
    """
    Собирает URL-строку прокси из отдельных полей (для UI). "" kind → "".

    Логин/пароль url-экранируются, чтобы строка корректно парсилась обратно
    даже если в них есть @ или :. Не валидирует — это делает parse_proxy().
    """
    kind = (kind or "").strip()
    if not kind:
        return ""
    host = _bracket_ipv6((host or "").strip())
    port = (port or "").strip()
    if kind == "mtproto":
        # Секрет может быть base64 с '+' и '/'. В URL query '+' декодируется как
        # пробел, поэтому percent-кодируем секрет целиком (quote с safe="").
        secret_enc = quote((secret or "").strip(), safe="")
        return f"mtproto://{host}:{port}?secret={secret_enc}"
    auth = ""
    username = (username or "").strip()
    password = (password or "").strip()
    if username:
        auth = quote(username, safe="")
        if password:
            auth += ":" + quote(password, safe="")
        auth += "@"
    return f"{kind}://{auth}{host}:{port}"
