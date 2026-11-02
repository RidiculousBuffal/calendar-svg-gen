from contextlib import asynccontextmanager
from datetime import date as dt_date, datetime

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import Response
from starlette.middleware.cors import CORSMiddleware

from backend.Holiday import DayDetail
from backend.SVG import generate_calendar_svg
from backend.Worker import Worker

_worker: Worker = Worker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await _worker.ensure_data()
    except Exception as e:
        print(f"警告：启动时加载节假日数据失败: {e}")
    yield


app = FastAPI(
    title="中国节假日月历 SVG API",
    description=(
        "提供中国法定节假日与调休补班查询，支持单日状态查询以及月历 SVG 生成。\n\n"
        "节假日数据来源：[china-holiday-calender](https://github.com/lanceliao/china-holiday-calender)"
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # 允许携带 Cookie
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有 HTTP 头部
)


@app.get(
    "/day",
    summary="查询单日节假日及上班状态",
    response_model=DayDetail,
    description=(
        "根据传入的日期（格式 `YYYY-MM-DD`）查询当天的状态，包括是否是节假日、是否是周末、是什么节假日、是否上班。\n\n"
        "- 若不传 `date` 参数，默认查询当天。"
    ),
)
async def get_day(
    date: str = Query(
        default=None,
        description="查询日期，格式为 YYYY-MM-DD（如 2026-02-17），默认当天",
        openapi_examples={
            "holiday": {
                "summary": "法定节假日（春节）",
                "value": "2026-02-17",
            },
            "comp_day": {
                "summary": "调休补班日（需上班）",
                "value": "2026-02-28",
            },
            "weekend": {
                "summary": "普通周末（不上班）",
                "value": "2026-03-01",
            },
            "workday": {
                "summary": "普通工作日（需上班）",
                "value": "2026-03-02",
            },
        },
    ),
):
    """
    查询单日状态：
    - **isHoliday**: 是否是节假日（放假）
    - **isWeekend**: 是否是周末
    - **holidayName**: 是什么节假日（如'春节'；若为补班日标注如'春节补班'；普通日为 null）
    - **isWorkday**: 是否上班（工作日或调休补班为 true，节假日或周末为 false）
    - **isCompDay**: 是否是调休补班日
    """
    if not date or not date.strip():
        target_date = dt_date.today()
    else:
        try:
            target_date = datetime.strptime(date.strip(), "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的日期格式: '{date}'，请使用 YYYY-MM-DD 格式，例如 2026-02-17",
            )

    try:
        return await _worker.get_day_detail(target_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get(
    "/calendar",
    summary="获取月历 SVG",
    response_description="SVG 格式月历，标注节假日（绿色）和调休补班（橙色）",
    responses={200: {"content": {"image/svg+xml": {}}}},
)
async def get_calendar(
    year: int = Query(default=None, description="年份，默认当前年", ge=2020, le=2030),
    month: int = Query(default=None, description="月份 1-12，默认当前月", ge=1, le=12),
):
    """
    返回指定年月（默认当月）的中国节假日月历 SVG。

    **样式说明**
    | 样式 | 含义 |
    |------|------|
    | 🟢 绿色背景 + 圆点 | 法定节假日（放假） |
    | 🟠 橙色背景 + 圆点 | 调休补班（需上班） |
    | 🔵 蓝色背景 | 今天 |
    """
    today = dt_date.today()

    y = year if year is not None else today.year
    m = month if month is not None else today.month
    try:
        svg = await generate_calendar_svg(y, m, _worker)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SVG 生成失败: {e}")

    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": f'inline; filename="calendar-{y}-{m:02d}.svg"',
            "Cache-Control": "no-cache",
        },
    )


@app.get("/", summary="API 首页")
def root():
    return {
        "name": "中国节假日月历 SVG API",
        "version": "2.0.0",
        "usage": {
            "单日状态查询": "GET /day?date=2026-02-17",
            "当月月历": "GET /calendar",
            "指定年月": "GET /calendar?year=2026&month=2",
            "交互文档": "GET /docs",
        },
    }
