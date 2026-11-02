# 日期状态查询接口（GET /day）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `GET /day?date=YYYY-MM-DD`，返回指定日期是否法定节假日、调休补班日、双休日。

**Architecture:** 在 `backend/Holiday.py` 增加三字段响应模型 `DayInfo`；在 `main.py` 新增路由，懒加载 `Worker.holidays`，复用 `Worker.check()` 判定节假日/补班，路由用 `weekday()` 判定周末。`/calendar` 与 `Worker.check()` 行为不变。

**Tech Stack:** Python 3.12, FastAPI 0.133.0, Pydantic 2.12.5, httpx 0.28.1, uvicorn 0.41.0

## Global Constraints

- 日期参数格式：`YYYY-MM-DD`，如 `2026-10-01`。
- 响应必须且只能包含 3 个布尔字段：`isHoliday`、`isCompDay`、`isWeekend`。
- `isWeekend` 纯按星期判定（周六/周日为 true），调休补班日也照常为 true。
- 未收录年份：返回 200，`isHoliday=false`、`isCompDay=false`，`isWeekend` 正常计算。
- 非法/缺失日期：422；数据源拉取或解析失败：500。
- 不修改 `Worker.check()` 签名与 `/calendar` 行为。
- 不新增依赖。
- 本任务禁止 Git 写操作（不执行 `git add` / `git commit` / `git push`）。
- 项目当前没有测试框架；不要新增 `tests/` 测试套件，使用临时 smoke 脚本验证。

---

### Task 1: 新增三字段响应模型

**Files:**
- Modify: `backend/Holiday.py`

**Interfaces:**
- Produces: `DayInfo`，字段为 `isHoliday: bool`、`isCompDay: bool`、`isWeekend: bool`，三个字段均为必填。

- [ ] **Step 1: 在 `backend/Holiday.py` 末尾追加模型**

```python
class DayInfo(BaseModel):
    isHoliday: bool = Field(description="是否为法定节假日")
    isCompDay: bool = Field(description="是否为调休补班日（需上班）")
    isWeekend: bool = Field(description="是否为周六/周日")
```

- [ ] **Step 2: 验证模型可正常构造**

Run:

```bash
uv run python - <<'PY'
from backend.Holiday import DayInfo

print(DayInfo(isHoliday=True, isCompDay=False, isWeekend=False).model_dump())
PY
```

Expected:

```text
{'isHoliday': True, 'isCompDay': False, 'isWeekend': False}
```

- [ ] **Step 3: 验证三个字段均为必填**

Run:

```bash
uv run python - <<'PY'
from pydantic import ValidationError

from backend.Holiday import DayInfo

try:
    DayInfo(isHoliday=True)
except ValidationError as exc:
    print("missing_fields", sorted(item["loc"][0] for item in exc.errors()))
PY
```

Expected:

```text
missing_fields ['isCompDay', 'isWeekend']
```

---

### Task 2: 新增 `GET /day` 路由

**Files:**
- Modify: `main.py`

**Interfaces:**
- Consumes: `DayInfo` from `backend.Holiday`；`_worker: Worker`；`Worker.check(year: int, month: int, day: int) -> HolidayResult`。
- Produces: `GET /day`，查询参数 `date`，响应模型 `DayInfo`。

**注意：** `Worker.check()` 内部直接下标访问 `self.holidays[year_str]`（`backend/Worker.py:25`），`holidays` 为 `None` 时会抛 `TypeError`，因此路由必须先完成加载。

- [ ] **Step 1: 在 `main.py` 的导入区加入 `DayInfo`**

在 `from backend.Worker import Worker` 之前加入：

```python
from backend.Holiday import DayInfo
```

`main.py` 已导入 `date` 与 `HTTPException`，本步骤不需要新增其它导入。

- [ ] **Step 2: 在 `get_calendar` 之后、`root` 之前新增路由**

```python
@app.get(
    "/day",
    summary="查询指定日期的节假日、调休与周末状态",
    response_model=DayInfo,
    response_description="当天的节假日、调休补班、双休日状态",
)
async def get_day(
        target_date: date = Query(
            ...,
            alias="date",
            description="日期，格式 YYYY-MM-DD，如 2026-10-01",
        ),
) -> DayInfo:
    """
    查询指定日期是否为法定节假日、调休补班日或双休日。

    **上班判定**
    `isCompDay || (!isHoliday && !isWeekend)`
    """
    if _worker.holidays is None:
        try:
            _worker.holidays = await _worker.crawl()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"节假日数据获取失败: {e}")

    result = await _worker.check(target_date.year, target_date.month, target_date.day)
    return DayInfo(
        isHoliday=result.isHoliday,
        isCompDay=result.isCompDay,
        isWeekend=target_date.weekday() >= 5,
    )
```

