# OpenClaw 联调快速开始

## 1. 环境变量

参考并复制：
- `/Users/xuzi/Downloads/AI_Dialogue/Server/.env.production.example`

至少保证以下字段已配置：
- `ADMIN_PASSWORD`
- `OPENCLAW_BOT_TOKEN`
- `OPENCLAW_RPM_LIMIT`
- 你的 LLM key/base/model

---

## 2. 健康检查

```bash
curl -s \
  -H "X-OpenClaw-Token: <OPENCLAW_BOT_TOKEN>" \
  http://127.0.0.1:8000/api/openclaw/session
```

---

## 3. 拉取待审提案

```bash
curl -s \
  -H "X-OpenClaw-Token: <OPENCLAW_BOT_TOKEN>" \
  "http://127.0.0.1:8000/api/openclaw/revisions?status=queue&limit=20"
```

---

## 4. 审批一个提案

```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-OpenClaw-Token: <OPENCLAW_BOT_TOKEN>" \
  -H "X-Request-Id: claw-approve-001" \
  -d '{"note":"openclaw auto approve: quality gate passed"}' \
  http://127.0.0.1:8000/api/openclaw/revisions/<proposal_id>/approve
```

---

## 5. 驳回一个提案

```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-OpenClaw-Token: <OPENCLAW_BOT_TOKEN>" \
  -H "X-Request-Id: claw-reject-001" \
  -d '{"note":"openclaw auto reject: duplicate proposal"}' \
  http://127.0.0.1:8000/api/openclaw/revisions/<proposal_id>/reject
```

---

## 6. 当前限制（预期行为）

- OpenClaw 只能访问 `/api/openclaw/*` 白名单接口。
- `apply_to_draft`、`rollback`、`apply_memory` 仍需人工管理员。
- 命中限流会返回 `429`。
