"""Tests for tg_exporter.utils.dates — parse_local_date, resolve_period_to_range."""

import datetime
import unittest

from tg_exporter.utils.dates import parse_local_date, resolve_period_to_range


UTC = datetime.timezone.utc


class TestParseLocalDate(unittest.TestCase):

    def test_empty_returns_none(self):
        self.assertIsNone(parse_local_date(""))
        self.assertIsNone(parse_local_date("   "))

    def test_invalid_returns_none(self):
        self.assertIsNone(parse_local_date("not a date"))
        self.assertIsNone(parse_local_date("2025-13-99"))
        self.assertIsNone(parse_local_date("yesterday"))

    def test_naive_date_returns_aware_utc(self):
        # Конкретное UTC-значение зависит от локальной TZ runner'а — не утверждаем
        # его, проверяем только инвариант: tzinfo == UTC, дата приблизительно
        # совпадает с введённой (±1 день из-за смены TZ).
        result = parse_local_date("2025-01-15")
        self.assertIsNotNone(result)
        self.assertEqual(result.tzinfo, UTC)
        self.assertIn(result.date(), {
            datetime.date(2025, 1, 14),
            datetime.date(2025, 1, 15),
            datetime.date(2025, 1, 16),
        })

    def test_aware_with_offset_normalized_to_utc(self):
        # 10:00 в +03:00 == 07:00 UTC, независимо от TZ хоста.
        result = parse_local_date("2025-01-15T10:00:00+03:00")
        self.assertEqual(
            result, datetime.datetime(2025, 1, 15, 7, 0, tzinfo=UTC),
        )

    def test_aware_z_suffix_treated_as_utc(self):
        result = parse_local_date("2025-01-15T10:00:00Z")
        self.assertEqual(
            result, datetime.datetime(2025, 1, 15, 10, 0, tzinfo=UTC),
        )

    def test_naive_with_time_component(self):
        result = parse_local_date("2025-01-15 10:00")
        self.assertIsNotNone(result)
        self.assertEqual(result.tzinfo, UTC)


class TestResolvePeriodToRange(unittest.TestCase):

    NOW = datetime.datetime(2025, 5, 1, 12, 0, tzinfo=UTC)

    def test_period_days_overrides_custom(self):
        # «N дней назад» в шапке должен побеждать введённый custom-диапазон,
        # иначе пользователь меняет селектор и не понимает, почему ничего
        # не изменилось.
        custom_from = datetime.datetime(2024, 1, 1, tzinfo=UTC)
        custom_to = datetime.datetime(2024, 12, 31, tzinfo=UTC)
        df, dt_ = resolve_period_to_range(7, custom_from, custom_to, now=self.NOW)
        self.assertEqual(df, self.NOW - datetime.timedelta(days=7))
        self.assertIsNone(dt_)

    def test_custom_dates_only(self):
        f = datetime.datetime(2025, 1, 1, tzinfo=UTC)
        t = datetime.datetime(2025, 1, 31, tzinfo=UTC)
        self.assertEqual(resolve_period_to_range(0, f, t), (f, t))

    def test_only_date_from(self):
        f = datetime.datetime(2025, 1, 1, tzinfo=UTC)
        self.assertEqual(resolve_period_to_range(0, f, None), (f, None))

    def test_only_date_to(self):
        t = datetime.datetime(2025, 1, 31, tzinfo=UTC)
        self.assertEqual(resolve_period_to_range(0, None, t), (None, t))

    def test_no_dates_no_period(self):
        self.assertEqual(resolve_period_to_range(0, None, None), (None, None))

    def test_negative_period_treated_as_no_period(self):
        # Защита от случайного «-1»: не должен генерить дату в будущем.
        self.assertEqual(resolve_period_to_range(-1, None, None), (None, None))

    def test_period_uses_real_now_when_not_injected(self):
        # Без now=... функция берёт текущее UTC. Проверяем диапазон, чтобы
        # тест не был flaky на медленной CI.
        before = datetime.datetime.now(UTC)
        df, dt_ = resolve_period_to_range(30, None, None)
        after = datetime.datetime.now(UTC)
        self.assertIsNone(dt_)
        self.assertGreaterEqual(df, before - datetime.timedelta(days=30))
        self.assertLessEqual(df, after - datetime.timedelta(days=30))


if __name__ == "__main__":
    unittest.main()
