# Agent 自迭代修订治理设计

## 1. 目标

把“AI 自迭代”收敛为可控的模组修订流水线：

- AI 可以提出修订建议（prompt / skill / memory 策略）
- AI **不能直接落盘或发布**
- 所有改动必须经过人工审计与审批
- 改动结果纳入模组版本体系，支持回滚

---

## 2. 核心原则

- 最小权限：Agent 仅有 `propose` 权限，无 `write/apply/publish` 权限
- 人工把关：审批前只读，不改运行态
- 全链路留痕：从“哪一局”到“改了什么”必须可追溯
- 可回滚：每次应用都保留快照与版本记录

---

## 3. 流程（建议）

1. 对局结束 -> `agent_report`
2. `agent_critic` 产出评分与建议
3. `agent_revision_propose` 生成“修订提案”（结构化 patch plan）
4. 进入后台“修订队列（Pending）”
5. 人工审阅 diff + 风险说明
6. 审批通过后应用到“模组草稿”
7. 验证通过再发布版本

---

## 4. 权限隔离模型

## 4.1 角色

- `player`: 只能触发自动测试，不可审批
- `agent`: 只能生成提案，不可写文件
- `reviewer/admin`: 可审批、驳回、应用、回滚

补充约束（按你的需求）：
- 玩家端与后台端都可触发“自迭代提案”。
- 但提案目标必须是当前身份有权限操作的模组。
- 游客/普通玩家不能直接修订 `default` 模组，必须先另存为本地模组。
- 工坊模组仅原作者（或管理员）可执行修订应用。

## 4.2 操作白名单（首期）

允许提案目标（仅提案，不直接写入）：
- `prompts/system/*.md`
- `prompts/skills/*.md`
- `prompts/world/*.md`
- `events/event_skeletons*.json`（仅局部字段）
- memory 策略配置文件（单独白名单）

禁止：
- 账号/权限/路由代码
- 执行脚本、系统配置、删除型操作
- 跨目录写入

---

## 5. 数据结构（提案）

建议新增 `data/users/{user_id}/revisions/`：

- `queue/{proposal_id}.json`：待审提案
- `applied/{proposal_id}.json`：已应用记录
- `rejected/{proposal_id}.json`：驳回记录

`proposal` 示例字段：

```json
{
  "proposal_id": "rev-20260324-xxxx",
  "created_at": "2026-03-24T12:34:56Z",
  "source_run": {
    "visitor_id": "xxx",
    "turn_count": 18,
    "report_id": "rep-xxx"
  },
  "scope": "mod_revision",
  "target_mod_id": "my_mod_v2",
  "risk_level": "medium",
  "summary": "优化手机消息触发频率与关键事件门槛反馈",
  "changes": [
    {
      "file": "prompts/skills/wechat_monitor.md",
      "op": "update",
      "reason": "减少无效消息，提升信息价值",
      "diff_preview": "...",
      "patch_text": "..."
    }
  ],
  "validator": {
    "schema_ok": true,
    "policy_ok": true,
    "blocked_rules": []
  },
  "status": "pending"
}
```

---

## 6. 接口草案

## 6.1 Agent 侧（仅生成）

- `POST /api/game/agent/revision/propose`
  - 入参：`report + critic + history_tail + final_state + target_mod_id`
  - 出参：结构化提案（不落盘时）或 `proposal_id`（落队列时）

## 6.2 Admin 侧（审计）

- `GET /api/admin/revisions/list?status=pending`
- `GET /api/admin/revisions/{proposal_id}`
- `POST /api/admin/revisions/{proposal_id}/approve`
- `POST /api/admin/revisions/{proposal_id}/reject`
- `POST /api/admin/revisions/{proposal_id}/apply_to_draft`
- `POST /api/admin/revisions/{proposal_id}/rollback`

---

## 7. 审计要求

每条提案必须包含：

- 来源：哪次对局、哪份 report/critic
- 改动：文件、字段、前后差异
- 原因：为何改、预期收益
- 风险：潜在副作用
- 审批信息：审批人、时间、结论

所有审计日志写入现有 `audit` 通道，动作名建议：
- `agent_revision_propose`
- `agent_revision_approve`
- `agent_revision_reject`
- `agent_revision_apply`
- `agent_revision_rollback`

---

## 8. 前端开关设计

在 `Agent Debug` 中新增：

- `Self-Iterate`（已实现）：是否做 critic
- `Revision Propose`（已实现）：是否在 critic 后自动生成“提案草稿”

建议默认：
- `Self-Iterate`: OFF
- `Revision Propose`: OFF

并在 UI 明确标注：**“仅生成提案，不会自动改文件”**。

---

## 11. 长期记忆并入模组向量库（新增）

