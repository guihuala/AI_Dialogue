# 代号：大学档案 ～ AI角色模拟游戏

[English](README_EN.md) | [简体中文](README.md)

## 项目简介

本项目是一个大语言模型驱动的的**角色模拟游戏**，是为桂花拉糕的毕设。

玩家（陆陈安然）将在大一至大四的校园周期中，与多位性格迥异、身怀秘密的 AI 室友深度互动，在学业、人际与社交中通过决策生存下去。

在我的设想中，大语言模型驱动的角色模拟游戏应该带给玩家更多可能性——于是我设计了自定义prompt，并将prompt打包发布的功能，此功能的目标是：
- 编写属于自己的世界观、角色和特殊事件
- 编写skill，让ai完成您提出的任务
- 发布您编写的模组包到服务器，供其他玩家体验

此外，由于主播水平比较抱歉，本项目高度依赖gemini，代码质量不佳，见笑了。请不要拷打我。

## todo

- [ ] 可能需要重构管理员系统
- [ ] 默认prompt包写得不怎么样（其实也都是ai生产...主播就差本人都是ai生成的了），ai生成的对话依旧人机，需要修改
- [ ] 将本项目部署在服务器上

## 项目结构

```text
AI_Dialogue/
├── WebClient/    # React 现代化前端（基于 Vite/Tailwind/Lucide）
├── Server/       # FastAPI 后端服务
├── README.md     # 本项目中文引导文档
└── README_EN.md  # 项目英文引导文档
```

## 快速启动

### 第一步：后端环境配置
1. 进入 `Server` 目录并安装依赖：
   ```bash
   cd Server
   pip install -r requirements.txt
   ```
2. 配置 `.env` 文件，填入你的APIKEY：
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

## 技术栈
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide React, Framer Motion
- **Backend**: FastAPI (Python), ChromaDB (Vector DB), Pydantic
- **AI Engine**: GPT-4 / DeepSeek-V3 (兼容 OpenAI 协议)

## 许可证
本项目采用 MIT 许可证。
