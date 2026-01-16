using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Serialization;

public class GameManager : Singleton<GameManager>
{
    public enum GameState { Playing, Paused, GameOver }
    private GameState currentState;

    [Header("Controllers")]
    [SerializeField] private NetworkService networkService;
    [SerializeField] private TopBarController topBar; // 新增：引用顶部状态栏
    [SerializeField] private StageController stage;   // 新增：引用演出舞台

    [Header("Data")]
    [SerializeField] private string playerName = "ArtStudent_01";
    public List<string> activeRoommates = new List<string>();

    public struct ChatLog { public string speaker; public string content; }
    private List<ChatLog> chatHistory = new List<ChatLog>();

    void Start()
    {
        // 绑定舞台的选项选择事件
        if (stage != null)
        {
            stage.OnOptionSelected += HandlePlayerChoice;
        }
    }

    // --- 游戏流程 ---

    public void StartNewGame(List<string> selectedChars)
    {
        chatHistory.Clear();
        activeRoommates = new List<string>(selectedChars);
        
        SetGameState(GameState.Playing);

        // 1. 初始化舞台立绘
        if(stage != null) stage.InitializeRoommates(activeRoommates);
        
        // 2. 初始刷新一下顶部栏 (可选，设为默认值)
        // if(topBar != null) topBar.Refresh(...);

        // 3. 开始回合
        StartNewTurn();
    }

    public void StartNewTurn()
    {
        if (currentState != GameState.Playing) return;

        StartCoroutine(networkService.GetOptionsCoroutine(
            activeRoommates,
            (res) => {
                if(stage != null) stage.ShowOptions(res.options);
            },
            (err) => ShowSystemError(err)
        ));
    }

    private void HandlePlayerChoice(string choice)
    {
        if (currentState != GameState.Playing) return;

        // 在舞台上立即显示玩家说的话
        stage.ShowImmediateMessage("Player", choice, Color.cyan);
        AddChatLog("Player", choice);

        StartCoroutine(networkService.PerformActionCoroutine(
            choice,
            activeRoommates,
            (res) => {
                // A. 更新顶部状态栏 (金钱、时间、事件)
                if (topBar != null)
                {
                    topBar.Refresh(res.player_stats, res.game_time, res.current_event);
                }

                // B. 检查游戏失败
                // (此处可以扩充：如果 GameTime 到了第4年，触发毕业结局等)
                if (res.player_stats.san <= 0) 
                {
                    EndGame(); // 简单处理
                }

                // C. 舞台开始表演
                if (stage != null)
                {
                    StartCoroutine(stage.PlayDialogueSequence(res.dialogue_sequence, () => {
                        StartNewTurn(); // 表演完，进入下一轮
                    }));
                }
            },
            (err) => ShowSystemError(err)
        ));
    }

    private void ShowSystemError(string error)
    {
        Debug.LogError(error);
        if (stage != null) stage.ShowImmediateMessage("System Error", $"<color=red>{error}</color>", Color.red);
    }

    // --- 辅助 ---
    public List<ChatLog> GetChatHistory() => chatHistory;
    public void AddChatLog(string s, string c) => chatHistory.Add(new ChatLog { speaker = s, content = c });


    public void SetGameState(GameState newState)
    {
        currentState = newState;
        switch (newState)
        {
            case GameState.Playing:
                Time.timeScale = 1;
                // 如果有 UIManager，这里关闭菜单
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
                Debug.Log("GAME OVER");
                // if(UIManager.Instance) UIManager.Instance.OpenPanel("GameResultPanel");
                break;
        }
    }

    public void PauseGame() => SetGameState(GameState.Paused);
    public void EndGame() => SetGameState(GameState.GameOver);
    public void ResumeGame() => SetGameState(GameState.Playing);

    public void ReturnToMainMenu()
    {
        // 清理数据，返回主菜单场景
        chatHistory.Clear();
        activeRoommates.Clear();
        UnityEngine.SceneManagement.SceneManager.LoadScene("MainMenuScene");
    }
}