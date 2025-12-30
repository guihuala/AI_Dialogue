using System.Collections;
using System.Collections.Generic;
using UnityEngine;

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
    public List<string> activeRoommates = new List<string>();

    // --- 数据结构：聊天记录 ---
    public struct ChatLog
    {
        public string speaker;
        public string content;
    }
    private List<ChatLog> chatHistory = new List<ChatLog>();

    // --- 初始化 ---
    void Start()
    {
        // 绑定 HUD 的选项点击事件
        if (hud != null) 
        {
            hud.OnOptionSelected += HandlePlayerChoice;
        }
        else
        {
            Debug.LogError("GameManager: HUD reference is missing!");
        }
    }

    // --- 游戏流程控制 ---

    // 1. 开始新游戏 (由选人界面调用)
    public void StartNewGame(List<string> selectedChars)
    {
        chatHistory.Clear();
        activeRoommates = new List<string>(selectedChars);

        Debug.Log($"游戏开始！室友: {string.Join(", ", activeRoommates)}");
        SetGameState(GameState.Playing);
        
        // 初始化 HUD 立绘
        if(hud != null) hud.InitializeRoommates(activeRoommates);

        // 立即开始第一个回合（生成选项）
        StartNewTurn();
    }

    // 2. 开启新回合：请求 AI 生成选项
    public void StartNewTurn()
    {
        if (currentState != GameState.Playing) return;

        Debug.Log("Waiting for AI options...");
        
        // 调用 NetworkService 的 GetOptions 接口
        // 注意：你需要确保 NetworkService.cs 中已经添加了 GetOptionsCoroutine 方法
        StartCoroutine(networkService.GetOptionsCoroutine(
            activeRoommates,
            (res) => {
                // 成功：让 HUD 显示 3 个按钮
                hud.ShowOptions(res.options);
            },
            (err) => hud.ShowError("获取选项失败: " + err)
        ));
    }

    // 3. 处理玩家选择
    private void HandlePlayerChoice(string choice)
    {
        if (currentState != GameState.Playing) return;

        // A. 先在屏幕上显示玩家说的话 (即刻反馈)
        hud.AppendMessage("Player", choice, Color.cyan); 

        // B. 发送给后端，请求演出结果
        StartCoroutine(networkService.PerformActionCoroutine(
            choice,
            activeRoommates,
            (res) => {
                // C. 收到回复后：
                
                // 1. 更新数值
                hud.UpdatePlayerStats(res.player_stats);
                
                // 2. 检查是否游戏结束 (SAN归零等)
                if (res.player_stats.san <= 0)
                {
                    EndGame();
                    return;
                }

                // 3. 播放连续对话动画
                // 这是一个 List<DialogueTurn>，HUD 会一个接一个播放
                StartCoroutine(hud.PlayDialogueSequence(res.dialogue_sequence, () => {
                    // 4. 播放完毕后，自动进入下一回合 (再次生成选项)
                    StartNewTurn();
                }));
            },
            (err) => hud.ShowError("执行动作失败: " + err)
        ));
    }

    // --- 辅助方法 ---

    public List<ChatLog> GetChatHistory() => chatHistory;

    public void AddChatLog(string speaker, string content)
    {
        chatHistory.Add(new ChatLog { speaker = speaker, content = content });
    }

    // --- 状态机 ---

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
    public void ResumeGame() => SetGameState(GameState.Playing);
    public void EndGame() => SetGameState(GameState.GameOver);
    
    public void ReturnToMainMenu()
    {
        // 清理数据，返回主菜单场景
        chatHistory.Clear();
        activeRoommates.Clear();
        UnityEngine.SceneManagement.SceneManager.LoadScene("MainMenuScene");
    }
}