# 项目总说明

本目录用于集中说明 `AI_Dialogue` 项目的整体结构，以及前端、后端各自的职责与开发方式。

## 1. 项目定位

`AI_Dialogue` 是一个以大语言模型为驱动的校园题材角色模拟游戏。项目采用前后端分离结构：

- `WebClient/`：玩家界面、编辑器、模组中心、后台管理页面
- `Server/`：游戏引擎、配置管理、模组应用、存档与用户隔离、AI 调度接口

项目不只是一个“对话生成器”，还包含了以下两层能力：

- 游戏运行层：角色选择、剧情推进、数值变化、事件脚本、手机界面与聊天通知
- 内容生产层：Prompt 编辑、角色/事件编辑、模组打包、工坊发布、后台校验

## 2. 顶层结构

```text
AI_Dialogue/
├── WebClient/           # React + Vite 前端
├── Server/              # FastAPI + 游戏引擎后端
├── docs/                # 项目文档
│   └── project_guide/   # 本次整理的总说明目录
├── README.md
└── README_EN.md
```

## 3. 运行方式

### 后端

1. 进入 `Server/`
2. 安装依赖：`pip install -r requirements.txt`
3. 参考 `.env.example` 创建 `.env`
4. 启动：`python src/app.py`

默认服务地址为 `http://127.0.0.1:8000`。

### 前端

1. 进入 `WebClient/`
2. 安装依赖：`npm install`
3. 启动：`npm run dev`

前端默认通过 Vite 本地端口访问，并直接请求 `http://127.0.0.1:8000/api`。

## 4. 系统协作关系

项目的主流程可以概括为：

1. 前端通过 `App.tsx` 管理当前页面标签，不依赖 `react-router`。
2. 玩家开始新游戏后，前端调用 `/api/game/start` 初始化对局。
3. 后端为当前访客创建或复用 `GameEngine`，并根据 Prompt、事件表和角色配置生成当前局面。
4. 玩家每次选择后，前端调用 `/api/game/turn` 推进剧情。
5. 后端在推进过程中会读写记忆、状态、事件脚本，并在必要时触发预取与反思逻辑。
6. 如果用户进入编辑器或模组中心，又会调用后台接口对 Prompt、事件文件、模组包和工坊数据进行管理。

## 5. 项目里的几个关键概念

### `visitor_id`

前端会在本地生成并持久化 `visitor_id`，之后通过 `X-Visitor-Id` 请求头传给后端。后端据此隔离不同用户的数据目录和运行中的游戏引擎实例。

### 活动配置与模组

后端把“当前生效的 Prompt + 事件 + 角色配置”视作活动配置。用户可以：

- 把当前配置保存到个人模组库
- 从个人模组库应用某个模组
- 将当前配置发布到工坊
- 从工坊下载或应用模组

### 用户隔离

后端通过 `Server/src/core/config.py` 中的路径函数，把不同用户的数据放到：

- `data/users/{user_id}/prompts`
- `data/users/{user_id}/events`
- `data/users/{user_id}/library`
- `data/users/{user_id}/saves`

默认用户 `default` 则直接使用 `Server/data/` 下的基础目录。

## 6. 建议阅读顺序

如果是第一次接手这个项目，建议按以下顺序阅读：

1. 根目录 `README.md`
2. `docs/project_guide/frontend.md`
3. `docs/project_guide/backend.md`
4. `WebClient/src/App.tsx`
5. `Server/src/app.py`

## 7. 子文档

- [前端说明](./frontend.md)
- [后端说明](./backend.md)
