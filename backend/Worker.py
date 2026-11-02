import asyncio
from datetime import date, datetime
from typing import Dict, List, Optional
import httpx
from httpx import Limits

from backend.Holiday import Holiday, HolidayCalendar, HolidayResult, DayDetail


class Worker:
    def __init__(self):
        self.holidays: Optional[Dict[str, List[Holiday]]] = None
        self.url = "https://www.shuyz.com/githubfiles/china-holiday-calender/master/holidayAPI.json"

    async def crawl(self) -> Dict[str, List[Holiday]]:
        async with httpx.AsyncClient(timeout=10,
                                     limits=Limits(max_connections=10, max_keepalive_connections=10)) as client:
            response = await client.get(self.url)
            self.holidays = HolidayCalendar.model_validate(response.json()).years
            return self.holidays

    async def ensure_data(self) -> Dict[str, List[Holiday]]:
        if self.holidays is None:
            await self.crawl()
        return self.holidays

    async def check(self, year: int, month: int, day: int) -> HolidayResult:
        await self.ensure_data()
        target_date = date(year, month, day)

        if not self.holidays:
            return HolidayResult(isHoliday=False, name="", isCompDay=False)

        # 检查当年及相邻年份（处理跨年节假日，如元旦假期可能跨越12月31日）
        candidate_years = [str(year), str(year + 1), str(year - 1)]
        for year_str in candidate_years:
            if year_str not in self.holidays:
                continue
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

    async def get_day_detail(self, target_date: date) -> DayDetail:
        holiday_result = await self.check(target_date.year, target_date.month, target_date.day)
        is_weekend = target_date.weekday() >= 5
        is_holiday = holiday_result.isHoliday
        is_comp_day = holiday_result.isCompDay

        # 是否上班：
        # 1. 节假日（放假）：不上班
        # 2. 补班日（调休）：上班
        # 3. 普通周末：不上班
        # 4. 普通工作日：上班
        if is_holiday:
            is_workday = False
        elif is_comp_day:
            is_workday = True
        else:
            is_workday = not is_weekend

        holiday_name = holiday_result.name if (is_holiday or is_comp_day) else None
        date_str = target_date.strftime("%Y-%m-%d")

        return DayDetail(
            date=date_str,
            isHoliday=is_holiday,
            isWeekend=is_weekend,
            holidayName=holiday_name,
            isWorkday=is_workday,
            isCompDay=is_comp_day,
        )


if __name__ == "__main__":
    async def main():
        worker = Worker()
        print(await worker.check(2026, 2, 28))
        print(await worker.get_day_detail(date(2026, 2, 28)))


    asyncio.run(main())