- [ ] **Step 3: 在 `root()` 的 `usage` 中补充接口说明**

保持 `root()` 其余内容不变，仅新增 `"日期查询"` 一行；修改后的完整代码如下（替换原 `root()`）：

```python
@app.get("/", summary="API 首页")
def root():
    return {
        "name": "中国节假日月历 SVG API",
        "version": "2.0.0",
        "usage": {
            "当月月历": "GET /calendar",
            "指定年月": "GET /calendar?year=2026&month=2",
            "日期查询": "GET /day?date=2026-10-01",
            "交互文档": "GET /docs",
        },
    }
```

- [ ] **Step 4: 语法检查**

Run:

```bash
uv run python -m compileall -q main.py backend/Holiday.py
```

Expected: 无输出，退出码 0。

- [ ] **Step 5: 使用确定性数据做接口 smoke 测试**

Run:

```bash
uv run python - <<'PY'
import asyncio

from httpx import ASGITransport, AsyncClient

import main
from backend.Holiday import Holiday

main._worker.holidays = {
    "2026": [
        Holiday.model_validate(
            {
                "Name": "国庆节",
                "StartDate": "2026-10-01",
                "EndDate": "2026-10-07",
                "Duration": 7,
                "CompDays": ["2026-09-20", "2026-10-10"],
                "URL": "https://www.gov.cn/",
                "Memo": "test",
            }
        )
    ]
}


async def fail_crawl():
    raise AssertionError("holidays 已加载时不应调用 crawl()")


async def run():
    main._worker.crawl = fail_crawl
    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://test"
    ) as client:
        cases = [
            ("2026-10-01", {"isHoliday": True, "isCompDay": False, "isWeekend": False}),
            ("2026-10-10", {"isHoliday": False, "isCompDay": True, "isWeekend": True}),
            ("2026-10-11", {"isHoliday": False, "isCompDay": False, "isWeekend": True}),
            ("2026-10-12", {"isHoliday": False, "isCompDay": False, "isWeekend": False}),
            ("2027-01-01", {"isHoliday": False, "isCompDay": False, "isWeekend": False}),
        ]
        for value, expected in cases:
            response = await client.get("/day", params={"date": value})
            assert response.status_code == 200, (value, response.status_code, response.text)
            assert response.json() == expected, (value, response.json(), expected)

        for bad in ("2026-13-01", "2026-02-30"):
            response = await client.get("/day", params={"date": bad})
            assert response.status_code == 422, (bad, response.status_code)

        response = await client.get("/day")
        assert response.status_code == 422, response.status_code

        async def boom():
            raise RuntimeError("network down")

        main._worker.holidays = None
        main._worker.crawl = boom
        response = await client.get("/day", params={"date": "2026-10-01"})
        assert response.status_code == 500, response.status_code
        detail = response.json()["detail"]
        assert detail.startswith("节假日数据获取失败"), detail
        assert "network down" in detail, detail

    print("smoke ok")


asyncio.run(run())
PY
```

Expected:

```text
smoke ok
```

说明：

- `fail_crawl` 替换后仍然通过前 5 个用例，证明「`holidays` 已加载时不重复拉取」的懒加载分支生效。
- 最后一个用例把 `holidays` 置回 `None`，验证拉取失败时返回 500 且 `detail` 带原因。

---

### Task 3: 更新接口文档

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: 已实现的 `GET /day`。
- Produces: README 中的日期查询示例。

- [ ] **Step 1: 在 `README.md` 的接口列表后补充说明**

````markdown
- 日期查询: `GET /day?date=2026-10-01`，返回 `isHoliday`、`isCompDay`、`isWeekend`。

```json
{"isHoliday": true, "isCompDay": false, "isWeekend": false}
```
````

- [ ] **Step 2: 确认文档与代码均包含新接口**

Run:

```bash
rg -n "GET /day|/day" README.md main.py
```

Expected: `README.md` 与 `main.py` 均有匹配行。

---

### Task 4: 使用真实数据源做端到端验证

**Files:**
- 无代码改动

**Interfaces:**
- Consumes: 运行中的 `GET /day` 与 `GET /calendar`。
- Produces: 真实数据下的响应记录。

- [ ] **Step 1: 启动服务**

Run（后台运行）:

```bash
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Expected: 日志出现 `Uvicorn running on http://127.0.0.1:8000`。

