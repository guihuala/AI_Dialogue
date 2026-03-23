# Skill 与模组分离改造计划

## 1. 目标与结论

本项目建议采用：**模组与 skill 分离**，但允许模组声明启用 skill（`enabled_skills`）。

- 模组：世界观、角色、事件、素材、提示词风格
- skill：可复用能力（手机消息、记忆标签、状态写入、辅助检索）

核心收益：
- 降低模组重复维护成本
- 提高系统可控性（权限、限流、审计）
- 为 function calling 引入提供稳定边界

---

## 2. 现状（简要）

- 当前 `skills/*.md` 主要作为提示词片段拼接，属于“文本注入型 skill”
- 模组可覆盖 prompt 与事件文件，导致“能力定义”和“世界内容”耦合
- 下载副本/工坊链路已增强，但能力层仍未独立建模

---

## 3. 目标架构

### 3.1 目录与配置

- 新增平台级 skill 注册表（示例）：
  - `Server/data/skills/registry.json`
- 每个 skill 一个定义文件（示例）：
  - `Server/data/skills/phone_messaging.json`
  - `Server/data/skills/memory_tagger.json`
- 模组 manifest 新增：
  - `enabled_skills: string[]`
  - `disabled_skills: string[]`（可选）

### 3.2 运行时职责

- PromptManager：只负责读取“已启用 skill”对应的提示词片段
- Tool/Function 层：只暴露白名单函数（按 skill 开关）
- GameEngine：不直接依赖模组里散落的“能力规则文本”

---

## 4. 分期计划（建议）

## P0（低风险准备）

目标：不改玩法，只加结构。

1. 新增 skill 注册表与加载器（只读）
2. 在 `manifest` 中接受 `enabled_skills` 字段（不强依赖）
3. 在 debug 面板增加“本局启用 skill 列表”显示

验收：
- 不改现有模组也能跑
- 新字段缺失时自动回退默认技能集

---

## P1（分离提示词型 skill）

目标：把“能力提示词”从模组正文中抽出来，改为按 skill 启用。

1. 将现有 `skills/*.md` 迁移为 skill 定义引用
2. Prompt 拼接改为：
   - 平台默认 skills
   - 模组 `enabled_skills` 覆盖
3. 模组编辑器增加 skill 开关（基础版）

验收：
- 同一 skill 可在多个模组复用
- 模组改世界观不再必须复制粘贴能力规则

---

## P2（手机系统先行 function calling）

目标：先把“手机消息”从纯文本控制改为函数调用。

1. 新增函数（建议）：
   - `phone.enqueue_message(chat, sender, content, priority?)`
2. AI 输出策略：
   - 对话正文仍由 JSON 文本返回
   - 手机消息走工具调用，不再靠 effects 字符串拼命令
3. 服务端统一校验：
   - 长度限制
   - sender 白名单
   - 脏词/注入过滤

验收：
- 手机消息稳定落库
- 不影响主对话速度（每回合最多 0-1 次调用）

---

## P3（状态写入能力工具化）

目标：把高风险状态变更变成可审计函数层。

1. 可选函数：
   - `memory.add_tag(tag, target?, ttl?)`
   - `relationship.apply_delta(target, trust, tension, intimacy)`
2. 保留系统侧最终裁决（AI 只能“提议”，系统可拒绝）
3. 全量审计日志（谁触发、何时触发、参数）

验收：
- 状态漂移减少
- 回放和调试更清晰

---

## 5. 兼容与迁移策略

1. 先“兼容旧模组”，再“鼓励新模组”
2. 若模组无 `enabled_skills`：
   - 自动按默认技能集运行
3. 若 skill 不存在：
   - 记录 warning，不阻断开局
4. 保留旧 `effects` 解析一个版本周期（过渡期）

---

## 6. 风险与控制

### 风险
- 工具调用增加时延
- skill 配置过多导致调试复杂
- 模组作者对新字段不熟悉

### 控制
- 严格限制每回合工具调用次数（建议 <=1）
- 先手机系统试点，再扩展
- 编辑器提供“技能模板预设”

---

## 7. 优先级建议（按你的限额节奏）

1. **先做 P0 + P1（低风险高收益）**
2. 再做 **P2 手机系统 function calling**（最值得）
3. 最后看节奏推进 P3

---

## 8. 预计工作量（粗估）

- P0：0.5~1 天
- P1：1~2 天
- P2：1~2 天（含前后端联调）
- P3：2 天+

---

## 9. 下一步可直接开工项

如果按“最小可交付”推进，建议下一个开发包是：

- 新增 `enabled_skills` 字段读取
- 增加 skill 注册表 + 默认技能集
- debug 面板展示本局 skills

这一步完成后，就能无痛进入手机系统 function calling 试点。
