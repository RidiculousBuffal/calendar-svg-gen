![calendar](https://calendar-svg.ridiculousbuffal.com/calendar)

## 接口说明

- **单日状态查询**: `GET /day?date=2026-02-17`（默认查询今天）
- **当前月历 SVG**: `GET /calendar`
- **指定年月 SVG**: `GET /calendar?year=2026&month=2`
- **交互式文档**: `GET /docs`

### `/day` 返回示例

```json
{
  "date": "2026-02-17",
  "isHoliday": true,
  "isWeekend": false,
  "holidayName": "春节",
  "isWorkday": false,
  "isCompDay": false
}
```

#### 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `date` | string | 查询日期（`YYYY-MM-DD`） |
| `isHoliday` | boolean | 是否是节假日（放假） |
| `isWeekend` | boolean | 是否是周末（周六、周日） |
| `holidayName` | string \| null | 是什么节假日（如“春节”；调休补班标注如“春节补班”；普通日为 `null`） |
| `isWorkday` | boolean | 是否上班（工作日或调休补班为 `true`，节假日或周末为 `false`） |
| `isCompDay` | boolean | 是否是调休补班日 |
