# 代号：大学档案 ～ AI角色模拟游戏

[English](README_EN.md) | [简体中文](README.md)

## 项目简介

本项目是一个大语言模型驱动的的**角色模拟游戏**，是为桂花拉糕的毕设。

玩家（陆陈安然）将在大一至大四的校园周期中，与多位性格迥异、身怀秘密的 AI 室友深度互动，在学业、人际与社交中通过决策生存下去。

在我的设想中，大语言模型驱动的角色模拟游戏应该带给玩家更多可能性——于是我设计了自定义prompt，并将prompt打包发布的功能，此功能的目标是：
- 编写属于自己的世界观、角色和特殊事件
- 编写skill，让ai完成您提出的任务
- 发布您编写的模组包到服务器，供其他玩家体验
简言之，我希望本作不仅是“AI驱动的游戏“————他应该是一个开放的沙盒，允许玩家修改或添加设定。

引入AI的意义不应该是“我懒得写剧情，交给AI吧“，而是借由LLM这个新兴工具，把玩法打包成较为成熟的框架，让玩家尝试不同角色在不同世界观下的组合。

此外，由于主播水平比较抱歉，本项目高度依赖gemini，代码质量不佳，见笑了。请不要拷打我。

## todo

- [ ] 可能需要重构管理员系统
- [ ] 默认prompt包写得不怎么样（其实也都是ai生产...主播就差本人都是ai生成的了），ai生成的对话依旧人机，需要修改
- [ ] 将本项目部署在服务器上

## 最近进展

- [x] 模组系统已补齐“首次公开 / 更新公开版本 / 发布派生作品”的分流
- [x] 模组元数据、列表组装、下载副本同步、发布身份推导与发布主流程已开始移入 `mod_service`
- [x] 发布落盘与状态写回已开始移入 `mod_service`
- [x] 模组库 / 工坊列表接口已补齐基础搜索、排序、分页查询入口
- [x] 前端模组中心已接入基础搜索、排序、分页查询链路
- [x] 账户系统第一阶段后端已补齐 register / login / logout / me，并开始接管身份解析
- [x] 前端已加入独立账户入口，支持访客提示、注册、登录、登出
- [x] 账户系统已补齐修改密码与“绑定当前访客数据”入口
- [x] 账户中心已补齐会话管理与最近活动展示，支持退出其他设备
- [x] 账户系统已补齐访客绑定预览；工坊发布类动作开始要求正式账户登录
- [x] 编辑器发布弹窗已补齐未登录提示，并可直接引导前往账户中心
- [x] 账户中心与模组页已开始显式展示“访客可用 / 登录后可用”的能力范围
- [x] 访客绑定支持冲突处理策略与迁移报告，后台已补齐用户检索与统计第一版
- [ ] 模组系统后续仍需继续补更强索引与更大规模检索能力

## 项目结构

```text
AI_Dialogue/
├── WebClient/    # React 现代化前端（基于 Vite/Tailwind/Lucide）
├── Server/       # FastAPI 后端服务
├── docs/         # 项目文档与说明
├── README.md     # 本项目中文引导文档
└── README_EN.md  # 项目英文引导文档
```

## 文档导航

如果你希望先快速理解项目结构，建议从以下文档开始：

- `docs/project_guide/README.md`：项目总说明
- `docs/project_guide/frontend.md`：前端说明
- `docs/project_guide/backend.md`：后端说明
- `docs/project_guide/mod_system.md`：模组系统说明与后续优先级
- `docs/project_guide/account_system.md`：账户系统设计说明

## 快速启动

### 第一步：后端环境配置
1. 进入 `Server` 目录并安装依赖：
   ```bash
   cd Server
   pip install -r requirements.txt
   ```
2. 以 `Server/.env.example` 为模板创建本地 `Server/.env`，填入你的密钥与后台口令：
   ```env
   DEEPSEEK_API_KEY=your_api_key_here
   ADMIN_PASSWORD=change_me_to_a_strong_password
   ADMIN_SESSION_TTL_SECONDS=43200
   ```
   `Server/.env` 已被 `.gitignore` 忽略，不应提交到仓库。
3. 启动后端服务：
   ```bash
   python src/app.py
   ```
   *默认监听地址: `http://127.0.0.1:8000`*

### 第二步：前端环境配置
1. 进入 `WebClient` 目录并安装依赖：
   ```bash
   cd WebClient
   npm install
   ```
2. 启动开发服务器：
   ```bash
   npm run dev
   ```
   *默认通过浏览器访问控制台中显示的本地端口*

### 后台说明
- 后台入口默认是 `http://localhost:5173/admin`
- 后台登录现在由后端校验 `ADMIN_PASSWORD`，不再使用前端硬编码口令
- 管理员会话会签发短期 token，服务重启后会失效，属于当前设计的正常行为

## 技术栈
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide React, Framer Motion
- **Backend**: FastAPI (Python), ChromaDB (Vector DB), Pydantic
- **AI Engine**: GPT-4 / DeepSeek-V3 (兼容 OpenAI 协议)

## 许可证
本项目采用 MIT 许可证。
