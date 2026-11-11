import unittest
from datetime import date

import pandas as pd

from src.sync_etf_daily import to_records


class TestETFDailyTransform(unittest.TestCase):
    def test_one_valid_bar(self):
        frame = pd.DataFrame([{
            "日期": "2026-11-10",
            "开盘": 1.12,
            "最高": 1.20,
            "最低": 1.10,
            "收盘": 1.18,
            "成交量": 100,
            "成交额": 200,
        }])
        records = to_records(frame, "563020", date(2026, 11, 11))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["symbol"], "563020")
        self.assertEqual(records[0]["trade_date"], "2026-11-10")

    def test_invalid_high_rejected(self):
        frame = pd.DataFrame([{
            "日期": "2026-11-10",
            "开盘": 1.12,
            "最高": 1.15,
            "最低": 1.10,
            "收盘": 1.18,
            "成交量": 100,
            "成交额": 200,
        }])
        with self.assertRaises(ValueError):
            to_records(frame, "563020", date(2026, 11, 11))


if __name__ == "__main__":
    unittest.main()
