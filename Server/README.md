# Roommate Survival Game API (Server)

这是一个基于 FastAPI 和 Python 构建的文字冒险游戏（室友生存/大学生活）的后端服务。它通过接入大型语言模型（LLM）来动态推演游戏剧情，提供玩家与不同性格室友之间的交互选项，并使用本地向量数据库维护角色的长期记忆。

## 目录结构

```
Server/
├── data/                  # 本地数据存储（如向量数据库 ChromaDB 数据、游戏存档等）
├── src/                   # 源代码目录
│   ├── app.py             # FastAPI 主程序入口，包含 API 路由
│   ├── core/              # 核心逻辑模块
│   │   ├── data_loader.py # 数据加载
│   │   ├── event_director.py # 随机事件调度
│   │   ├── event_script.py   # 事件脚本管理
│   │   ├── game_engine.py    # 游戏主引擎，处理状态、天数流转和核心玩法
│   │   ├── memory_manager.py # 记忆管理模块（长短期记忆处理）
│   │   ├── presets.py        # 核心预设数据（室友档案候选池等）
│   │   ├── prompt_manager.py # 提示词管理器
│   │   └── wechat_system.py  # 模拟微信交互系统
│   ├── models/            # Pydantic 数据模型定义 (Schema, State 等)
│   ├── services/          # 第三方及外部服务集成
│   │   └── llm_service.py # 封装的语言模型（LLM）客户端服务
│   └── storage/           # 底层存储与数据库操作（如 ChromaDB 交互）
├── tests/                 # 单元测试与测试脚本
├── .env                   # 环境变量配置文件（如 API_KEY 等）
└── requirements.txt       # Python 运行所需依赖
```

## 核心接口

服务当前主要暴露以下接口：

- **`POST /api/get_options`**：通过提供当前在场的室友数据，结合 LLM 动态生成玩家的多个可交互行动选项（如：附和、沉默/转移话题、阴阳怪气等）。
- **`POST /api/perform_action`**：接收玩家选择，并通过 LLM 推演后续的对话发展（提供 1~3 句推演对话），并结算该行为对玩家个人属性（SAN值、资金、GPA等）及时间的影响。

## 核心机制设计

1. **动态选项生成**：由 LLM 驱动，确保每次互动选项贴合当前寝室局势与人物特性。
2. **防 OOC (Out of Character)**：通过向 LLM 提供详尽的室友属性设定档案（包括行为逻辑、口头禅、禁语），最大程度保持人物性格一致性。
3. **长期记忆系统**：结合 `ChromaDB`，记录对局中的历史事件、对话，并通过检索增强（RAG）让系统形成长远记忆，影响此后的交互发展。
4. **游戏数值与状态结算**：每次交互不仅触发剧情，也会联动玩家基础数值（SAN值, GPA, 资金）的变化，结合时间流逝形成连续的模拟经营玩法。

## 运行方式 (本地环境)

1. 安装依赖：
```bash
pip install -r requirements.txt
pip install fastapi uvicorn # 推荐
```

2. 确保在 `.env` 文件中配置了对应的 LLM 服务密钥（如 OpenAI / OpenRouter 等）。

3. 启动 FastAPI 服务：
```bash
python src/app.py
```
或者使用 Uvicorn 直接启动：
```bash
uvicorn src.app:app --host 0.0.0.0 --port 8000
```
服务默认运行在 `http://127.0.0.1:8000`。可前往 `http://127.0.0.1:8000/docs` 查看 Swagger 互动 API 文档。

## 依赖库摘要

- `FastAPI` / `uvicorn` (主服务器框架)
- `pydantic` (数据建模与校验)
- `openai` (LLM 调用客户端)
- `chromadb` (向量数据库)
- `python-dotenv` (环境变量加载)
- `pandas` / `gradio` (数据处理与可能的前端调试功能)
