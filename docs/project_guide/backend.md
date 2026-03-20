# 后端说明

## 1. 技术栈

后端位于 `Server/`，当前项目实际使用的是：

- FastAPI
- Pydantic
- OpenAI 兼容接口客户端
- ChromaDB
- pandas
- python-dotenv

依赖定义见 `Server/requirements.txt`。

## 2. 启动入口

主入口文件是：

- `Server/src/app.py`

这个文件负责：

- 初始化 FastAPI 应用
- 创建共享线程池
- 构造全局 `AdminAuthManager`
- 维护按用户隔离的 `GameEngine` 实例
- 注册各个 router
- 启用 CORS
- 启动 `uvicorn`

如果直接运行：

```bash
python src/app.py
```

服务会监听 `0.0.0.0:8000`。

## 3. 后端整体结构

后端主要可以分成五层：

### 路由层

位于 `Server/src/routers/`，负责暴露 HTTP API。

### 服务层

位于 `Server/src/services/`，负责用户状态、模组应用、管理员鉴权、角色 roster 等偏业务的辅助逻辑。

### 核心引擎层

位于 `Server/src/core/`，负责游戏推进、Prompt 管理、事件调度、记忆系统、脚本执行、反思系统等核心能力。

### 数据模型层

位于 `Server/src/models/`，定义结构化数据模型。

### 存储层

位于 `Server/src/storage/`，负责 JSON/向量存储。

## 4. 路由模块说明

### `system_router`

负责系统级配置与辅助能力：

- 读取/更新大模型配置
- 重建知识库
- 手动触发反思
- 初始化角色 Agent

常见接口：

- `GET /api/system/settings`
- `POST /api/system/settings`
- `POST /api/system/rebuild_knowledge`
- `POST /api/game/reflect`
- `POST /api/agent/chat`

### `game_router`

负责核心游戏流程，是最重要的业务入口：

- 获取候选角色
- 开始新游戏
- 推进回合
- 预取下个事件
- 查询运行状态
- 存档、读档、删档、重置
- 记忆查询与删除

其中 `/api/game/start` 和 `/api/game/turn` 最关键，最终都会落到 `GameEngine.play_main_turn(...)`。

### `admin_router`

负责后台编辑与管理员能力：

- 管理员登录、会话查询、登出
- 获取可编辑文件列表
- 读取/保存 Prompt、事件等文本文件
- 上传角色立绘
- 借助 LLM 生成 Skill Prompt

### `content_router`

负责模组与用户资源管理：

- 将当前活动配置保存到个人模组库
- 列出、校验、应用、删除库内模组
- 查询用户状态
- 查询与清理存储配额
- 读取审计日志
- 快照与回滚
- 工坊发布、下载、应用、更新、删除

这一层是“游戏内容可编辑、可打包、可回滚”的关键。

### `intervention_router`

负责更底层的强制干预能力：

- 直接查看/注入/删除记忆
- 强制调用工具
- 覆盖好感度
- 覆盖角色数值

这一层更像调试和实验接口。

### `debug_router`

负责开发排查：

- 查看聊天历史
- 查看当前引擎状态
- 清除缓存

## 5. 用户隔离与目录结构

后端通过 `Server/src/core/config.py` 统一管理路径。

基础目录包括：

- `data/prompts`
- `data/events`
- `data/saves`
- `data/chroma_db`

对非默认用户，系统会自动切到：

- `data/users/{user_id}/prompts`
- `data/users/{user_id}/events`
- `data/users/{user_id}/saves`
- `data/users/{user_id}/library`
- `data/users/{user_id}/chroma_db`

这里的 `user_id` 来自请求头 `X-Visitor-Id`。

这意味着后端不是传统数据库驱动的多租户系统，而是“文件目录隔离 + 内存中引擎实例隔离”的方案。

## 6. `GameEngine` 的角色

虽然本文没有展开所有核心源码，但从路由入口已经可以确认：`GameEngine` 是整个后端的核心调度中心。

它至少承担以下职责：

- 初始化和重置对局
- 推进主剧情回合
- 调用 LLM 生成叙事结果
- 管理记忆与事件缓存
- 维护当前章节、事件、角色与数值状态
- 配合预取和反思系统优化体验

在 `app.py` 中，后端会为每个用户维护一个 `engines[user_id]`，首次访问时才创建。

## 7. 后端里几个重要的业务机制

### 配置热重载

当管理员修改角色、Prompt 或事件文件后，系统会在需要时：

- 重载时间线
- 重建 PromptManager
- 同步主角名到工具管理器

这使得编辑器修改后的内容可以较快反映到运行环境里。

### 快照与回滚

在应用模组前，系统会先创建快照。这样即使模组内容有问题，也可以通过快照回滚到上一份可用状态。

### 存储配额控制

内容系统会限制：

- 模组数量上限
- 模组总存储大小
- 快照保留数量

管理员页还能触发存储清理。

### 后台任务

后端维护了 `ThreadPoolExecutor`，主要用于：

- 预取剧情
- 异步反思

这样可以尽量减少主流程阻塞。

## 8. 环境配置

至少要关注以下环境变量：

- `DEEPSEEK_API_KEY`
- `ADMIN_PASSWORD`
- `ADMIN_SESSION_TTL_SECONDS`
- `DATA_ROOT_DIR`（可选，用于改写数据根目录）

目前项目默认更偏向本地开发环境，部署前建议再补充：

- 更严格的 CORS 策略
- 更稳定的管理员会话持久化
- API 地址和模型配置的环境化管理

## 9. 你接手后端时最值得先看的文件

建议优先阅读：

1. `Server/src/app.py`
2. `Server/src/core/game_engine.py`
3. `Server/src/core/config.py`
4. `Server/src/routers/game_router.py`
5. `Server/src/routers/content_router.py`
6. `Server/src/services/state_service.py`
7. `Server/src/services/mod_service.py`

## 10. 当前架构的特点与风险

优点：

- 文件结构直观，适合做内容编辑型项目
- 模组、快照、工坊、编辑器这些能力耦合得比较完整
- 用户隔离机制简单直接，易于本地调试

需要留意的点：

- 引擎实例保存在进程内，多进程部署或服务重启会影响会话连续性
- API 权限边界主要依赖请求头和管理员 token，生产化前需要继续加固
- 文件读写型架构在并发升高后会面临锁、热更新一致性和恢复策略问题
