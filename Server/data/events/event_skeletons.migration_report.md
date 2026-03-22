# 旧事件 -> 骨架事件 迁移报告

- 生成时间: `2026-03-22 01:45:34`
- 事件目录: `/Users/xuzi/Downloads/AI_Dialogue/Server/data/events`
- 输出文件: `/Users/xuzi/Downloads/AI_Dialogue/Server/data/events/event_skeletons.generated.json`

## 总览

- CSV 文件数: `5`
- 读取事件行: `47`
- 空 Event_ID 跳过: `0`
- key 事件: `20`
- daily 事件: `27`

## 按文件统计

- `00_开局剧情.csv`: `1`
- `01_固定剧情.csv`: `11`
- `02_通用随机池.csv`: `22`
- `03_角色专属.csv`: `8`
- `04_条件触发.csv`: `5`

## 自动迁移提示

- `原事件无显式触发条件，已按 chapter/day_min 与事件类型做保守映射。` x `39`
- `触发条件含 hygiene/卫生，已降级映射到 legacy flags，请人工复核。` x `1`

## 样例（前5条）

- `evt_opening` | `key` | priority `88`
  - title: 大学生活开启
  - triggers: {"day_min": 1}
  - options: [{"id": "evt_opening_support", "attitude": "支持", "effects": {"dorm_mood_delta": 2}, "text_hint": "支持并推进：欢迎来到大学。这是一段充满挑战与机遇"}, {"id": "evt_opening_neutral", "attitude": "中立", "effects": {"dorm_mood_delta": 0}, "text_hint": "保留意见：欢迎来到大学。这是一段充满挑战与机遇"}, {"id": "evt_opening_avoid", "attitude": "回避", "effects": {"dorm_mood_delta": -2}, "text_hint": "先回避冲突：欢迎来到大学。这是一段充满挑战与机遇"}]
- `evt_ch4_boss_job` | `key` | priority `80`
  - title: 散伙饭晒Offer
  - triggers: {"day_min": 22}
  - options: [{"id": "evt_ch4_boss_job_support", "attitude": "支持", "effects": {"dorm_mood_delta": 2}, "text_hint": "支持并推进：最后的散伙饭上。有人拿到了大厂Off"}, {"id": "evt_ch4_boss_job_neutral", "attitude": "中立", "effects": {"dorm_mood_delta": 0}, "text_hint": "保留意见：最后的散伙饭上。有人拿到了大厂Off"}, {"id": "evt_ch4_boss_job_avoid", "attitude": "回避", "effects": {"dorm_mood_delta": -2}, "text_hint": "先回避冲突：最后的散伙饭上。有人拿到了大厂Off"}]
- `evt_ch4_photo` | `key` | priority `80`
  - title: 毕业照C位之争
  - triggers: {"day_min": 22}
  - options: [{"id": "evt_ch4_photo_support", "attitude": "支持", "effects": {"dorm_mood_delta": 2}, "text_hint": "支持并推进：拍毕业照时，有人想站在C位，但大家觉"}, {"id": "evt_ch4_photo_neutral", "attitude": "中立", "effects": {"dorm_mood_delta": 0}, "text_hint": "保留意见：拍毕业照时，有人想站在C位，但大家觉"}, {"id": "evt_ch4_photo_avoid", "attitude": "回避", "effects": {"dorm_mood_delta": -2}, "text_hint": "先回避冲突：拍毕业照时，有人想站在C位，但大家觉"}]
- `evt_ch4_thesis` | `key` | priority `80`
  - title: 毕业论文查重
  - triggers: {"day_min": 22}
  - options: [{"id": "evt_ch4_thesis_support", "attitude": "支持", "effects": {"dorm_mood_delta": 2}, "text_hint": "支持并推进：大四下学期。有人的论文查重率高达80"}, {"id": "evt_ch4_thesis_neutral", "attitude": "中立", "effects": {"dorm_mood_delta": 0}, "text_hint": "保留意见：大四下学期。有人的论文查重率高达80"}, {"id": "evt_ch4_thesis_avoid", "attitude": "回避", "effects": {"dorm_mood_delta": -2}, "text_hint": "先回避冲突：大四下学期。有人的论文查重率高达80"}]
- `evt_ch3_boss_baoyan` | `key` | priority `78`
  - title: 保研名额争夺战
  - triggers: {"day_min": 15}
  - options: [{"id": "evt_ch3_boss_baoyan_support", "attitude": "支持", "effects": {"dorm_mood_delta": 2}, "text_hint": "支持并推进：保研边缘。你和另一个室友分数极其接近"}, {"id": "evt_ch3_boss_baoyan_neutral", "attitude": "中立", "effects": {"dorm_mood_delta": 0}, "text_hint": "保留意见：保研边缘。你和另一个室友分数极其接近"}, {"id": "evt_ch3_boss_baoyan_avoid", "attitude": "回避", "effects": {"dorm_mood_delta": -2}, "text_hint": "先回避冲突：保研边缘。你和另一个室友分数极其接近"}]

## 后续建议

- 先抽查 key 事件的 `triggers`，优先修正 `flags_all_true` 的 legacy 条件。
- 再补充专属角色缺失项，避免角色专属事件进入全局池。
- 验证通过后可把 `event_skeletons.generated.json` 改名为 `event_skeletons.json` 启用。
