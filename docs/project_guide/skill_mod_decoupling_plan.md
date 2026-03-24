# Skill 与模组市场解耦改造方案（分期版）

## 1. 目标与结论

目标：把“内容分发（模组）”与“能力分发（skill）”拆成两条独立链路，运行时再装配。

结论：对本项目是明显收益项，建议执行。  
原因：
- 模组应聚焦剧情内容（角色/事件/世界观/资源）
- skill 应聚焦运行能力（提示注入/工具调用/策略）
- 两者独立后，权限、审计、复用、回滚都更清晰

---

## 2. 当前耦合点（现状）

当前模型里，模组记录会携带 `enabled_skills`，且从模组 `content` 推导：
- `Server/src/services/mod_service.py`：`extract_enabled_skills`、`normalize_*_record`、`build_*_record`

这会导致：
- 模组发布/下载行为隐式影响 skill 开关
- “内容更新”与“能力更新”混在一次变更里，审计粒度不清晰
- 市场侧难解释“这个模组到底改了剧情，还是改了系统行为”

---

## 3. 目标架构（解耦后）

### 3.1 概念边界

- 模组（Mod Package）
  - 只描述内容资产
  - 可带“推荐 skill 清单”（advisory）
  - 不拥有 skill 实际开关状态

- Skill 配置（Skill Profile）
  - 用户级/存档级配置
  - 负责 enable/disable、参数、优先级
  - 可独立导入导出、可审计

### 3.2 运行时装配

开局时由 Runtime Resolver 组合：
1. 当前活动模组内容
2. 当前用户（或存档）skill 配置
3. 安全策略（黑白名单、管理员限制）

输出最终执行集 `resolved_skills`，供引擎注入。

---

## 4. 数据模型改造

## 4.1 模组记录字段调整

保留：
- `recommended_skills: string[]`（可选，给 UI 推荐）

弱化/迁移：
- `enabled_skills` 从“模组权威字段”降级为“兼容字段”

后续阶段可废弃：
- 模组记录中的强绑定 skill 开关语义

## 4.2 新增 skill profile（用户侧）

建议新增文件：
- `Server/data/users/{user_id}/skill_profile.json`

建议结构：
```json
{
  "version": 1,
  "updated_at": "2026-03-24T20:00:00",
  "global": {
    "phone_system_enabled": true
  },
  "skills": {
    "character_roster": { "enabled": true, "priority": 100 },
    "relationship_matrix": { "enabled": true, "priority": 110 },
    "secret_note": { "enabled": false, "priority": 200 }
  },
  "per_mod_overrides": {
    "kindergarten_theme_v1": {
      "phone_system_enabled": false,
      "skills": {
        "academic_world": { "enabled": false }
      }
    }
  }
}
```

---

## 5. API 与前端改造

## 5.1 新增接口（建议）

- `GET /api/skills/profile`
- `POST /api/skills/profile`（整体保存）
- `POST /api/skills/profile/resolve`（输入 mod_id，返回 runtime resolved_skills）

## 5.2 模组接口调整（兼容期）

- `library/workshop` 列表仍返回 `enabled_skills`（兼容旧 UI）
- 新增返回 `recommended_skills`
- 前端逐步改为展示“推荐 skill”而非“绑定开关”

## 5.3 前端页面调整

- 模组市场页：
  - 展示“推荐 skill 标签”
  - 不直接改 skill 开关

- Skill 中心页：
  - 成为唯一 skill 开关与参数管理入口
  - 提供“按模组应用推荐配置（一次性）”按钮

---

## 6. 权限与审计

审计动作拆分：
- 模组变更：`mod_update` / `mod_publish`
- skill 变更：`skill_profile_update`
- 运行装配：`skill_resolve_runtime`

权限原则：
- 游客可改自己的 skill profile（仅影响自己）
- 默认模板只读仍保持
- 管理员可限制高风险工具型 skill

---

## 7. 分期实施（低风险）

### P1（推荐先做）
- 引入 `skill_profile.json`
- 新增 `skills/profile` 接口
- Runtime 改为“模组 + profile 装配”
- 保留旧字段 `enabled_skills` 仅做回显兼容

### P2
- 模组市场页改为展示 `recommended_skills`
- Skill 中心接管全部开关操作
- 模组发布逻辑仅记录推荐项，不写真实开关状态

### P3
- 清理 `enabled_skills` 的强绑定语义
- 完成迁移脚本（旧数据 -> profile）
- 文档与后台审计口径统一

---

## 8. 迁移策略

首次升级时：
1. 读取当前用户最近活动模组的 `enabled_skills`
2. 生成初始 `skill_profile.json`
3. 写入 `migration_meta` 标记，避免重复迁移

回滚策略：
- 保留原模组记录字段不删除
- profile 读写异常时回退到旧逻辑（只读兼容）

---

## 9. 验收标准

- 模组发布/下载不再直接改变 skill 开关状态
- skill 开关只在 Skill 中心生效并可审计
- 开局时可稳定拿到 `resolved_skills`
- 旧模组仍可运行，不出现能力丢失

---

## 10. 建议下一步

按 P1 开工，先做“后端 profile + runtime resolver”，前端只加最小入口，不做大改版式。  
这样我们可以在一到两轮内完成核心解耦，再逐步清理历史耦合字段。

---

## 11. 当前进度（2026-03-24）

P1 已完成（第一步）：
- 已新增 `skill_profile` 接口：
  - `GET /api/skills/profile`
  - `POST /api/skills/profile`
  - `POST /api/skills/profile/resolve`
- 已在 `PromptManager` 接入 profile 读取与合并逻辑：
  - `get_enabled_skills(context?)` 支持 profile 全局覆盖与按 `mod_id` 覆盖
  - `is_phone_system_enabled(context?)` 支持 profile 覆盖
- 已在前端 API 封装新增对应调用（供后续 UI 接入）

下一步（P1 第二步）：
- 在技能中心 UI 接入 profile 的读取/保存/按模组 resolve 预览
- 增加“从当前模组迁移初始化 profile”的一次性迁移入口（兼容旧数据）
