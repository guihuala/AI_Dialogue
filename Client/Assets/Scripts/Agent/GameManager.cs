using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Serialization;

public class GameManager : Singleton<GameManager>
{
    public enum GameState
    {
        Playing,    // 游戏进行中
        Paused,     // 游戏暂停
        GameOver    // 游戏结束
    }

    private GameState currentState;

    [Header("Core References")]
    [SerializeField] private NetworkService networkService;
    [SerializeField] private HudController hud; 

    [Header("Player Settings")]
    [SerializeField] private string playerName = "ArtStudent_01";
    
    [Header("Roommate State")]
    // 存储当前选中的 3 个室友 ID
    public List<string> activeRoommates = new List<string>();

    // --- 初始化 ---
    void Start()
    {
        // 不再自动 StartGame，而是等待 UI 选择
        // StartGame(); 
        
        // 初始化监听 HUD 发送消息
        if (hud != null) hud.OnSendRequest += HandleChatRequest;
    }

    // --- 新增：由选人界面调用 ---
    public void StartNewGame(List<string> selectedChars)
    {
        activeRoommates = new List<string>(selectedChars);
        Debug.Log($"游戏开始！室友: {string.Join(", ", activeRoommates)}");
        
        // 这里可以通知 Backend 初始化这 3 个人的数据 (可选，目前是Lazy Load)
        
        SetGameState(GameState.Playing);
        
        // 初始化 HUD 的下拉框，只显示这 3 个人
        if(hud != null) hud.InitializeRoommates(activeRoommates);
    }

    // --- 修改：处理玩家发送消息 ---
    private void HandleChatRequest(string content, string targetId)
    {
        if (currentState != GameState.Playing) return;

        // 这里继续用之前的逻辑
        StartCoroutine(networkService.SendMessageCoroutine(
            content, targetId, playerName, OnChatSuccess, OnChatFailure
        ));
    }
    
    // --- 新增：核心功能 "观察 (Participatory Observation)" ---
    // 这个方法绑定在 UI 的 "观察/下一回合" 按钮上
    public void ObserveNextTurn()
    {
        if (currentState != GameState.Playing) return;

        // 随机挑选两个在场的室友进行互动，或者由后端决定
        // 我们只需要告诉后端：现在是“观察模式”，请推进剧情
        StartCoroutine(networkService.SendObserveRequest(
            activeRoommates, // 把当前在场的名单发给后端
            OnChatSuccess,   // 复用成功的处理逻辑（显示对话）
            OnChatFailure
        ));
    }
    
    private void OnChatSuccess(GroupChatResponse res)
    {
        // 1. 在 UI 上显示 AI 回复
        // 你可以在这里加逻辑：比如根据 mood 改变颜色
        Color nameColor = Color.yellow; 
        hud.AppendMessage(res.speaker, res.response, nameColor);

        // 2. 更新 UI 上的玩家属性 (SAN/GPA/Money)
        hud.UpdatePlayerStats(res.player_stats);
        
        // 3. (可选) 游戏结束判定
        // 比如：如果 SAN 值归零，触发 GameOver
        if (res.player_stats.san <= 0)
        {
            Debug.Log("SAN值耗尽，游戏结束！");
            EndGame();
        }
    }

    private void OnChatFailure(string error)
    {
        hud.ShowError(error);
    }

    // --- 原有的状态控制逻辑 (保持不变或微调) ---

    public void SetGameState(GameState newState)
    {
        currentState = newState;

        switch (newState)
        {
            case GameState.Playing:
                Time.timeScale = 1;
                // 假设你有全局 UI 管理器来关菜单
                if(UIManager.Instance) 
                {
                    UIManager.Instance.ClosePanel("SettingPanel");
                    UIManager.Instance.ClosePanel("GameResultPanel");
                }
                break;

            case GameState.Paused:
                Time.timeScale = 0;
                if(UIManager.Instance) UIManager.Instance.OpenPanel("SettingPanel");
                break;

            case GameState.GameOver:
                Time.timeScale = 0;
                if(UIManager.Instance) UIManager.Instance.OpenPanel("GameResultPanel");
                break;
        }
    }

    #region 状态控制方法

    public void StartGame()
    {
        SetGameState(GameState.Playing);
    }

    public void PauseGame()
    {
        if (currentState == GameState.Playing)
        {
            SetGameState(GameState.Paused);
        }
    }

    public void ResumeGame()
    {
        if (currentState == GameState.Paused)
        {
            SetGameState(GameState.Playing);
        }
    }

    public void EndGame()
    {
        SetGameState(GameState.GameOver);
        // 这里可以通知 GameplayUI 显示结算信息
        // hud.ShowGameOver(...)
    }

    public void ReturnToMainMenu()
    {
        SetGameState(GameState.Playing);
        // SceneLoader.Instance.LoadScene(GameScene.MainMenu); // 假设你有 SceneLoader
    }

    #endregion
}