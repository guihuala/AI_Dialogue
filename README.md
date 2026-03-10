# AI Roommate Survival Game (大学室友生存模拟)

[English](README_EN.md) | [中文](README.md)

## 项目简介

本项目是一个结合了大语言模型（LLM）的文字冒险与生存模拟游戏。玩家将在游戏中扮演一名大学生，与具有不同性格和独特背景设定的 AI 室友进行长周期的互动。

游戏内置了强大的 **AI 角色记忆系统**，支持多角色长期记忆、结构化档案管理和动态剧情生成。后端模型会根据角色性格推演剧情走向，并在每次互动中结算对玩家属性（如：SAN值、资金、GPA等）及时间流逝的影响。

## 项目结构

整个项目呈前后端分离的架构，主要由 **Client (Unity 客户端)** 和 **Server (Python 接口服务)** 组成。

```
AI_Dialogue/
├── Client/       # Unity 客户端前端，处理游戏 UI 展现、动画及与玩家的直接交互
├── Server/       # Python FastAPI 后端服务，处理 LLM 调用、游戏状态逻辑和记忆管理
├── README.md     # 项目整体中文引导文档
└── README_EN.md  # 项目整体英文引导文档
```

### 1. 后端服务 (Server)
包含游戏核心逻辑引擎，基于 Python FastAPI 构建：
- **AI 动态能力**：通过 `/api/get_options` 和 `/api/perform_action` 接口，根据角色人设、口头禅与禁忌词，动态生成符合逻辑的玩家备选项及剧情发展。
- **长期记忆检索 (RAG)**：通过 ChromaDB 本地向量数据库管理多角色的过往剧情与观察想法，解决上下文碎片化问题，在每次对话时动态引入过往内容进行参考。
- **智能反思与记录**：角色可以进行自我反思更新心情或人际关系，形成带有时间维度的每日日志。
- **Web 系统控制台**：运行后可通过 `http://127.0.0.1:8000/admin` 访问管理后台，提供实时监控、记忆修改、好感度篡改、存档快照管理及剧本热重载功能。

*详情请参考 [Server/README.md](Server/README.md) 用于进一步开发与深入。*

### 2. 前端客户端 (Client)
基于 Unity 引擎开发，构筑前端视听体验：
- 负责 2D/UI 场景的界面视觉展现（包含 FlatKit, ProPixelizer 等视觉插件基础支持）。
- 扩展丰富的游戏演出体验：支持**角色动作旁白渲染**与真实的**微信群聊界面模拟**显示。
- 管理前端网络连接服务逻辑 (`NetworkService`)，主要通过 HTTP `POST` 请求向 `http://127.0.0.1:8000` 通信驱动游戏运转。

## 运行与开发指南

游戏跑起来需要分别启动 Server 和 Client，建议按照以下步骤进行：

### 第一步：启动后端服务 (Server)
1. 进入服务器目录并安装依赖环境：
   ```bash
   cd Server
   pip install -r requirements.txt
   # 若提示找不到 fastapi 环境，可单独再运行 pip install fastapi uvicorn
   ```
2. 需要将你的 LLM 服务（OpenRouter / OpenAI 等）的鉴权密钥配置在 `.env` 文件中。
3. 运行后端服务：
   ```bash
   python src/app.py
   ```
后端服务启动成功后默认监听本地 `127.0.0.1:8000` 端口。

### 第二步：启动前端游戏环境 (Client)
1. 使用 **Unity Hub** 添加并打开 `Client` 目录作为项目。
2. 在 Unity Editor 中定位到游戏主场景，并且确保在启动游戏前，后端的 `http://127.0.0.1:8000` 确实可访问。
3. 点击 Unity Editor 中的 **Play(播放)** 按钮，开始生存试炼。

## 技术栈与依赖库
- **后端框架**: Python, FastAPI, uvicorn
- **大语言模型与 AI**: OpenAI SDK (支持各类兼容接口), ChromaDB (向量数据库)
- **数据与配置管理**: Pydantic, python-dotenv
- **游戏客户端**: Unity C# Engine

## 许可证

本项目采用 MIT 许可证 - 查看 [Server/LICENSE](Server/LICENSE) 文件或者各核心组件包含的开源许可了解详情。
