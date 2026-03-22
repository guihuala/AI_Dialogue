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

补充（expression-only 短输出提示词）：

- 目前短输出链路的三段核心提示词已改为文件驱动，默认路径为：
  - `Server/data/prompts/system/expression_system_prompt.md`
  - `Server/data/prompts/system/expression_user_prompt.md`
  - `Server/data/prompts/system/expression_json_contract.md`
- `GameEngine` 会优先读取这些文件；读取失败时才回退到代码内置兜底文本。

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
- 列出、校验、删除库内模组
- 切换当前编辑目标
- 查询用户状态
- 查询与清理存储配额
- 读取审计日志
- 快照与回滚
- 工坊下载
- 工坊首次公开、更新公开版本、发布派生作品
- 工坊列表、元数据展示、后台删除与基础更新

这一层是“游戏内容可编辑、可打包、可回滚、可公开”的关键。

当前语义已经调整为：

- 模组不能在局外直接应用
- 模组只会在开始新游戏时生效
- 编辑器修改的是“当前编辑目标”
- 默认模组只读，想修改必须先另存为私有模组
- 公共模组只能由原作者更新
- 下载公共模组得到的是私有副本
- 下载副本再次公开时按派生作品处理，而不是覆盖原作

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

在 `app.py` 中，后端会为每个用户维护一个 `engines[user_id]`，首次访问时才创建。

## 6. 重要业务

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

## 7. 环境配置

要关注以下环境变量：

- `DEEPSEEK_API_KEY`
- `ADMIN_PASSWORD`
- `ADMIN_SESSION_TTL_SECONDS`
- `DATA_ROOT_DIR`（可选，用于改写数据根目录）

目前项目默认更偏向本地开发环境，部署前建议再补充：

- 更严格的 CORS 策略
- 更稳定的管理员会话持久化
- API 地址和模型配置的环境化管理

## 8. 重要文件

建议优先阅读：

1. `Server/src/app.py`
2. `Server/src/core/game_engine.py`
3. `Server/src/core/config.py`
4. `Server/src/routers/game_router.py`
5. `Server/src/routers/content_router.py`
6. `Server/src/services/state_service.py`
7. `Server/src/services/mod_service.py`
