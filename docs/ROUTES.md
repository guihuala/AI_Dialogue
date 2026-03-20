# 项目路由说明（前后端）

## 1) 如何进入后台（Admin）

- 前端后台页面不是通过侧边栏暴露的，而是隐藏入口。
- 直接在浏览器地址栏访问：
  - `http://localhost:5173/admin`（Vite 默认端口）
  - 或 `http://localhost:5173/#/admin`
- 进入后会显示口令框，当前口令写死在前端代码中：
  - `mokukeki`
- 代码位置：
  - `WebClient/src/App.tsx`（检查 `/admin` 或 `#/admin`）
  - `WebClient/src/components/AdminDashboard.tsx`（`ADMIN_PASSWORD`）

## 2) 前端“路由”现状

项目当前未使用 `react-router`，是单页状态切换（`activeTab`）：

- `game` -> 游戏主界面
- `mods` -> 模组库
- `workshop` -> 也复用 `ModManager`
- `editor` -> Prompt/事件编辑器
- `settings` -> 系统设置
- `admin` -> 后台管理页（仅 URL 触发）

主入口代码：
- `WebClient/src/App.tsx`

## 3) 后端 API 路由总览（FastAPI）

### Game
- `GET /api/game/candidates`
- `POST /api/game/start`
- `POST /api/game/turn`
- `POST /api/game/prefetch`
- `GET /api/game/monitor`
- `POST /api/game/save`
- `GET /api/game/saves_info`
- `GET /api/game/load/{slot_id}`
- `DELETE /api/game/save/{slot_id}`
- `POST /api/game/reset`
- `GET /api/game/memories`
- `DELETE /api/game/memories/{memory_id}`
- `POST /api/game/reflect`

### System
- `GET /api/system/settings`
- `POST /api/system/settings`
- `POST /api/system/rebuild_knowledge`

### Admin
- `GET /api/admin/files`
- `GET /api/admin/file`
- `POST /api/admin/file`
- `POST /api/admin/upload_portrait`
- `POST /api/admin/generate_skill_prompt`

### Agent
- `POST /api/agent/chat`

### Library / User / Storage
- `POST /api/library/save_current`
- `GET /api/library/list`
- `POST /api/library/apply/{item_id}`
- `POST /api/library/validate/{item_id}`
- `DELETE /api/library/{item_id}`
- `GET /api/user/state`
- `GET /api/user/audit`
- `GET /api/user/snapshots`
- `POST /api/user/rollback/{snapshot_id}`
- `GET /api/storage/quota`
- `POST /api/storage/cleanup`

### Workshop
- `POST /api/workshop/validate_current`
- `POST /api/workshop/publish_current`
- `GET /api/workshop/list`
- `POST /api/workshop/download/{item_id}`
- `POST /api/workshop/apply/{item_id}`
- `DELETE /api/workshop/{item_id}`
- `PATCH /api/workshop/{item_id}`

### Intervention
- `GET /api/intervention/memory`
- `POST /api/intervention/memory`
- `DELETE /api/intervention/memory/{mem_id}`
- `GET /api/intervention/tools`
- `POST /api/intervention/tool`
- `POST /api/intervention/affinity`
- `POST /api/intervention/stats`

### Debug
- `GET /api/debug/chat_history`
- `GET /api/debug/state`
- `POST /api/debug/clear_cache`

后端定义文件：
- `Server/src/app.py`

## 4) 建议的整理方向（下一步）

### 前端
- 引入 `react-router-dom`，将 `activeTab` 切为显式路径：
  - `/`, `/mods`, `/workshop`, `/editor`, `/settings`, `/admin`
- 保留 `activeTab` 作为 UI 状态，而不是路由来源。

### 后端
- 将 `app.py` 拆分为模块化路由：
  - `src/routers/game.py`
  - `src/routers/system.py`
  - `src/routers/admin.py`
  - `src/routers/library.py`
  - `src/routers/workshop.py`
  - `src/routers/intervention.py`
  - `src/routers/debug.py`
- `main app` 里只保留 `include_router(...)` 和全局中间件。

当前已落地（第一阶段）：
- `Server/src/routers/system_router.py`
- `Server/src/routers/admin_router.py`
- `Server/src/routers/debug_router.py`

由 `Server/src/app.py` 统一注册：
- `register_system_routes(...)`
- `register_admin_routes(...)`
- `register_debug_routes(...)`

当前已落地（第二阶段）：
- `Server/src/routers/content_router.py`（`library/workshop/user/storage`）
- `Server/src/routers/intervention_router.py`（干预工具）

当前已落地（第三阶段）：
- `Server/src/routers/game_router.py`（`game/save/memory/prefetch`）

当前 `app.py` 自身仅保留：
- 少量应用装配代码
- 多用户引擎管理
- Router 注册入口

当前已落地（第四阶段，service 下沉）：
- `Server/src/services/roster_service.py`
- `Server/src/services/state_service.py`
- `Server/src/services/mod_service.py`

当前主入口体量：
- `Server/src/app.py` 已缩减到约 200 行

### 安全（建议尽快）
- 当前后台口令在前端硬编码，等同“公开口令”。
- 至少改为后端校验 + 环境变量口令（或签发临时 token）。