目标：
- AI 自迭代不仅产出文本改动提案，也可产出长期记忆候选；
- 候选记忆按 `target_mod_id` 归档，写入“模组自带向量库”。

建议机制：
- `proposal.memory_candidates` 保存候选记忆（content/importance/tags）。
- 审批通过后再执行“入库动作”，禁止提案阶段直接入库。
- 检索时按 `active_mod_id` 过滤，防止不同模组记忆串扰。

元数据建议：
- `memory_type=mod_long_term`
- `mod_id=<target_mod_id>`
- `proposal_id=<proposal_id>`
- `approved_by=<reviewer_id>`

---

## 9. 风险与防护

- 风险：AI 提案偏离模组主题  
  防护：提案需附“主题一致性评分”，低分默认阻断。

- 风险：提案过大难审  
  防护：单提案最多 N 个文件、每文件最大 patch 字数限制。

- 风险：错误应用破坏运行态  
  防护：只能应用到草稿模组；应用前自动快照；支持一键回滚。

---

## 10. 分期实施建议

P0：
- 提案结构定义 + 队列落盘 + 后台列表只读

当前进度（2026-03-24）：
- 已完成：`/api/game/agent/revision/propose`（提案入队 + 权限校验）
- 已完成：玩家端 `Agent Debug` 开关链路（Self-Iterate + Revision Propose）
- 已完成：提案包含 `memory_candidates`（长期记忆候选）
- 已完成：后台修订队列基础管理接口  
  - `GET /api/admin/revisions`  
  - `GET /api/admin/revisions/{proposal_id}`  
  - `POST /api/admin/revisions/{proposal_id}/approve`  
  - `POST /api/admin/revisions/{proposal_id}/reject`  
  - `POST /api/admin/revisions/{proposal_id}/apply_memory`
- 已完成：后台新增“修订队列”Tab（审计/审批/入长期记忆）

P1：
- 审批/驳回 + 人工应用到草稿 + 基础回滚

当前进度（2026-03-24，追加）：
- 已完成：`apply_to_draft`（将提案变更写入目标模组草稿）
- 已完成：`rollback`（按提案备份恢复草稿内容）
- 已完成：后台“修订队列”Tab 提供按钮操作  
  - 通过 / 驳回 / 应用到草稿 / 入长期记忆 / 回滚
- 已升级：`apply_to_draft` 以结构化 `content_after` 为准；缺少该字段的变更会被跳过并返回统计。

P2：
- 自动策略优化（多次对局聚合后再提案）
- 提案质量评分与优先级调度

当前进度（2026-03-24，P2-1）：
- 已完成：提案质量信号自动计算（`quality_score/priority`）
- 已完成：提案校验信息 `validator`（`schema_ok/policy_ok/blocked_rules/structured_ratio`）
- 已完成：后台修订队列展示质量信号，支持快速筛选可应用提案

当前进度（2026-03-24，P2-2）：
- 已完成：多次对局聚合信号接入提案校验（`run_sample_count/common_issues`）
- 已完成：按目标模组归档对局报告摘要（用于后续提案聚合）
- 已完成：低样本提案标记规则（`insufficient_run_samples`）

当前进度（2026-03-24，P2-3）：
- 已完成：`apply_to_draft` 质量门禁（质量分/样本数/规则阻断）
- 已完成：支持管理员备注 `force_apply` 强制放行（保留审计记录）
- 已完成：后台修订队列对门禁状态进行可视化提示
- 已完成：后台提供“强制应用”显式按钮（二次确认后提交 `force_apply`）

当前进度（2026-03-24，P2-4）：
- 已完成：提案去重信号（`validator.duplicate_proposal/duplicate_with`）
- 已完成：提案合并建议信号（`validator.merge_suggestion/merge_with`）
- 已完成：后台修订队列展示“重复提案/合并建议”提示，便于人工审计收敛

当前进度（2026-03-24，P2-5）：
- 已完成：后台修订队列增加“按主题聚合 / 平铺列表”切换
- 已完成：按 `target_mod_id + 摘要主题` 聚合显示，便于大批量提案审阅

当前进度（2026-03-24，P2-6）：
- 已完成：聚合组级批处理操作（待审队列支持“整组通过 / 整组驳回”）
- 已完成：批处理复用现有单条审计链路，保持审批与审计一致性

当前进度（2026-03-24，P2-7）：
- 已完成：聚合组级“智能建议”提示（建议整组驳回/优先通过/人工复核）
- 已完成：基于组内重复占比与质量分布给出轻量决策参考，降低人工筛选成本

当前进度（2026-03-24，P2-8）：
- 已完成：聚合组级批处理前置预览确认（显示条数与 proposal_id 预览）
- 已完成：组级“整组通过/驳回”误操作保护
