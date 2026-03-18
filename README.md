# AI Roommate Survival Game (大学室友生存模拟 - 重筑版)

[English](README_EN.md) | [中文](README.md)

## 🌟 项目简介

本项目是一个融合了大语言模型（LLM）的**高保真文字冒险与生存模拟游戏**。玩家将在大一至大四的校园周期中，与多位性格迥异、身怀秘密的 AI 室友深度互动，在学业、人际与社交中通过决策生存下去。

**核心特色：**
- **🧠 记忆链系统**：基于 ChromaDB 处理多角色长期记忆，AI 室友能记住你曾经的冒犯、帮助与承诺，并在对话中动态回溯。
- **🎮 自动化剧本引擎**：支持动态推演玩家行为对数值（SAN、GPA、资金、名誉等）的深度影响，并实时重构后续剧情。
- **📦 创意模组编辑器 (Mod Editor)**：内置强大的可视化配置工具，支持零代码修改角色档案、剧情时间轴、系统逻辑提示词 (Skill)。
- **🌐 全端 Web 体验**：采用现代化 React + Vite 架构，提供高审美、玻璃拟态风格的 UI 交互，支持 WebAdmin 监控后台。

## 📂 项目结构

```text
AI_Dialogue/
├── WebClient/    # React 现代化前端（基于 Vite/Tailwind/Lucide），包含游戏核心与模组编辑器
├── Server/       # FastAPI 后端服务，处理 LLM 调用、RAG 记忆存储、存档管理与模组打包
├── README.md     # 本项目中文引导文档
└── README_EN.md  # 项目英文引导文档
```

### 1. 现代化前端 (WebClient)
- **游戏主对局**：流式打字机演出、微信群聊模拟、实时好感度反馈。
- **创意编辑器**：
  - **角色管理**：可视化配置角色档案、立绘上传与身世设定。
  - **剧情时间轴**：拖拽式编排学年剧情步进与事件池优先级。
  - **系统逻辑 (Skill)**：支持 AI 一键生成复杂的系统插件 Prompts，并动态挂载至 DM 逻辑中枢。
- **监控终端**：上帝视角实时查看 AI 决策链、检索到的记忆节点以及底层推理逻辑。

### 2. 后端服务 (Server)
- **src/app.py**：核心 API 网关，支持热重载模组及存档快照。
- **src/core/game_engine.py**：游戏主控大脑，负责异步推演、分支剪枝及数值结算。
- **src/core/agent_system.py**：实现 NPC 的反思机制与独立的性格驱动模型。
- **scripts/run_ai_test.py**：全自动压力测试脚本，可模拟真实玩家进行全周期（大一至大四）的逻辑校验。

## 🚀 快速启动

### 第一步：后端环境配置 (Server)
1. 进入 `Server` 目录并安装依赖：
   ```bash
   cd Server
   pip install -r requirements.txt
   ```
2. 配置 `.env` 文件，填入你的大模型鉴权：
   ```env
   OPENAI_API_KEY=your_key_here
   OPENAI_BASE_URL=https://api.yourprovider.com/v1
   MODEL_NAME=gpt-4o-mini
   ```
3. 启动后端服务：
   ```bash
   python src/app.py
   ```
   *默认监听地址: `http://127.0.0.1:8000`*

### 第二步：前端环境配置 (WebClient)
1. 进入 `WebClient` 目录并安装包：
   ```bash
   cd WebClient
   npm install
   ```
2. 启动开发服务器：
   ```bash
   npm run dev
   ```
   *默认通过浏览器访问控制台中显示的本地端口*

## 🛠️ 模组开发与测试

### 如何本地测试我的模组？
我们提供了一套严密的自动测试流水线，避免模组上线后出现剧情死循环或数值崩溃：
```bash
# 在 Server 目录下运行
python scripts/run_ai_test.py
```
该脚本将生成详细的测试报告 `Server/data/test_report.md`，供您分析 AI 的逻辑一致性。

## 🎨 技术栈
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide React, Framer Motion
- **Backend**: FastAPI (Python), ChromaDB (Vector DB), Pydantic
- **AI Engine**: GPT-4o-mini / DeepSeek (兼容 OpenAI 协议)

## 📄 许可证
本项目采用 MIT 许可证。
