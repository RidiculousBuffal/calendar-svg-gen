import asyncio
import calendar
from datetime import date, timedelta

from  backend.Worker import Worker

# 月份中文名称
MONTH_NAMES = {
    1: "一月", 2: "二月", 3: "三月", 4: "四月",
    5: "五月", 6: "六月", 7: "七月", 8: "八月",
    9: "九月", 10: "十月", 11: "十一月", 12: "十二月",
}

WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 颜色配置
C = {
    "bg":               "#FFFFFF",
    "title":            "#1a1a2e",
    "header":           "#666666",
    "cell_bg":          "#FFFFFF",
    "cell_border":      "#E8E8E8",
    "weekend_bg":       "#FFF7F7",
    "weekend_border":   "#F2D6D6",
    "day_text":         "#1a1a2e",
    "other_bg":         "#FAFAFA",
    "other_text":       "#BBBBBB",
    # 节假日
    "hol_bg":           "#F0FBF0",
    "hol_border":       "#C8EAC8",
    "hol_text":         "#2E7D32",
    "hol_dot":          "#4CAF50",
    # 调休补班
    "comp_bg":          "#FFF8F0",
    "comp_border":      "#FFD9B0",
    "comp_text":        "#E65100",
    "comp_dot":         "#FF6D00",
    # 今天
    "today_bg":         "#E3F2FD",
    "today_border":     "#90CAF9",
    "today_text":       "#1565C0",
}

# 布局
CELL_W   = 130
CELL_H   = 110
CELL_GAP = 8
PAD_X    = 40
PAD_TOP  = 100
HEADER_H = 50
RADIUS   = 12


def _rect(x, y, w, h, r, fill, stroke, sw=1.5):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'rx="{r}" ry="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def _text(x, y, content, size, color, anchor="middle", weight="normal", baseline="auto"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}" dominant-baseline="{baseline}">'
            f'{content}</text>')


async def generate_calendar_svg(year: int, month: int, worker: Worker) -> str:
    """异步生成指定年月的月历 SVG 字符串，可传入已缓存的 Worker 实例"""
    today = date.today()
    first_day = date(year, month, 1)
    _, days_in_month = calendar.monthrange(year, month)

    # 构建 6×7 格子（周一起始）
    cells: list[date] = []
    first_weekday = first_day.weekday()
    for i in range(first_weekday):
        cells.append(first_day - timedelta(days=first_weekday - i))
    for d in range(1, days_in_month + 1):
        cells.append(date(year, month, d))
    last = date(year, month, days_in_month)
    while len(cells) < 42:
        cells.append(last + timedelta(days=len(cells) - (first_weekday + days_in_month) + 1))

    # 确保节假日数据已加载
    await worker.ensure_data()
    current_month_dates = [d for d in cells if d.month == month and d.year == year]
    results = await asyncio.gather(
        *[worker.check(d.year, d.month, d.day) for d in current_month_dates]
    )
    day_info: dict[date, object] = dict(zip(current_month_dates, results))

    # SVG 尺寸
    cols, rows = 7, 6
    svg_w = PAD_X * 2 + cols * CELL_W + (cols - 1) * CELL_GAP
    svg_h = PAD_TOP + HEADER_H + CELL_GAP + rows * CELL_H + (rows - 1) * CELL_GAP + 44

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" '
        f'viewBox="0 0 {svg_w} {svg_h}" '
        f'font-family="\'PingFang SC\',\'Microsoft YaHei\',\'Noto Sans CJK SC\',sans-serif">'
    )
    parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="{C["bg"]}"/>')

    # 标题
    parts.append(_text(svg_w / 2, 58, f"{year} 年 {MONTH_NAMES[month]}",
                       28, C["title"], weight="bold"))

    # 星期表头
    for col, name in enumerate(WEEKDAY_NAMES):
        x = PAD_X + col * (CELL_W + CELL_GAP) + CELL_W / 2
        y = PAD_TOP + HEADER_H / 2 + 6
        parts.append(_text(x, y, name, 14, C["header"]))

    # 表头分隔线
    line_y = PAD_TOP + HEADER_H + 2
    parts.append(f'<line x1="{PAD_X}" y1="{line_y}" x2="{svg_w - PAD_X}" y2="{line_y}" '
                 f'stroke="#EEEEEE" stroke-width="1"/>')

    # 格子
    for idx, d in enumerate(cells):
        row, col = divmod(idx, cols)
        x = PAD_X + col * (CELL_W + CELL_GAP)
        y = PAD_TOP + HEADER_H + CELL_GAP + row * (CELL_H + CELL_GAP)

        is_cur = (d.month == month and d.year == year)
        is_today = (d == today)
        info = day_info.get(d) if is_cur else None

        # 决定样式
        if not is_cur:
            bg, border, day_color = C["other_bg"], C["cell_border"], C["other_text"]
            dot, label, label_color = None, None, None
        elif is_today:
            bg, border, day_color = C["today_bg"], C["today_border"], C["today_text"]
            dot, label, label_color = None, None, None
        elif info and info.isHoliday:
            bg, border, day_color = C["hol_bg"], C["hol_border"], C["hol_text"]
            dot, label, label_color = C["hol_dot"], info.name, C["hol_text"]
        elif info and info.isCompDay:
            bg, border, day_color = C["comp_bg"], C["comp_border"], C["comp_text"]
            dot, label, label_color = C["comp_dot"], info.name, C["comp_text"]
        elif d.weekday() >= 5:
            bg, border, day_color = C["weekend_bg"], C["weekend_border"], C["day_text"]
            dot, label, label_color = None, None, None
        else:
            bg, border, day_color = C["cell_bg"], C["cell_border"], C["day_text"]
            dot, label, label_color = None, None, None

        # 格子背景
        parts.append(_rect(x, y, CELL_W, CELL_H, RADIUS, bg, border))

        # 右上角圆点
        if dot:
            parts.append(f'<circle cx="{x + CELL_W - 14}" cy="{y + 14}" r="4" fill="{dot}"/>')

        # 日期数字
        fs = 22 if is_cur else 18
        fw = "bold" if is_cur else "normal"
        offset_y = -10 if label else 0
        parts.append(_text(x + CELL_W / 2, y + CELL_H / 2 + offset_y,
                           str(d.day), fs, day_color, weight=fw, baseline="middle"))

        # 节假日/补班标签
        if label:
            parts.append(_text(x + CELL_W / 2, y + CELL_H / 2 + offset_y + fs / 2 + 14,
                               label, 12, label_color))

    # 图例
    lx = svg_w - PAD_X - 280
    ly = svg_h - 18
    parts.append(f'<circle cx="{lx}" cy="{ly - 3}" r="4" fill="{C["hol_dot"]}"/>')
    parts.append(_text(lx + 10, ly, "节假日", 11, C["hol_text"], anchor="start"))
    parts.append(f'<circle cx="{lx + 62}" cy="{ly - 3}" r="4" fill="{C["comp_dot"]}"/>')
    parts.append(_text(lx + 72, ly, "调休补班", 11, C["comp_text"], anchor="start"))
    parts.append(_rect(lx + 140, ly - 11, 12, 12, 3, C["today_bg"], C["today_border"], 1.5))
    parts.append(_text(lx + 156, ly, "今天", 11, C["today_text"], anchor="start"))
    parts.append(_rect(lx + 198, ly - 11, 12, 12, 3, C["weekend_bg"], C["weekend_border"], 1.5))
    parts.append(_text(lx + 214, ly, "周末", 11, C["day_text"], anchor="start"))

    parts.append("</svg>")
    return "\n".join(parts)
