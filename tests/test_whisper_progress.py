"""
Регрессионные тесты для прогресс-бара скачивания Whisper-модели.

Контекст бага (PR #3 review, подтверждён по исходникам huggingface_hub 1.15.0):
в snapshot_download переданным `tqdm_class` создаются ДВА разных бара:

  1. родительский БАЙТОВЫЙ бар `bytes_progress` — unit="B", unit_scale=True,
     создаётся с total=0, а реальный размер hub дописывает прямым
     `bytes_progress.total += size` (в обход нашего __init__); прогресс в
     байтах прилетает через .update(n). Внутри snapshot_download hub НЕ
     закрывает этот бар (после thread_map только set_description);
  2. служебный счётчик ФАЙЛОВ из thread_map — unit="it", total = число файлов
     (1–4), тикает по +1 на завершённый файл.

Старый `_make_progress_tqdm` складывал total/инкременты ОБОИХ баров в одну
статистику. Из-за total=0 у байтового бара в момент создания знаменателем
становилось число файлов (≈4), и UI замирал на «0 / 0 МБ (100%)».

Фикс: учитывать только байтовые бары (распознаём по unit на "B*" ИЛИ по
unit_scale — устойчиво к переименованию unit в будущих версиях hub) и брать
знаменатель прямо из их .total (который hub меняет на месте), с откатом на
размер модели, пока total ещё 0. Финальный кадр форсится при достижении 100%,
т.к. hub не закрывает байтовый бар.

ВНИМАНИЕ для будущих правок: единственный тест, реально воспроизводящий
исходный баг «0/0 МБ (100%)» на старом коде, — test_file_count_bar_*. Если
ослабить/удалить его mid-point ассерт (assertLess на ~0.10), регрессия
знаменателя может проскочить незамеченной. Остальные тесты проверяют смежные
свойства (ход до 100%, fallback, unit_scale-распознавание, агрегацию).

tqdm здесь настоящий (зависимость huggingface_hub), сеть/диск не задействованы.
"""

from __future__ import annotations

import unittest

from tg_exporter.services.transcription.whisper_local import _make_progress_tqdm


