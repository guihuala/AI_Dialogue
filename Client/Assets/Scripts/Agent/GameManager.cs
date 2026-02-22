using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Serialization;

public class GameManager : Singleton<GameManager>
{
    public enum GameState
    {
        Playing,
        Paused,
        GameOver
    }

    private GameState currentState;

    [Header("Controllers")] [SerializeField]
    private NetworkService networkService; // 网络服务可以挂在子节点或同样持久化

    [Header("Data")] [SerializeField] private string playerName = "ArtStudent_01";
    public List<string> activeRoommates = new List<string>();

    public struct ChatLog
    {
        public string speaker;
        public string content;
    }

    private List<ChatLog> chatHistory = new List<ChatLog>();

    // --- 定义UI需要监听的事件 ---
    public event Action<List<string>> OnInitRoommates;
    public event Action<List<string>> OnShowOptions;
    public event Action<string, string, Color> OnShowImmediateMessage;
    public event Action<PlayerStatsData, GameTimeData, string> OnStatsRefreshed;
    public event Action<string> OnEventNotified;
    public event Action<List<DialogueTurn>, Action> OnPlayDialogueSequence;

    // --- 游戏流程 ---
    private void Start()
    {
        // 从跨场景总线中读取选中的角色
        List<string> charsToLoad = GameContext.SelectedRoommates;

        // 如果在开发时直接从 Gameplay 场景点 Play 运行，静态列表会是空的
        // 这里给个默认数据防止报错，方便你平时测试
        if (charsToLoad == null || charsToLoad.Count == 0)
        {
            Debug.LogWarning("[GameManager] 未检测到选人数据，正在使用默认测试阵容！");
            charsToLoad = new List<string> { "tang_mengqi", "li_yinuo", "chen_yuting" };
        }

        // 启动游戏逻辑
        StartNewGame(charsToLoad);
    }
    
    public void StartNewGame(List<string> selectedChars)
    {
        Debug.Log($"[GameManager] 开始新游戏，选中的室友数量: {selectedChars.Count}");

        if (networkService == null)
        {
            Debug.LogError("[GameManager] 致命错误: networkService 未赋值！请在 Inspector 面板中拖拽对应物体。");
            return;
        }

        chatHistory.Clear();
        activeRoommates = new List<string>(selectedChars);
        SetGameState(GameState.Playing);

        if (OnInitRoommates == null) Debug.LogWarning("[GameManager] 警告: OnInitRoommates 没有人订阅！UI可能未准备好。");
        OnInitRoommates?.Invoke(activeRoommates);

        StartNewTurn();
    }

    public void StartNewTurn()
    {
        Debug.Log("[GameManager] 请求新回合的选项...");
        if (currentState != GameState.Playing) return;

        StartCoroutine(networkService.GetOptionsCoroutine(
            activeRoommates,
            (res) =>
            {
                Debug.Log($"[GameManager] 收到选项，数量: {res?.options?.Count}");
                if (OnShowOptions == null) Debug.LogWarning("[GameManager] 警告: OnShowOptions 没有 UI 订阅监听！");
                OnShowOptions?.Invoke(res.options);
            },
            (err) => ShowSystemError(err)
        ));
    }

    public void HandlePlayerChoice(string choice)
    {
        Debug.Log($"[GameManager] 玩家做出了选择: {choice}");
        if (currentState != GameState.Playing) return;

        OnShowImmediateMessage?.Invoke("Player", choice, Color.cyan);
        AddChatLog("Player", choice);

        StartCoroutine(networkService.PerformActionCoroutine(
            choice,
            activeRoommates,
            (res) =>
            {
                Debug.Log("[GameManager] 收到后端返回的剧本演出，开始广播给UI...");
                OnStatsRefreshed?.Invoke(res.player_stats, res.game_time, res.current_event);
                OnEventNotified?.Invoke(res.current_event);

                if (res.player_stats.san <= 0)
                {
                    EndGame();
                }

                if (OnPlayDialogueSequence == null)
                    Debug.LogWarning("[GameManager] 警告: OnPlayDialogueSequence 没人监听！对话不会播放！");

                OnPlayDialogueSequence?.Invoke(res.dialogue_sequence, () => { StartNewTurn(); });
            },
            (err) => ShowSystemError(err)
        ));
    }

    private void ShowSystemError(string error)
    {
        Debug.LogError(error);
        OnShowImmediateMessage?.Invoke("System Error", $"<color=red>{error}</color>", Color.red);
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
                if (UIManager.Instance)
                {
                    UIManager.Instance.ClosePanel("SettingPanel");
                    UIManager.Instance.ClosePanel("GameResultPanel");
                }

                break;
            case GameState.Paused:
                Time.timeScale = 0;
                if (UIManager.Instance) UIManager.Instance.OpenPanel("SettingPanel");
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