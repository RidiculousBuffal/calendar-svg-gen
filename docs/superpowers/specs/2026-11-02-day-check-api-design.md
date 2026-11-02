# 日期状态查询接口设计（GET /day）

## 背景与目标

现有服务只提供 `GET /calendar` 月历 SVG，节假日与调休补班的判定逻辑位于 `backend/Worker.py` 的 `Worker.check()`。本次新增一个按日期查询的接口，让调用方能够确认某一天是否为法定节假日、调休补班日或双休日，并据此判断当天是否需要上班。

## 已确认需求

- 接口接收 `yyyy-mm-dd` 格式的日期，例如 `2026-10-01`。
- 返回 3 个布尔字段：是否节假日、是否调休补班、是否双休日。
- 调用方可以通过这三个字段确定当天是否需要上班。
- 数据源为 `https://www.shuyz.com/githubfiles/china-holiday-calender/master/holidayAPI.json`，后续年份数据由数据源更新。
- 若查询年份暂未收录，不报错：节假日与调休补班返回 `false`，双休日仍按星期正常判定。

## 接口契约

```
GET /day?date=2026-10-01
```

查询参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `date` | string（ISO 日期） | 是 | 日期，格式 `YYYY-MM-DD`，如 `2026-10-01` |

成功响应 `200 application/json`：

```json
{
  "isHoliday": false,
  "isCompDay": false,
  "isWeekend": false
}
```

响应字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `isHoliday` | boolean | 是否为法定节假日（放假日期范围内，包含与周末重叠的日期） |
| `isCompDay` | boolean | 是否为调休补班日（需上班的周末或调休工作日） |
| `isWeekend` | boolean | 是否为周六或周日。纯按日历星期判定，补班日也照常为 `true` |

## 字段语义与上班判定

三个字段是相互独立的事实：

- 普通工作日：`isHoliday=false`、`isCompDay=false`、`isWeekend=false`
- 普通周末：`isHoliday=false`、`isCompDay=false`、`isWeekend=true`
- 法定节假日（工作日）：`isHoliday=true`、`isCompDay=false`、`isWeekend=false`
- 法定节假日（与周末重叠）：`isHoliday=true`、`isCompDay=false`、`isWeekend=true`
- 调休补班日（通常是周末）：`isHoliday=false`、`isCompDay=true`、`isWeekend=true`

当天是否需要上班由调用方按以下公式判定：

```
isWorkday = isCompDay || (!isHoliday && !isWeekend)
```

接口不额外返回 `isWorkday` 字段，保持返回对象只有 3 个字段。

## 数据流与缓存

1. 路由收到请求后，检查全局 `_worker.holidays` 是否已加载。
2. 若未加载，调用 `Worker.crawl()` 拉取并解析数据源，结果保存到 `_worker.holidays`。
3. 调用 `Worker.check(year, month, day)` 获取 `isHoliday` 与 `isCompDay`。
4. 路由根据 `date.weekday() >= 5` 计算 `isWeekend`。
5. 组合为响应模型返回。

说明：

- `Worker.check()` 的签名和现有返回值保持不变，`/calendar` 不受影响。
- 若年份未收录，`Worker.check()` 已返回 `isHoliday=false`、`isCompDay=false`，路由继续正常计算 `isWeekend`。
- 多个首次请求并发时可能重复拉取数据，但不影响结果正确性；本次不引入额外锁或 TTL 缓存。
- `Worker.holidays` 为 `None` 时不能直接调用 `check()`，因此路由必须先完成加载。

## 错误处理

| 场景 | 响应 |
|------|------|
| 缺少 `date` 参数 | `422`，由 FastAPI 参数校验返回 |
| `date` 格式非法或日期不存在（如 `2026-13-01`、`2026-02-30`） | `422`，由 FastAPI/Pydantic 日期解析返回 |
| 数据源拉取或解析失败 | `500`，`detail` 为 `节假日数据获取失败: <原因>` |
| 查询年份未收录 | `200`，`isHoliday=false`、`isCompDay=false`，`isWeekend` 正常计算 |

## 代码改动

1. `backend/Holiday.py`
   - 新增响应模型 `DayInfo`，包含 `isHoliday`、`isCompDay`、`isWeekend` 三个必填布尔字段。

2. `main.py`
   - 新增 `GET /day` 路由，使用 `target_date: date = Query(..., alias="date")` 避免参数名与 `datetime.date` 类型名冲突。
   - 懒加载 `_worker.holidays`，组合 `Worker.check()` 与 `weekday()` 结果。
   - 在 `/` 首页的 `usage` 中补充 `GET /day?date=2026-10-01`。

3. `README.md`
   - 在现有月历接口说明后补充日期查询接口的示例。

## 验证用例

| 日期 | 预期 `isHoliday` | 预期 `isCompDay` | 预期 `isWeekend` | 预期上班 |
|------|------------------|------------------|------------------|----------|
| `2026-10-01`（国庆，周四） | `true` | `false` | `false` | 否 |
| `2026-10-10`（国庆补班，周六） | `false` | `true` | `true` | 是 |
| `2026-10-11`（周日） | `false` | `false` | `true` | 否 |
| `2026-10-12`（周一） | `false` | `false` | `false` | 是 |
| `2026-02-14`（春节补班，周六） | `false` | `true` | `true` | 是 |
| `2026-02-15`（春节，周日） | `true` | `false` | `true` | 否 |
| `2027-01-01`（周五，年份未收录） | `false` | `false` | `false` | 是 |

补充校验：

- `GET /day` 返回 `422`。
- `GET /day?date=2026-13-01` 返回 `422`。
- 数据源不可用时返回 `500`，且 `detail` 包含失败原因。

## 非目标

- 不新增批量日期查询接口。
- 不返回节假日名称、放假区间、调休说明等额外字段。
- 不修改 `/calendar` 的渲染逻辑和 `Worker.check()` 的现有行为。
- 不引入定时刷新、持久化缓存或数据库。
