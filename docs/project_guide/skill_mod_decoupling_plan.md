# Skill 与模组市场解耦计划（进度）

## 已完成（P1-1）
- 后端新增接口：
  - `GET /api/skills/profile`
  - `POST /api/skills/profile`
  - `POST /api/skills/profile/resolve`
- `PromptManager` 已接入 profile 覆盖逻辑（含按 `mod_id` resolve）。

## 已完成（P1-2）
- 编辑器技能面板改为优先走 `skill_profile`（非后台预设模式）。
- 保留后台预设编辑模式继续编辑 `system/mod_features.json`（兼容老流程）。
- 新增“迁移旧开关”按钮：可把 `system/mod_features.json` 的技能开关与手机开关迁移到 `skill_profile`。

## 下一步（P1-3）
- 在技能面板加“当前 resolve 结果来源”小标签（profile/mod override/default）。
- 加一次性迁移标记，避免重复迁移。
- 在模组市场卡片中把 `enabled_skills` 文案改为 `recommended_skills`（弱关联展示）。

## 当前进度（2026-03-24，P1-3）
- 已完成：`/api/skills/profile/resolve` 返回来源追踪字段：
  - `phone_source`
  - `skill_sources`
- 已完成：编辑器技能开关栏展示来源标签（`default / mod / profile / profile(mod)`）。
- 已完成：技能面板可直接观测“当前开关是被谁覆盖的”，便于调试解耦后的优先级。

## 当前进度（2026-03-24，P2-1）
- 已完成：模组元数据新增 `recommended_skills`（优先读取 `mod_features.recommended_skills`，缺失时兼容回退旧字段）。
- 已完成：模组市场详情页文案改为“推荐技能”，并优先展示 `recommended_skills`。

## 当前进度（2026-03-24，P2-2）
- 已完成：编辑器技能工具栏新增“推荐技能”可视化编辑区（与运行时开关分离）。
- 已完成：支持将推荐技能写回 `system/mod_features.json` 的 `recommended_skills` 字段。