- [ ] **Step 2: 等待服务就绪**

Run:

```bash
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ || true)
  [ "$code" = "200" ] && break
  sleep 1
done
printf "ready=%s\n" "$code"
```

Expected:

```text
ready=200
```

- [ ] **Step 3: 验证真实节假日数据**

Run:

```bash
for d in 2026-10-01 2026-10-10 2026-10-11 2026-10-12 2026-02-14 2026-02-15 2027-01-01; do
  printf "%s " "$d"
  curl -s "http://127.0.0.1:8000/day?date=$d"
  echo
done
```

Expected:

```text
2026-10-01 {"isHoliday":true,"isCompDay":false,"isWeekend":false}
2026-10-10 {"isHoliday":false,"isCompDay":true,"isWeekend":true}
2026-10-11 {"isHoliday":false,"isCompDay":false,"isWeekend":true}
2026-10-12 {"isHoliday":false,"isCompDay":false,"isWeekend":false}
2026-02-14 {"isHoliday":false,"isCompDay":true,"isWeekend":true}
2026-02-15 {"isHoliday":true,"isCompDay":false,"isWeekend":true}
2027-01-01 {"isHoliday":false,"isCompDay":false,"isWeekend":false}
```

如果外网不可达导致数据拉取失败，或数据源实际内容与上表不一致，记录实际响应与错误原因；不要将本步骤标记为通过，改以 Task 2 的确定性 smoke 结果作为逻辑验证依据。

- [ ] **Step 4: 验证非法参数与缺失参数返回 422**

Run:

```bash
curl -s -o /dev/null -w "invalid=%{http_code}\n" "http://127.0.0.1:8000/day?date=2026-13-01"
curl -s -o /dev/null -w "nonexistent=%{http_code}\n" "http://127.0.0.1:8000/day?date=2026-02-30"
curl -s -o /dev/null -w "missing=%{http_code}\n" "http://127.0.0.1:8000/day"
```

Expected:

```text
invalid=422
nonexistent=422
missing=422
```

- [ ] **Step 5: 验证 `/calendar` 无回归**

Run:

```bash
curl -s -o /dev/null -w "calendar=%{http_code}\n" "http://127.0.0.1:8000/calendar?year=2026&month=10"
```

Expected:

```text
calendar=200
```

说明：`generate_calendar_svg` 会重新 `crawl()` 数据源，若外网不可达可能返回 500；此时记录为环境问题，并以 Task 2 的 smoke 结果判断 `/day` 是否引入回归。

- [ ] **Step 6: 确认改动范围**

Run:

```bash
git status --short
```

Expected: 仅出现 `backend/Holiday.py`、`main.py`、`README.md` 的修改（以及本计划文档本身）；不应出现新增依赖文件。

- [ ] **Step 7: 停止服务并清理测试进程**

停止本任务启动的 uvicorn 进程；不要保留后台服务。

---

## Self-Review

**Spec coverage:**
- `GET /day?date=YYYY-MM-DD`：Task 2。
- 3 个布尔响应字段：Task 1、Task 2。
- `isWeekend` 纯星期判定、补班日也 true：Task 2 的 `target_date.weekday() >= 5`。
- 数据流「已加载则直接查询、未加载才 `crawl()`」：Task 2 Step 5 的 `fail_crawl` 守卫用例。
- 未收录年份返回 200 且两个 false：Task 2 的 smoke case `2027-01-01`。
- 非法/不存在/缺失日期 422：Task 2 Step 5（`2026-13-01`、`2026-02-30`、无参）、Task 4 Step 4。
- 数据源失败 500：Task 2 Step 5。
- 首页 usage 与 README：Task 2 Step 3、Task 3。
- `/calendar` 与 `Worker.check()` 不变：Global Constraints、Task 4 Step 5。
- 改动范围与「不新增依赖」：Task 4 Step 6 的 `git status --short`。

**Placeholder scan:** 无 TBD/TODO；所有代码步骤均给出完整代码与命令。

**Type consistency:** `DayInfo` 的三个字段在模型、路由返回与验证用例中命名一致；`Worker.check` 仍返回 `HolidayResult`，路由只读取 `isHoliday`、`isCompDay`（`HolidayResult.name` 为必填，但路由不读取、不修改）。

**环境核对（计划编写时实测）：** Python 3.12.3、FastAPI 0.133.0、Pydantic 2.12.5、httpx 0.28.1、uv 0.7.13；`pytest` 未安装，故不新增 `tests/` 套件；Pydantic 2 对 `2026-13-01`、`2026-02-30` 均判为非法日期。
