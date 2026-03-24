# 模组作者 Skill 最佳实践

## 1. 何时用 Skill，何时写事件

- 用 Skill：跨事件复用的“能力规则”
  - 例如：关系里程碑提示、秘密纸条机制、手机消息触发策略、语气风格包
- 写事件（CSV / 骨架）：具体剧情与分支内容
  - 例如：某次寝室冲突、某次约会邀约、某次课堂风波

一句话判断：
- 能在多个事件里重复用的逻辑 => Skill
- 只属于某个剧情片段的内容 => 事件

---

## 2. Skill 编写建议（避免拖慢与跑偏）

- 短：优先 8~20 行约束，不要写成长篇世界观
- 硬约束优先：先写“必须/禁止”，再写风格偏好
- 可验证：尽量给可观测信号（例如“每 2~3 回合最多 1 条手机消息”）
- 不重复：不要把角色大设定再抄一遍（角色信息已由角色/世界模块提供）

推荐结构：

1. 目标（这个 Skill 解决什么）
2. 触发条件（什么时候生效）
3. 输出约束（允许做什么，不允许做什么）
4. 失败回退（不满足条件时怎么处理）

### 2.1 建议使用结构化元数据（Front Matter）

自定义 `skills/*.md` 现在支持前置元数据，推荐格式：

```md
---
id: dorm_whisper_note
name: 寝室小道消息
description: 在合适时机补一条“短消息风格”的八卦旁白
enabled: true
priority: 90
when: always
target: general
tags: [custom, flavor]
created_at: 2026-03-24T10:00:00Z
---

（这里写 skill 正文约束）
```

字段说明：
- `id`: 稳定标识，建议只用小写字母/数字/`_`/`-`
- `name`: 展示名称
- `description`: 一行简介
- `enabled`: 是否启用（`false` 时不注入）
- `priority`: 加载顺序（数字越小越靠前）
- `when`: 生效时机（`always` / `daily_event` / `key_event` / `transition`）
- `target`: 面向模块（如 `general`/`phone`/`relationship`，仅作语义标注）
- `tags`: 标签数组，便于后续筛选

兼容性：
- 没有 front matter 的旧 skill 仍可用，会按“启用 + always”处理。

---

## 3. 与 function calling 的配合

- 能结构化执行的动作，优先 tool：
  - `phone_enqueue_message`
  - `memory_add_tag`
  - `relationship_apply_delta`
- Skill 负责“何时调用/调用原则”
- 事件负责“剧情内容”

不要做的事：
- 在 Skill 中要求模型直接写 legacy wechat 文本命令
- 在 Skill 中直接篡改系统状态（应通过状态工具提议，系统裁决）

---

## 4. 推荐默认技能组合

- 基础稳定包：
  - `academic_world`
  - `character_roster`
  - `relationship_matrix`
  - `slang_dict`
- 玩法增强包（按需求开）：
  - `relationship_milestone`
  - `secret_note`
- 自定义扩展：
  - `user_skills`

---

## 5. 常见反模式

- Skill 里写具体剧情台词（应写到事件）
- 一个 Skill 同时做“世界观 + 关系规则 + 手机系统”（应拆分）
- 每回合都强制发手机消息（会显得机械且拖慢）
- 把“可能触发”写成“必须触发”（破坏演出自然度）

---

## 6. 发布前自查清单

- 是否明确了“触发条件”与“禁止行为”
- 是否避免重复注入世界观大段文本
- 是否定义了失败回退（不满足条件时输出为空/跳过）
- 是否在调试面板验证了来源分布（tool / fallback / legacy）
- 是否与模组主题一致（例如幼儿园主题禁用大学宿舍术语）
