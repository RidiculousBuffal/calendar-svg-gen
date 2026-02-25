from datetime import date, datetime
from typing import Dict, List
from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class Holiday(BaseModel):
    name: str = Field(alias="Name", description="节假日名称，如：元旦、春节")
    start_date: date = Field(alias="StartDate", description="放假开始日期 (YYYY-MM-DD)")
    end_date: date = Field(alias="EndDate", description="放假结束日期 (YYYY-MM-DD)")
    duration: int = Field(alias="Duration", description="放假天数")
    comp_days: List[str] = Field(alias="CompDays", description="调休/补班日期列表 (YYYY-MM-DD 格式)")
    url: HttpUrl = Field(alias="URL", description="国务院公告链接")
    memo: str = Field(alias="Memo", description="放假安排详细说明")


class HolidayCalendar(BaseModel):

    name: str = Field(alias="Name", description="数据集名称")
    version: str = Field(alias="Version", description="版本号")
    generated: str = Field(alias="Generated", description="数据生成时间")
    timezone: str = Field(alias="Timezone", description="时区，如：Asia/Shanghai")
    author: str = Field(alias="Author", description="作者/来源")
    url: HttpUrl = Field(alias="URL", description="项目/数据源链接")
    years: Dict[str, List[Holiday]] = Field(
        alias="Years",
        description="按年份分组的节假日列表，键为年份字符串(如'2023')"
    )

class HolidayResult(BaseModel):
    isHoliday: bool = False
    name:str
    # 是否补班，如果是，那么name 同步变为 春节补班
    isCompDay: bool = False