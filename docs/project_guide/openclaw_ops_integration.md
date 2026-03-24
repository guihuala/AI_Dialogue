# OpenClaw 运营后台接入方案（部署版）

## 1. 目标

将网站部署到服务器后，引入 OpenClaw 作为“运营助手”管理后台流程，同时保证：
- 权限最小化
- 所有操作可审计
- 高风险动作可回滚
- 不影响普通玩家体验

---

## 2. 角色与权限

建议拆成三类身份：

1. `super_admin`（人工）
- 全权限
- 可执行高风险动作（强制应用、回滚、删除）

2. `ops_admin`（人工运营）
- 可审提案、可发布审核结论
- 不可直接覆盖默认模板

3. `openclaw_bot`（机器账号）
- 只允许调用白名单运营接口
- 默认只做“建议/预执行”
- 高风险动作必须人工确认（双闸门）

---

## 3. OpenClaw 接口白名单（已落地第一版）

允许：
- `GET /api/openclaw/session`
- `GET /api/openclaw/revisions`
- `GET /api/openclaw/revisions/{proposal_id}`
- `POST /api/openclaw/revisions/{proposal_id}/approve`
- `POST /api/openclaw/revisions/{proposal_id}/reject`

受限（默认禁用，仅人工）：
- `POST /api/admin/revisions/{proposal_id}/apply_to_draft`
- `POST /api/admin/revisions/{proposal_id}/rollback`
- `POST /api/admin/revisions/{proposal_id}/apply_memory`
- 文件直写接口（如 admin file save）

---

## 4. 安全控制

## 4.1 鉴权
- 给 OpenClaw 单独签发 `bot token`
- token 设置最短必要权限和过期时间
- 支持主动吊销与轮换
- 当前后端使用环境变量：`OPENCLAW_BOT_TOKEN`
- OpenClaw 调用时通过请求头传入：`X-OpenClaw-Token`

## 4.2 网络
- 后台 API 仅允许 HTTPS
- 建议后台入口走独立子域名（如 `admin.xxx.com`）
- 对 bot 请求追加 IP 白名单（或内网专线）

## 4.3 限流
- 登录、审批、发布、下载接口全部加限流
- 对 bot 账号单独配置更严格速率
- 当前 OpenClaw 接口已接入轻量限流（环境变量：`OPENCLAW_RPM_LIMIT`，默认 `60`）

---

## 5. 审计与可追溯

每个 OpenClaw 操作必须记录：
- `actor_type=bot`
- `actor_id=openclaw_bot`
- `action`
- `target_id`
- `request_id`
- `result`
- `note`
- `timestamp`
- 当前 OpenClaw approve/reject 已支持 `X-Request-Id` 透传并写入审计

建议日志结构统一 JSON，便于后续检索和告警。

---

## 6. 运营流程（推荐）

1. OpenClaw 周期拉取待审提案队列  
2. 依据质量信号生成“建议动作”（通过/驳回/人工复核）  
3. 对低风险提案可自动执行“通过/驳回”  
4. 对高风险提案仅生成建议并通知人工  
5. 人工审核后再执行应用或回滚  

---

## 7. 失败与回滚策略

- OpenClaw 调用失败：重试最多 2 次，之后进入死信队列
- 连续失败触发熔断，暂停自动操作，仅告警
- 所有“应用到草稿”前必须有快照
- 回滚动作必须保留原因并写审计

---

## 8. 上线清单（可勾选）

- [ ] 配置 `VITE_API_BASE_URL` 为生产地址  
- [ ] 后端 CORS 改为生产域名白名单  
- [ ] 管理后台与玩家前台使用独立 token 策略  
- [ ] 创建 `openclaw_bot` 账号并绑定权限白名单  
- [ ] 配置 bot 限流与 IP 白名单  
- [ ] 接入审计日志与错误告警  
- [ ] 完成一次灰度演练（审批 -> 应用 -> 回滚）  
- [ ] 产出应急手册（封禁 bot、回滚模板、恢复快照）

---

## 9. 第一阶段建议（最快可落地）

先让 OpenClaw 只做两件事：
- 自动标注提案建议（不落库写入）
- 自动执行低风险“驳回”  

暂不开放自动“应用到草稿/回滚”，先保守上线，稳定后再扩权。
