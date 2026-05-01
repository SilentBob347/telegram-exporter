"""Парсинг пользовательских дат и сведение выбора периода к (date_from, date_to)."""

from __future__ import annotations

import datetime
from typing import Optional, Tuple


DateRange = Tuple[Optional[datetime.datetime], Optional[datetime.datetime]]


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


def resolve_period_to_range(
    period_days: int,
    custom_from: Optional[datetime.datetime],
    custom_to: Optional[datetime.datetime],
    *,
    now: Optional[datetime.datetime] = None,
) -> DateRange:
    """Сводит выбор периода в шапке к паре (date_from, date_to).

    Приоритет: «N дней назад» > «свой период» > «все время».

    - period_days > 0 → (now - N дней, None); custom_* игнорируются.
    - period_days <= 0 и хотя бы одна custom-дата → (custom_from, custom_to).
    - всё пусто → (None, None).

    `now` инжектится в тестах, иначе берётся текущий UTC.
    """
    if period_days > 0:
        anchor = now if now is not None else datetime.datetime.now(datetime.timezone.utc)
        return (anchor - datetime.timedelta(days=period_days), None)
    if custom_from is not None or custom_to is not None:
        return (custom_from, custom_to)
    return (None, None)
