import asyncio

import httpx
from httpx import Limits
from backend.Holiday import Holiday, HolidayCalendar, HolidayResult
from datetime import date, datetime


class Worker:
    def __init__(self):
        self.url = "https://www.shuyz.com/githubfiles/china-holiday-calender/master/holidayAPI.json"

    async def crawl(self):
        async with httpx.AsyncClient(timeout=1000,
                                     limits=Limits(max_connections=1000, max_keepalive_connections=1000)) as client:
            response = await client.get(self.url)
            return HolidayCalendar.model_validate(response.json()).years

    async def check(self, year: int, month: int, day: int) -> HolidayResult:
        # 如果数据未缓存，先调用crawl获取数据
        if not hasattr(self, 'holidays'):
            self.holidays = await self.crawl()

        target_date = date(year, month, day)
        year_str = str(year)

        # 如果年份不存在于数据中，返回默认非节假日结果
        if year_str not in self.holidays:
            return HolidayResult(isHoliday=False, name="", isCompDay=False)

        # 遍历该年份的所有节假日安排
        for holiday in self.holidays[year_str]:
            # 检查是否在放假日期范围内（含起止日期）
            if holiday.start_date <= target_date <= holiday.end_date:
                return HolidayResult(
                    isHoliday=True,
                    name=holiday.name,
                    isCompDay=False
                )

            # 检查是否为补班日（调休工作日）
            for comp_day_str in holiday.comp_days:
                comp_date = datetime.strptime(comp_day_str, "%Y-%m-%d").date()
                if comp_date == target_date:
                    return HolidayResult(
                        isHoliday=False,
                        name=f"{holiday.name}补班",
                        isCompDay=True
                    )

        return HolidayResult(isHoliday=False, name="", isCompDay=False)


if __name__ == "__main__":
    async def main():
        worker = Worker()
        print(await worker.check(2026, 2, 28))


    asyncio.run(main())
