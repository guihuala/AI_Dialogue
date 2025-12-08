# AI 视觉小说项目文档
[English](README.md) | [中文](README_CN.md)

## 1. 项目概述
这是一个由 **本地 LLM** 驱动的 **视觉小说 (Galgame)** 项目。它结合了 **Unity 客户端**（负责视觉界面）和 **Python 后端**（负责 AI 逻辑和记忆管理）。

### 核心功能
-   **Sidecar 架构**：Unity 处理 UI，Python 处理 AI。
-   **视觉小说 UI**：支持角色立绘、对话气泡和选项。
-   **动态剧情**：剧情由 LLM 根据游戏规则和角色档案实时生成。
-   **游戏循环**：包含 12 天的生存循环，涉及数值系统（金钱、心情、GPA）。

## 2. 架构
-   **客户端 (Unity)**:
    -   位于 `Client/` 目录。
    -   负责渲染、用户输入和游戏状态显示。
    -   通过 HTTP (流式 API) 与服务器通信。
-   **服务端 (Python)**:
    -   位于 `Server/` 目录。
    -   托管 LLM 逻辑、记忆系统 (向量数据库) 和游戏规则。
    -   为客户端提供 REST API (`/v1/chat/completions`)。

## 3. 安装指南

### 服务端要求
1.  安装 Python 3.8+。
2.  安装依赖：
    ```bash
    cd Server
    pip install -r requirements.txt
    ```

### Unity 要求
-   Unity 2021.3 或更高版本（推荐）。
-   将 `Client` 文件夹作为 Unity 项目打开。

## 4. 配置

### API Key (后端)
服务器默认使用 **OpenRouter** 访问 LLM。
1.  在 `Server/` 目录下创建一个名为 `.env` 的文件。
2.  添加你的 Key：
    ```env
    OPENROUTER_API_KEY=sk-or-v1-your-key-here
    ```
    *如果使用 DeepSeek 或其他服务商：*
    ```env
    OPENROUTER_API_KEY=your-deepseek-key
    LLM_BASE_URL=https://api.deepseek.com
    LLM_MODEL=deepseek-chat
    ```

### 游戏逻辑 (提示词)
你可以无需修改代码即可自定义游戏规则和剧情。直接编辑 `Server/data/prompts/` 下的文本文件：
-   **`Prompt_CoreRules.txt`**：游戏机制（数值、胜负条件）。
-   **`Prompt_World.txt`**：世界观设定（城市、学校）。
-   **`Prompt_Characters.txt`**：角色性格和说话风格。

### 角色数据
-   **`Server/data/candidates.json`**：定义可用角色的列表（ID、名字、描述）。

## 5. 运行步骤

### 第一步：启动服务器
在 `Server` 目录下打开终端：
```bash
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

### 第二步：运行客户端
1.  打开 Unity。
2.  打开 **CharacterSelection** 场景（在 `Assets/Scenes` 中，或自行创建）。
3.  点击 **Play**。
4.  选择 3 名室友并点击 **Start Game**。

## 6. 开发指南

### 目录结构
-   **Client/Assets/Scripts/**
    -   `Core/`: 核心游戏逻辑 (`GameDirector.cs`)。
    -   `UI/`: UI 管理器 (`ChatUIManager.cs`, `CharacterSelection.cs`)。
    -   `UI/Character/`: 角色预制件逻辑 (`CharacterPresenter.cs`)。
    -   `Network/`: API 通信 (`LLMClient.cs`)。
    -   `Data/`: 数据模型 (`DataModels.cs`)。
-   **Server/**
    -   `src/`: 源代码 (`api.py`, `services/`, `core/`)。
    -   `data/`: 配置文件 (`prompts/`, `candidates.json`)。

### 添加新角色
1.  **服务端**：在 `Server/data/prompts/Prompt_Characters.txt` 中添加其性格描述。
2.  **服务端**：在 `Server/data/candidates.json` 中添加其元数据（ID、名字）。
3.  **Unity**：
    -   为角色创建一个 **UI Prefab**（包含 Image + Bubble）。
    -   将 `CharacterPresenter` 脚本挂载到 Prefab 上。
    -   在 Inspector 中设置 `Character Id`（必须与 JSON 匹配）。
    -   将 Prefab 添加到场景中 `ChatUIManager` 的列表中。
