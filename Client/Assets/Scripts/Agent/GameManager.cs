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

    private int currentSan = 100;
    private float currentMoney = 2000f;
    private float currentGpa = 4.0f;
    private int argCount = 0;
    private int currentChapter = 1;
    private int currentTurn = 0;
    private string currentEvtId = "";
    private bool isAwaitingTransition = false; // Add flag for transitioning from a finished event

    [Serializable]
    public struct ChatLog
    {
        public string speaker;
        public string content;
    }

    [Serializable]
    private class ChatLogWrapper
    {
        public List<ChatLog> logs = new List<ChatLog>();
    }

    private List<ChatLog> chatHistory = new List<ChatLog>();

    // --- 定义UI需要监听的事件 ---
    public event Action<List<string>> OnInitRoommates;
    public event Action<List<string>> OnShowOptions;
    public event Action<string, string, Color> OnShowImmediateMessage;
    public event Action<PlayerStatsData, GameTimeData, string> OnStatsRefreshed;
    public event Action<string> OnEventNotified;
    public event Action<List<DialogueTurn>, Action> OnPlayDialogueSequence;
    public event Action<List<WeChatNotification>> OnWeChatNotified;

    // --- 游戏流程 ---
    private IEnumerator Start()
    {
        // 等待一帧，确保 StageController 等 UI 已经完成了事件订阅
        yield return null; 

        if (PlayerPrefs.GetInt("IsContinuingGame", 0) == 1)
        {
            // 继续游戏，清理游玩标记避免死循环
            PlayerPrefs.SetInt("IsContinuingGame", 0);
            PlayerPrefs.Save();
            LoadLocalProgress();
        }
        else
        {
            // 从跨场景总线中读取选中的角色
            List<string> charsToLoad = GameContext.SelectedRoommates;

            // 默认数据防报错（用于直接在Gameplay场景测试）
            if (charsToLoad == null || charsToLoad.Count == 0)
            {
                Debug.LogWarning("[GameManager] 未检测到选人数据，正在使用默认测试阵容！");
                charsToLoad = new List<string> { "tang_mengqi", "li_yinuo", "chen_yuting" };
            }

            StartNewGame(charsToLoad);
        }
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

        currentSan = 100;
        currentMoney = 2000f;
        currentGpa = 4.0f;
        argCount = 0;
        currentChapter = 1;
        currentTurn = 0;
        currentEvtId = "";
        isAwaitingTransition = false;

        if (OnInitRoommates == null) Debug.LogWarning("[GameManager] 警告: OnInitRoommates 没有人订阅！UI可能未准备好。");
        OnInitRoommates?.Invoke(activeRoommates);

        StartCoroutine(networkService.StartGameCoroutine(
            activeRoommates,
            (res) => HandleTurnResponse(res, ""),
            (err) => ShowSystemError(err)
        ));
    }

    private void HandleTurnResponse(GameTurnResponse res, string choice)
    {
        if (!string.IsNullOrEmpty(res.error))
        {
            ShowSystemError($"后端大模型生成异常:\n{res.error}");
            return;
        }

        currentSan = res.san;
        currentMoney = res.money;
        currentGpa = res.gpa;
        argCount = res.arg_count;
        currentChapter = res.chapter;
        currentTurn = res.turn;
        currentEvtId = res.current_evt_id;
        
        PlayerStatsData stats = new PlayerStatsData { san = res.san, money = res.money, gpa = res.gpa };
        GameTimeData timeData = new GameTimeData { year = $"第 {res.chapter} 章", month = res.chapter, week = res.turn };

        OnStatsRefreshed?.Invoke(stats, timeData, res.current_evt_id);
        OnEventNotified?.Invoke(res.current_evt_id);

        if (res.wechat_notifications != null && res.wechat_notifications.Count > 0)
        {
            OnWeChatNotified?.Invoke(res.wechat_notifications);
        }

        if (res.is_game_over || res.san <= 0)
        {
            EndGame();
        }

        // 统一构建对话序列用于展示
        List<DialogueTurn> dts = new List<DialogueTurn>();
        
        // 如果有旁白，先塞一句旁白
        if (!string.IsNullOrEmpty(res.narrator_transition))
        {
            dts.Add(new DialogueTurn { speaker = "剧情推进", content = res.narrator_transition, mood = "neutral" });
        }
        
        // 加上实际的大模型生成的角色台词
        if (res.dialogue_sequence != null && res.dialogue_sequence.Count > 0)
        {
            dts.AddRange(res.dialogue_sequence);
        }
        else if (string.IsNullOrEmpty(res.narrator_transition))
        {
            // 如果连旁白和对话都没有，兜底直接扔出 display_text （处理早期的纯文本）
            dts.Add(new DialogueTurn { speaker = "剧情推进", content = res.display_text, mood = "neutral" });
        }

        if (OnPlayDialogueSequence == null)
            Debug.LogWarning("[GameManager] 警告: OnPlayDialogueSequence 没人监听！对话不会播放！");

        // 决定这个回合播完之后，是否已经结束当前事件，如果结束了，下次点击按钮就进入下个事件
        isAwaitingTransition = res.is_end;

        OnPlayDialogueSequence?.Invoke(dts, () => { 
            if (res.next_options != null && res.next_options.Count > 0)
            {
                OnShowOptions?.Invoke(res.next_options);
            }
        });
    }

    public void HandlePlayerChoice(string choice)
    {
        Debug.Log($"[GameManager] 玩家做出了选择: {choice}");
        if (currentState != GameState.Playing) return;

        OnShowImmediateMessage?.Invoke("Player", choice, Color.cyan);
        AddChatLog("Player", choice);

        GameTurnRequest req = new GameTurnRequest {
            choice = choice,
            active_roommates = activeRoommates,
            current_evt_id = currentEvtId,
            is_transition = isAwaitingTransition, // 动态使用上回合结束返回的标记
            chapter = currentChapter,
            turn = currentTurn,
            san = currentSan,
            money = currentMoney,
            gpa = currentGpa,
            arg_count = argCount,
            wechat_data_list = WeChatApp.Instance != null ? WeChatApp.Instance.ExportChatHistory() : new List<WeChatSession>()
        };

        StartCoroutine(networkService.PlayTurnCoroutine(
            req,
            (res) => HandleTurnResponse(res, choice),
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
    public void EndGame()
    {
        PlayerPrefs.SetInt("HasSaveData", 0); // 结束游戏清除存档标记
        PlayerPrefs.Save();
        SetGameState(GameState.GameOver);
    }
    public void ResumeGame() => SetGameState(GameState.Playing);

    private void SaveLocalProgress()
    {
        PlayerPrefs.SetInt("HasSaveData", 1);
        PlayerPrefs.SetInt("currentSan", currentSan);
        PlayerPrefs.SetFloat("currentMoney", currentMoney);
        PlayerPrefs.SetFloat("currentGpa", currentGpa);
        PlayerPrefs.SetInt("argCount", argCount);
        PlayerPrefs.SetInt("currentChapter", currentChapter);
        PlayerPrefs.SetInt("currentTurn", currentTurn);
        PlayerPrefs.SetString("currentEvtId", currentEvtId);
        PlayerPrefs.SetInt("isAwaitingTransition", isAwaitingTransition ? 1 : 0);
        
        PlayerPrefs.SetString("activeRoommates", string.Join(",", activeRoommates));
        
        ChatLogWrapper wrapper = new ChatLogWrapper { logs = chatHistory };
        PlayerPrefs.SetString("chatHistory", JsonUtility.ToJson(wrapper));

        PlayerPrefs.Save();
        Debug.Log("[GameManager] Local progress saved.");
    }

    private void LoadLocalProgress()
    {
        currentSan = PlayerPrefs.GetInt("currentSan", 100);
        currentMoney = PlayerPrefs.GetFloat("currentMoney", 2000f);
        currentGpa = PlayerPrefs.GetFloat("currentGpa", 4.0f);
        argCount = PlayerPrefs.GetInt("argCount", 0);
        currentChapter = PlayerPrefs.GetInt("currentChapter", 1);
        currentTurn = PlayerPrefs.GetInt("currentTurn", 0);
        currentEvtId = PlayerPrefs.GetString("currentEvtId", "");
        isAwaitingTransition = PlayerPrefs.GetInt("isAwaitingTransition", 0) == 1;

        string rmStr = PlayerPrefs.GetString("activeRoommates", "");
        if (!string.IsNullOrEmpty(rmStr)) activeRoommates = new List<string>(rmStr.Split(','));

        string chatJson = PlayerPrefs.GetString("chatHistory", "");
        if (!string.IsNullOrEmpty(chatJson))
        {
            ChatLogWrapper wrapper = JsonUtility.FromJson<ChatLogWrapper>(chatJson);
            if (wrapper != null && wrapper.logs != null) chatHistory = wrapper.logs;
        }

        SetGameState(GameState.Playing);

        if (OnInitRoommates == null) Debug.LogWarning("[GameManager] 警告: OnInitRoommates 没有人订阅！UI可能未准备好。");
        OnInitRoommates?.Invoke(activeRoommates);

        // Notify Stats UI
        PlayerStatsData stats = new PlayerStatsData { san = currentSan, money = currentMoney, gpa = currentGpa };
        GameTimeData timeData = new GameTimeData { year = $"第 {currentChapter} 章", month = currentChapter, week = currentTurn };
        OnStatsRefreshed?.Invoke(stats, timeData, currentEvtId);

        // Resume game via backend by sending an empty choice / transition
        GameTurnRequest req = new GameTurnRequest
        {
            choice = "【继续游戏】",
            active_roommates = activeRoommates,
            current_evt_id = currentEvtId,
            is_transition = true,
            chapter = currentChapter,
            turn = currentTurn,
            san = currentSan,
            money = currentMoney,
            gpa = currentGpa,
            arg_count = argCount,
            //affinity = new AffinityDictionary(),
            wechat_data_list = WeChatApp.Instance != null ? WeChatApp.Instance.ExportChatHistory() : new List<WeChatSession>()
        };

        StartCoroutine(networkService.PlayTurnCoroutine(
            req,
            (res) => HandleTurnResponse(res, "【继续游戏】"),
            (err) => ShowSystemError(err)
        ));
    }

    public void ReturnToMainMenu()
    {
        // 清理数据，返回主菜单场景
        chatHistory.Clear();
        activeRoommates.Clear();
        UnityEngine.SceneManagement.SceneManager.LoadScene("MainMenuScene");
    }
}