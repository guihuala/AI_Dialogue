# AI 角色记忆系统

一个支持本地部署的 AI 角色记忆系统，具备长期记忆、结构化档案管理和智能反思功能。

[English](README_EN.md) | [中文](README.md)

## 项目简介

本项目旨在为游戏中的 AI 角色提供一套完整的记忆系统服务。它特别解决了记忆数据向量化时的切片问题，避免了上下文碎片化，同时完整保留了向量化的语义理解能力。

## 项目结构

```
d:\MyProj\character-memory\
├── data/                  # 💾 运行时数据存储
│   ├── profile.json       # 角色档案 (姓名, 性格, 日志等)
│   └── chroma_db/         # 向量数据库 (ChromaDB) 用于语义记忆检索
├── src/                   # 🧠 源代码
│   ├── app.py             # Streamlit 主程序 (前端入口)
│   ├── core/              # 核心逻辑
│   │   └── memory_manager.py # 管理档案、检索和反思逻辑
│   ├── models/            # 数据模型
│   │   └── schema.py      # Pydantic 模型 (CharacterProfile, MemoryItem, DailyLogEntry)
│   ├── services/          # 外部服务
│   │   └── llm_service.py # LLM 集成 (OpenRouter/OpenAI)
│   └── storage/           # 数据访问层
│       ├── json_store.py  # 处理 profile.json 操作
│       └── vector_store.py# 处理 ChromaDB 操作
├── docs/                  # 文档
└── requirements.txt       # Python 依赖
```

## 数据存储

-   **档案数据 (Profile Data)**: 存储在 `data/profile.json`。包含角色的结构化状态：
    -   基本信息 (姓名, 职业)
    -   性格与价值观
    -   人际关系
    -   **每日日志 (Daily Log)** (活动和互动的记录)
    -   状态 (健康, 财富)

-   **记忆数据 (Memory Data)**: 存储在 `data/chroma_db`。这是一个本地向量数据库，存储：
    -   对话历史 (用户输入 & AI 回复)
    -   观察与想法
    -   每条记忆都经过 Embedding 处理以支持语义搜索 (RAG)。

## 如何运行

```bash
streamlit run src/app.py
```

## 核心功能

1.  **RAG 记忆检索**: 根据当前对话检索相关的过往记忆。
2.  **智能反思 (Agentic Reflection)**:
    -   点击 **"🛑 End Conversation & Reflect"** 触发自我反思流程。
    -   AI 会分析对话，更新心情/人际关系，并写入 **每日日志**。
3.  **实时耗时显示**: 在界面上实时显示检索 (RAG) 和生成 (LLM) 的耗时。
4.  **高级 RAG (父子索引策略)**:
    -   **基于阈值的总结机制**:
        -   **短对话 (<300 字符)**: 直接存储，保留细节并节省成本。
        -   **长对话 (>300 字符)**: 由 LLM 自动总结。**总结**用于索引，**原始内容**用于上下文检索。
    -   **每日日志集成**: 每日日志也会被向量化 (类型为 `daily_log`)，确保能检索到过往的活动记录。
## 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。