class TestWhisperProgressTqdm(unittest.TestCase):
    def setUp(self) -> None:
        self.events: list[tuple[float, str]] = []
        # size_mb=147 ≈ модель "base"; отсюда берётся fallback-знаменатель.
        self.size_mb = 147
        self.total_bytes = self.size_mb * 1024 * 1024
        self.cls = _make_progress_tqdm(
            progress_cb=lambda ratio, text: self.events.append((ratio, text)),
            model_size="base",
            size_mb=self.size_mb,
        )

    def _new_bytes_progress(self):
        """Имитация bytes_progress: байтовый бар, создаётся с total=0."""
        return self.cls(total=0, unit="B", unit_scale=True)

    def test_tqdm_class_is_available(self) -> None:
        self.assertIsNotNone(self.cls, "tqdm недоступен — _make_progress_tqdm вернул None")

    def test_byte_progress_advances_smoothly(self) -> None:
        """
        Сценарий hub 1.15.0: bytes_progress создан с total=0, hub дописывает
        total на месте, прогресс в байтах прилетает через .update(n).
        Проверяем промежуточные кадры (а не только финал) и реальный
        знаменатель — без застывания.
        """
        bp = self._new_bytes_progress()
        bp.total += self.total_bytes  # hub объявляет размер ПОСЛЕ создания

        bp.update(self.total_bytes // 4)
        mid_ratio, mid_text = self.events[-1]
        self.assertAlmostEqual(mid_ratio, 0.25, places=2)
        self.assertIn("147", mid_text)  # знаменатель реальный, не «0»

        bp.update(self.total_bytes - self.total_bytes // 4)
        final_ratio, final_text = self.events[-1]
        self.assertAlmostEqual(final_ratio, 1.0, places=2)
        self.assertIn("100%", final_text)

    def test_file_count_bar_does_not_poison_denominator(self) -> None:
        """
        ГЛАВНЫЙ регрессионный тест исходного бага. Служебный файловый бар
        (unit="it", total=4), созданный тем же tqdm_class, НЕ должен попадать в
        байтовый знаменатель. На старом коде этот тест падал с «0 / 0 МБ
        (100%)» — ровно симптом из issue #2.
        """
        # thread_map создаёт файловый счётчик ПЕРВЫМ:
        file_bar = self.cls(total=4, unit="it")
        # параллельно идёт байтовый бар:
        bp = self._new_bytes_progress()
        bp.total += self.total_bytes

        # скачали реально ~10% байт, при этом 1 файл уже «завершён»:
        bp.update(self.total_bytes // 10)
        file_bar.update(1)

        ratio, text = self.events[-1]
        # По байтам должно быть ~0.10. Если бы файловый бар отравил знаменатель
        # (total стал бы 4), ratio подскочил бы к ~0.25+/1.0. Узкая граница
        # вокруг 0.10 — намеренно: это и есть load-bearing ассерт регрессии.
        self.assertAlmostEqual(ratio, 0.10, places=2,
                               msg=f"знаменатель отравлён файловым баром: ratio={ratio}, text={text}")
        # Знаменатель в тексте — реальные 147 МБ, а не «0» (как на старом коде).
        self.assertIn("/ 147 МБ", text)
        self.assertNotIn("0 / 0", text)

        # дочитываем до конца — должны дойти до 100%, не застрять:
        bp.update(self.total_bytes - self.total_bytes // 10)
        file_bar.update(3)
        final_ratio, _ = self.events[-1]
        self.assertAlmostEqual(final_ratio, 1.0, places=2)

    def test_bytes_bar_detected_by_unit_scale_not_just_literal_B(self) -> None:
        """
        Устойчивость к переименованию unit: если будущая версия hub создаст
        байтовый бар с unit != "B" (например "iB") но с unit_scale=True, он
        всё равно должен распознаваться как байтовый и двигать прогресс.
        Защищает от молчаливого возврата бага при дрейфе незапиненного hub.
        """
        bar = self.cls(total=0, unit="iB", unit_scale=True)
        bar.total += self.total_bytes
        bar.update(self.total_bytes // 2)
        self.assertTrue(self.events, "iB-бар не распознан как байтовый — прогресс молчит")
        ratio, _ = self.events[-1]
        self.assertAlmostEqual(ratio, 0.5, places=2)

    def test_final_frame_forced_despite_throttle(self) -> None:
        """
        hub НЕ закрывает байтовый бар, а последние .update могут попасть в окно
        троттла 0.3с. Финальный кадр 100% должен форситься в update() при
        достижении total — без опоры на close() или внешний emit.
        """
        bp = self._new_bytes_progress()
        bp.total += self.total_bytes
        # Два быстрых апдейта подряд (внутри окна троттла), второй добивает до 100%.
        bp.update(self.total_bytes // 2)
        bp.update(self.total_bytes - self.total_bytes // 2)
        # close() НЕ вызываем — имитируем реальное поведение hub.
        final_ratio, final_text = self.events[-1]
        self.assertAlmostEqual(final_ratio, 1.0, places=2)
        self.assertIn("100%", final_text)

    def test_no_total_falls_back_to_model_size(self) -> None:
        """
        Пока hub не объявил размеры (total всех байтовых баров ещё 0),
        знаменатель должен откатываться на size_mb, а не делить на ноль.
        """
        bp = self._new_bytes_progress()  # total остаётся 0
        bp.update(10 * 1024 * 1024)  # 10 МБ скачано, размер ещё не объявлен
        ratio, text = self.events[-1]
        # 10 МБ из 147 МБ fallback ≈ 0.068
        self.assertGreater(ratio, 0.0)
        self.assertLess(ratio, 0.15)
        self.assertIn("147", text)

    def test_multiple_byte_files_aggregate(self) -> None:
        """
        Несколько байтовых файлов (модель из нескольких шардов): знаменатель —
        сумма их .total; ratio считается по сумме.
        """
        a = self.cls(total=0, unit="B", unit_scale=True)
        a.total += 100 * 1024 * 1024
        b = self.cls(total=0, unit="B", unit_scale=True)
        b.total += 100 * 1024 * 1024
        a.update(100 * 1024 * 1024)
        b.update(100 * 1024 * 1024)
        final_ratio, _ = self.events[-1]
        self.assertAlmostEqual(final_ratio, 1.0, places=2)


if __name__ == "__main__":
    unittest.main()
