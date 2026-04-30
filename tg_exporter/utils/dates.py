"""Парсинг пользовательских дат в aware-UTC."""

from __future__ import annotations

import datetime
from typing import Optional


def parse_local_date(raw: str) -> Optional[datetime.datetime]:
    """Парсит ISO-строку как локальное время хоста и возвращает aware-UTC.

    - Naive-строка ("2025-01-15", "2025-01-15 10:00") интерпретируется в
      локальной таймзоне и приводится к UTC через astimezone.
    - Aware-строка (с явным offset или Z) уже знает свою таймзону —
      приводим к UTC.
    - None при пустой строке или невалидном формате.
    """
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.astimezone(datetime.timezone.utc)
