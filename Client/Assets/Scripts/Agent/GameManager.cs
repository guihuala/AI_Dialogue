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

    // --- 初始化 ---
    void Start()
    {
        // 游戏启动时，默认进入 Playing 状态
        StartGame();
        
        if (hud != null)
        {
            hud.OnSendRequest += HandleChatRequest;
        }
        else
        {
            Debug.LogError("GameManager: GameplayUI reference is missing!");
        }
    }
    
    // --- 核心聊天逻辑 ---
    
    private void HandleChatRequest(string content, string targetId)
    {
        // 如果游戏暂停或结束，禁止发送消息
        if (currentState != GameState.Playing) return;

        // 调用网络服务
        StartCoroutine(networkService.SendMessageCoroutine(
            content, 
            targetId, 
            playerName,
            OnChatSuccess, 
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