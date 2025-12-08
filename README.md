# AI Visual Novel Project Documentation
[English](README.md) | [中文](README_CN.md)

## 1. Project Overview
This is a **Visual Novel (Galgame)** project powered by a **Local LLM**. It combines a **Unity Client** for the visual interface with a **Python Backend** for AI logic and memory management.

### Key Features
-   **Sidecar Architecture**: Unity handles the UI, while Python handles the AI.
-   **Visual Novel UI**: Character sprites, dialogue bubbles, and options.
-   **Dynamic Story**: The story is generated in real-time by the LLM based on game rules and character profiles.
-   **Game Loop**: A 12-day survival cycle with stats (Money, Sanity, GPA).

## 2. Architecture
-   **Client (Unity)**:
    -   Located in `Client/`.
    -   Responsible for rendering, user input, and game state display.
    -   Communicates with the Server via HTTP (Streaming API).
-   **Server (Python)**:
    -   Located in `Server/`.
    -   Host the LLM logic, Memory System (Vector DB), and Game Rules.
    -   Exposes a REST API (`/v1/chat/completions`) for the client.

## 3. Installation

### Server Requirements
1.  Install Python 3.8+.
2.  Install dependencies:
    ```bash
    cd Server
    pip install -r requirements.txt
    ```

### Unity Requirements
-   Unity 2021.3 or later (recommended).
-   Open the `Client` folder as a Unity Project.

## 4. Configuration

### API Key (Backend)
The server uses **OpenRouter** to access LLMs.
1.  Create a file named `.env` in the `Server/` directory.
2.  Add your API key:
    ```env
    OPENROUTER_API_KEY=sk-or-v1-your-key-here
    ```
    *If using DeepSeek or other providers:*
    ```env
    OPENROUTER_API_KEY=your-deepseek-key
    LLM_BASE_URL=https://api.deepseek.com
    LLM_MODEL=deepseek-chat
    ```

### Game Logic (Prompts)
You can customize the game rules and story without touching code. Edit the text files in `Server/data/prompts/`:
-   **`Prompt_CoreRules.txt`**: Game mechanics (Stats, Win/Loss conditions).
-   **`Prompt_World.txt`**: World setting (City, School).
-   **`Prompt_Characters.txt`**: Character personalities and speaking styles.

### Character Data
-   **`Server/data/candidates.json`**: Defines the list of available characters (ID, Name, Description).

## 5. How to Run

### Step 1: Start the Server
Open a terminal in the `Server` directory:
```bash
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Run the Client
1.  Open Unity.
2.  Open the **CharacterSelection** scene (in `Assets/Scenes` or create one).
3.  Press **Play**.
4.  Select 3 roommates and click **Start Game**.

## 6. Development Guide

### Directory Structure
-   **Client/Assets/Scripts/**
    -   `Core/`: Main game logic (`GameDirector.cs`).
    -   `UI/`: UI Managers (`ChatUIManager.cs`, `CharacterSelection.cs`).
    -   `UI/Character/`: Character Prefab logic (`CharacterPresenter.cs`).
    -   `Network/`: API communication (`LLMClient.cs`).
    -   `Data/`: Data models (`DataModels.cs`).
-   **Server/**
    -   `src/`: Source code (`api.py`, `services/`, `core/`).
    -   `data/`: Configuration files (`prompts/`, `candidates.json`).

### Adding a New Character
1.  **Server**: Add their personality to `Server/data/prompts/Prompt_Characters.txt`.
2.  **Server**: Add their metadata to `Server/data/candidates.json`.
3.  **Unity**:
    -   Create a **UI Prefab** for the character (Image + Bubble).
    -   Attach `CharacterPresenter` script to the prefab.
    -   Set the `Character Id` in the Inspector (must match JSON).
    -   Add the prefab to the `ChatUIManager` list in the scene.
