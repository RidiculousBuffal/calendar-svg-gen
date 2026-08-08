from datetime import date

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import Response
from starlette.middleware.cors import CORSMiddleware

from backend.SVG import generate_calendar_svg
from backend.Worker import Worker

_worker: Worker = Worker()

app = FastAPI(
    title="中国节假日月历 SVG API",
    description=(
        "返回当月（或指定年月）的月历 SVG，自动标注中国法定节假日与调休补班。\n\n"
        "节假日数据来源：[china-holiday-calender](https://github.com/lanceliao/china-holiday-calender)"
    ),
    version="2.0.0",
)

app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_credentials=True,  # 允许携带 Cookie
                   allow_methods=["*"],  # 允许所有 HTTP 方法
                   allow_headers=["*"],  # 允许所有 HTTP 头部
                   )


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
    today = date.today()

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
            "当月月历": "GET /calendar",
            "指定年月": "GET /calendar?year=2026&month=2",
            "交互文档": "GET /docs",
        },
    }
