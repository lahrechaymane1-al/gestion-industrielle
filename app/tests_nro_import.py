"""Tests for NRO2026 import."""

from datetime import date

from django.test import SimpleTestCase

from app.nro_import_utils import (
    build_cause,
    diversite_for_store_day,
    filter_rows_by_day,
    import_tag_for_day,
    split_row_into_hour_fiches,
)


class NroImportTests(SimpleTestCase):
    def test_split_under_60_one_fiche(self):
        self.assertEqual(split_row_into_hour_fiches(29), [(1, 29)])
        self.assertEqual(split_row_into_hour_fiches(60), [(1, 60)])
        self.assertEqual(split_row_into_hour_fiches(0), [(1, 0)])

    def test_split_266_into_hours(self):
        self.assertEqual(
            split_row_into_hour_fiches(266),
            [(1, 60), (2, 60), (3, 60), (4, 60), (5, 26)],
        )

    def test_split_overflow_merges_into_h8(self):
        chunks = split_row_into_hour_fiches(500)
        self.assertEqual(len(chunks), 8)
        self.assertEqual(chunks[-1][0], 8)
        self.assertEqual(sum(m for _, m in chunks), 500)

    def test_day_filter(self):
        rows = [
            {"date": date(2026, 5, 1), "minutes": 10},
            {"date": date(2026, 5, 8), "minutes": 5},
            {"date": date(2026, 5, 7), "minutes": 3},
        ]
        d1 = filter_rows_by_day(rows, date(2026, 5, 1))
        self.assertEqual(len(d1), 1)
        self.assertEqual(import_tag_for_day(date(2026, 5, 3)), "[import:NRO2026]:2026-05-03")

    def test_diversite_calendar_a1_ranges(self):
        self.assertEqual(diversite_for_store_day(date(2026, 5, 1)), "A1")
        self.assertEqual(diversite_for_store_day(date(2026, 5, 10)), "A1")
        self.assertEqual(diversite_for_store_day(date(2026, 5, 13)), "A1")
        self.assertEqual(diversite_for_store_day(date(2026, 5, 14)), "A1")

    def test_diversite_calendar_a3_outside_ranges(self):
        self.assertEqual(diversite_for_store_day(date(2026, 5, 11)), "A3")
        self.assertEqual(diversite_for_store_day(date(2026, 5, 12)), "A3")
        self.assertEqual(diversite_for_store_day(date(2026, 5, 15)), "A3")
        self.assertEqual(diversite_for_store_day(date(2026, 5, 17)), "A3")

    def test_build_cause_includes_diversite_tag(self):
        cause = build_cause("A3", "Panne capteur", day=date(2026, 5, 11))
        self.assertIn("[diversite:A3]", cause)
        self.assertIn("[import:NRO2026]:2026-05-11", cause)
