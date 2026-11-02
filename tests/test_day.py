import unittest
from datetime import date
from fastapi.testclient import TestClient

from main import app


class TestDayAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        with cls.client:
            pass  # triggers lifespan

    def test_holiday_spring_festival(self):
        """2026-02-17 春节当天：节假日、非周末（周二）、不上班、节日名春节"""
        response = self.client.get("/day?date=2026-02-17")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            set(data.keys()),
            {"date", "isHoliday", "isWeekend", "holidayName", "isWorkday", "isCompDay"},
        )
        self.assertEqual(data["date"], "2026-02-17")
        self.assertTrue(data["isHoliday"])
        self.assertFalse(data["isWeekend"])
        self.assertEqual(data["holidayName"], "春节")
        self.assertFalse(data["isWorkday"])
        self.assertFalse(data["isCompDay"])

    def test_comp_day_saturday(self):
        """2026-02-28 春节补班日（周六）：非节假日、是周末、需上班、节日名春节补班"""
        response = self.client.get("/day?date=2026-02-28")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            set(data.keys()),
            {"date", "isHoliday", "isWeekend", "holidayName", "isWorkday", "isCompDay"},
        )
        self.assertEqual(data["date"], "2026-02-28")
        self.assertFalse(data["isHoliday"])
        self.assertTrue(data["isWeekend"])
        self.assertEqual(data["holidayName"], "春节补班")
        self.assertTrue(data["isWorkday"])
        self.assertTrue(data["isCompDay"])

    def test_holiday_on_weekend(self):
        """2026-02-15 春节假期首日（周日）：是节假日、是周末、不上班、节日名春节"""
        response = self.client.get("/day?date=2026-02-15")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            set(data.keys()),
            {"date", "isHoliday", "isWeekend", "holidayName", "isWorkday", "isCompDay"},
        )
        self.assertEqual(data["date"], "2026-02-15")
        self.assertTrue(data["isHoliday"])
        self.assertTrue(data["isWeekend"])
        self.assertEqual(data["holidayName"], "春节")
        self.assertFalse(data["isWorkday"])
        self.assertFalse(data["isCompDay"])

    def test_normal_workday(self):
        """2026-03-02 普通周一：非节假日、非周末、需上班、节日名为 null"""
        response = self.client.get("/day?date=2026-03-02")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            set(data.keys()),
            {"date", "isHoliday", "isWeekend", "holidayName", "isWorkday", "isCompDay"},
        )
        self.assertEqual(data["date"], "2026-03-02")
        self.assertFalse(data["isHoliday"])
        self.assertFalse(data["isWeekend"])
        self.assertIsNone(data["holidayName"])
        self.assertTrue(data["isWorkday"])
        self.assertFalse(data["isCompDay"])

    def test_normal_weekend(self):
        """2026-03-01 普通周日：非节假日、是周末、不上班、节日名为 null"""
        response = self.client.get("/day?date=2026-03-01")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            set(data.keys()),
            {"date", "isHoliday", "isWeekend", "holidayName", "isWorkday", "isCompDay"},
        )
        self.assertEqual(data["date"], "2026-03-01")
        self.assertFalse(data["isHoliday"])
        self.assertTrue(data["isWeekend"])
        self.assertIsNone(data["holidayName"])
        self.assertFalse(data["isWorkday"])
        self.assertFalse(data["isCompDay"])

    def test_national_day_user_example(self):
        """2026-10-01 国庆节：验证用户提到的示例"""
        response = self.client.get("/day?date=2026-10-01")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, {
            "date": "2026-10-01",
            "isHoliday": True,
            "isWeekend": False,
            "holidayName": "国庆节",
            "isWorkday": False,
            "isCompDay": False,
        })

    def test_default_today(self):
        """不传 date 参数时，默认返回当天"""
        response = self.client.get("/day")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["date"], date.today().strftime("%Y-%m-%d"))

    def test_invalid_date(self):
        """非法日期格式返回 400"""
        response = self.client.get("/day?date=not-a-date")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("无效的日期格式", data["detail"])

    def test_invalid_month_date(self):
        """不存在的日期返回 400"""
        response = self.client.get("/day?date=2026-02-30")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("无效的日期格式", data["detail"])

    def test_single_digit_format(self):
        """支持 2026-2-8 格式解析"""
        response = self.client.get("/day?date=2026-2-8")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["date"], "2026-02-08")

    def test_calendar_endpoint_still_works(self):
        """确保现有 /calendar 接口正常运行"""
        response = self.client.get("/calendar?year=2026&month=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/svg+xml")
        self.assertIn("<svg", response.text)

    def test_root_endpoint(self):
        """确保首页包含 /day 文档说明"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("单日状态查询", data["usage"])


if __name__ == "__main__":
    unittest.main()
