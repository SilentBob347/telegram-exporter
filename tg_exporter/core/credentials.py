"""
CredentialsManager — единственное место где хранятся секреты приложения.

Правила:
- api_hash и session string хранятся ТОЛЬКО в системном Keyring.
- deepgram_api_key тоже хранится в Keyring.
- НЕТ fallback к plaintext файлу — если Keyring недоступен, кидаем понятное исключение.
- api_id НЕ является секретом (это публичный идентификатор приложения).
"""

from __future__ import annotations

from typing import Optional

try:
    import keyring
    import keyring.errors
    _KEYRING_AVAILABLE = True
except ImportError:
    keyring = None  # type: ignore[assignment]
    _KEYRING_AVAILABLE = False


_SERVICE_NAME = "tg_exporter"


def keyring_set_with_retry(service: str, key: str, value: str, attempts: int = 3) -> None:
    """
    Запись в Keyring с retry + read-back проверкой.

    macOS Keychain периодически бросает (-25244 Unknown Error). Его backend
    делает set = delete + add, поэтому сбой на add может СТЕРЕТЬ значение
    (удалил старое, не записал новое). Read-back подтверждает, что значение
    реально легло, прежде чем считать его сохранённым. Бросает последнее
    исключение, если все попытки провалились.
    """
    import time
    import keyring as _kr  # локальный импорт: уважает подмену sys.modules в тестах
    last_exc = None
    for i in range(attempts):
        try:
            _kr.set_password(service, key, value)
            if _kr.get_password(service, key) == value:
                return
            last_exc = RuntimeError("keyring set verification mismatch")
        except Exception as exc:  # incl. keyring.errors.PasswordSetError (-25244)
            last_exc = exc
        time.sleep(0.15 * (i + 1))
    raise last_exc if last_exc else RuntimeError("keyring set failed")


class KeyringUnavailableError(RuntimeError):
    """Keyring не установлен или недоступен в текущей среде."""


class CredentialsManager:
    """
    Thread-safe менеджер секретов через системный Keyring.

    Ключи в Keyring:
        tg_exporter / {api_id}:api_hash  → api_hash
        tg_exporter / {api_id}:session   → session string
        tg_exporter / deepgram           → Deepgram API key
    """

    # ---- Проверка доступности ----

    @staticmethod
    def is_available() -> bool:
        """True если Keyring установлен и работает."""
        if not _KEYRING_AVAILABLE:
            return False
        try:
            keyring.get_password(_SERVICE_NAME, "__probe__")
            return True
        except Exception:
            return False

    @staticmethod
    def _require_keyring() -> None:
        if not _KEYRING_AVAILABLE:
            raise KeyringUnavailableError(
                "Пакет keyring не установлен. "
                "Установите его: pip install keyring"
            )
        try:
            keyring.get_password(_SERVICE_NAME, "__probe__")
        except Exception as exc:
            raise KeyringUnavailableError(
                f"Системный Keyring недоступен: {exc}"
            ) from exc

    # ---- Вспомогательные ----

    @staticmethod
    def _api_hash_key(api_id: str) -> str:
        return f"{api_id}:api_hash"

    @staticmethod
    def _session_key(api_id: str) -> str:
        return f"{api_id}:session"

    _DEEPGRAM_KEY = "deepgram_api_key"

    # ---- API Hash ----

    def save_api_hash(self, api_id: str, api_hash: str) -> None:
        """Сохраняет api_hash в Keyring. Кидает KeyringUnavailableError если недоступен."""
        self._require_keyring()
        keyring_set_with_retry(_SERVICE_NAME, self._api_hash_key(api_id), api_hash)

    def load_api_hash(self, api_id: str) -> Optional[str]:
        """Загружает api_hash из Keyring. Возвращает None если не найден."""
        if not _KEYRING_AVAILABLE:
            return None
        try:
            return keyring.get_password(_SERVICE_NAME, self._api_hash_key(api_id)) or None
        except Exception:
            return None

    def delete_api_hash(self, api_id: str) -> None:
        if not _KEYRING_AVAILABLE:
            return
        try:
            if keyring.get_password(_SERVICE_NAME, self._api_hash_key(api_id)):
                keyring.delete_password(_SERVICE_NAME, self._api_hash_key(api_id))
        except Exception:
            pass

    # ---- Session ----

    def save_session(self, api_id: str, session_str: str) -> None:
        """Сохраняет session string в Keyring."""
        self._require_keyring()
        keyring_set_with_retry(_SERVICE_NAME, self._session_key(api_id), session_str)

    def load_session(self, api_id: str) -> Optional[str]:
        """Загружает session string из Keyring. Возвращает None если не найден."""
        if not _KEYRING_AVAILABLE:
            return None
        try:
            return keyring.get_password(_SERVICE_NAME, self._session_key(api_id)) or None
        except Exception:
            return None

    def delete_session(self, api_id: str) -> None:
        if not _KEYRING_AVAILABLE:
            return
        try:
            if keyring.get_password(_SERVICE_NAME, self._session_key(api_id)):
                keyring.delete_password(_SERVICE_NAME, self._session_key(api_id))
        except Exception:
            pass

    # ---- Deepgram ----

    def save_deepgram_key(self, api_key: str) -> None:
        self._require_keyring()
        keyring.set_password(_SERVICE_NAME, self._DEEPGRAM_KEY, api_key)

    def load_deepgram_key(self) -> Optional[str]:
        if not _KEYRING_AVAILABLE:
            return None
        try:
            return keyring.get_password(_SERVICE_NAME, self._DEEPGRAM_KEY) or None
        except Exception:
            return None

    def delete_deepgram_key(self) -> None:
        if not _KEYRING_AVAILABLE:
            return
        try:
            if keyring.get_password(_SERVICE_NAME, self._DEEPGRAM_KEY):
                keyring.delete_password(_SERVICE_NAME, self._DEEPGRAM_KEY)
        except Exception:
            pass

    # ---- Полная очистка ----

    def delete_all(self, api_id: str) -> None:
        """Удаляет все секреты для данного api_id."""
        self.delete_api_hash(api_id)
        self.delete_session(api_id)

    # ---- Миграция из старого формата ----

    def migrate_from_plaintext(
        self,
        api_id: str,
        api_hash: Optional[str],
        session_str: Optional[str],
    ) -> bool:
        """
        Переносит секреты из старого config.json в Keyring.
        Возвращает True если миграция прошла успешно.
        """
        if not self.is_available():
            return False
        try:
            if api_hash and not self.load_api_hash(api_id):
                self.save_api_hash(api_id, api_hash)
            if session_str and not self.load_session(api_id):
                self.save_session(api_id, session_str)
            return True
        except Exception:
            return False
