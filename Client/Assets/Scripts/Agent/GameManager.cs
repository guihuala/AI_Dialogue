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
    
    [Header("Data")] [SerializeField] private string playerName = "ArtStudent_01";
    public List<string> activeRoommates = new List<string>();
    
    [Header("Auto Save")]
    // 开启/关闭定时自动保存的开关
    public bool enableTimerAutoSave = true;
    public float autoSaveInterval = 300f; // 默认 5 分钟 (300秒) 保存一次
    private Coroutine autoSaveCoroutine;

    private int currentSlotId = -1;
    private int currentSan = 100;
    private float currentMoney = 2000f;
    private float currentGpa = 4.0f;
    private int argCount = 0;
    private int currentChapter = 1;
    private int currentTurn = 0;
    private string currentEvtId = "";
    private bool isAwaitingTransition = false;

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
            int slotId = PlayerPrefs.GetInt("SelectedSlotID", 1);
            
            // 清理标记
            PlayerPrefs.SetInt("IsContinuingGame", 0);
            PlayerPrefs.Save();

            // 调用你之前写好的读档方法
            LoadGameFromSlot(slotId);
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

        StartCoroutine(NetworkService.Instance.StartGameCoroutine(
            activeRoommates,
            (res) =>
            {
                HandleTurnResponse(res, "");
                if (autoSaveCoroutine != null) StopCoroutine(autoSaveCoroutine);
                if (enableTimerAutoSave) autoSaveCoroutine = StartCoroutine(TimerAutoSaveRoutine());
            },
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
        
        // 决定这个回合播完之后，是否已经结束当前事件
        isAwaitingTransition = res.is_end;
        
        if (res.is_end)
        {
            AutoSaveGame();
        }

        OnPlayDialogueSequence?.Invoke(dts, () => { 
            if (res.next_options != null && res.next_options.Count > 0)
            {
                OnShowOptions?.Invoke(res.next_options);
            }
        });

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

        StartCoroutine(NetworkService.Instance.PlayTurnCoroutine(
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
    
    [Header("Save System")]
    private string currentSaveId = "";
    
    // ==========================================
    // 💾 存档与读档核心业务
    // ==========================================
    
    
    /// <summary>
    /// 执行静默自动存档（覆盖当前所在的槽位）
    /// </summary>
    public void AutoSaveGame()
    {
        // 🌟 防御性检查：如果当前是新游戏且从未存过档，跳过自动保存
        // (如果不加这句，可能会因为 currentSlotId = -1 导致后端报错)
        if (currentSlotId < 1 || currentSlotId > 3)
        {
            Debug.Log("[AutoSave] 当前游戏尚未绑定槽位，已跳过自动保存。请先手动存档一次！");
            return;
        }

        // 收集当前所有的核心状态
        SaveGameRequest req = new SaveGameRequest
        {
            slot_id = this.currentSlotId, // 🌟 核心修改：动态使用当前绑定的槽位
            active_roommates = this.activeRoommates,
            current_evt_id = this.currentEvtId,
            chapter = this.currentChapter,
            turn = this.currentTurn,
            san = this.currentSan,
            money = this.currentMoney,
            gpa = this.currentGpa,
            arg_count = this.argCount,
            wechat_data_list = WeChatApp.Instance != null ? WeChatApp.Instance.ExportChatHistory() : new List<WeChatSession>()
        };
        
        StartCoroutine(NetworkService.Instance.SaveGameCoroutine(req, (res) =>
            {
                Debug.Log($"[AutoSave] 游戏已自动保存至云端 (覆盖当前槽位 {this.currentSlotId})。");
            }, 
            (err) => 
            {
                Debug.LogWarning($"[AutoSave] 自动保存失败: {err}");
            }));
    }

    /// <summary>
    /// 定时自动保存的协程
    /// </summary>
    private IEnumerator TimerAutoSaveRoutine()
    {
        while (enableTimerAutoSave)
        {
            yield return new WaitForSeconds(autoSaveInterval);
            
            // 只有在正常游玩状态下才进行定时保存
            if (currentState == GameState.Playing) 
            {
                AutoSaveGame();
            }
        }
    }
    
    /// <summary>
    /// 从指定槽位加载数据并恢复游戏状态
    /// </summary>
    public void LoadGameFromSlot(int slotId)
    {
        StartCoroutine(NetworkService.Instance.LoadGameCoroutine(slotId, (res) =>
        {
            Debug.Log($"[Load] 读取槽位 {slotId} 成功，正在恢复游戏状态...");
            currentSlotId = slotId;
            PlayerPrefs.SetInt("LastPlayedSlot", slotId);
            
            // 1. 恢复 GameManager 的内存状态
            this.activeRoommates = res.data.active_roommates;
            this.currentEvtId = res.data.current_evt_id;
            this.currentChapter = res.data.chapter;
            this.currentTurn = res.data.turn;
            this.currentSan = res.data.san;
            this.currentMoney = res.data.money;
            this.currentGpa = res.data.gpa;
            this.argCount = res.data.arg_count;

            // 如果有微信聊天记录，推给微信管理器恢复
            if (WeChatApp.Instance != null && res.data.wechat_data_list != null)
            {
                WeChatApp.Instance.ImportChatHistory(res.data.wechat_data_list);
            }

            // 2. 派发事件，强制刷新所有的 UI 面板 (顶部状态栏、人物栏等)
            OnInitRoommates?.Invoke(activeRoommates);
            PlayerStatsData stats = new PlayerStatsData { san = currentSan, money = currentMoney, gpa = currentGpa };
            GameTimeData timeData = new GameTimeData { year = $"第 {currentChapter} 章", month = currentChapter, week = currentTurn };
            OnStatsRefreshed?.Invoke(stats, timeData, currentEvtId);

            // 3. 向后端发一个“空动作”以获取当前的剧情文本和选项，完成无缝续借
            SendTurnRequest("【继续游戏】", true);
        }, 
        (err) => 
        {
            Debug.LogError($"[Load] 读取槽位 {slotId} 失败: {err}");
            ShowSystemError("读取存档失败: " + err);
            
            if (autoSaveCoroutine != null) StopCoroutine(autoSaveCoroutine);
            if (enableTimerAutoSave) autoSaveCoroutine = StartCoroutine(TimerAutoSaveRoutine());
        }));
    }
    
    // ==========================================
    // 🔄 核心回合调度辅助方法
    // ==========================================

    /// <summary>
    /// 封装向后端发送回合请求的逻辑
    /// (读档恢复画面、或者玩家点击选项时均可调用此方法)
    /// </summary>
    public void SendTurnRequest(string choiceText, bool isTransition = false)
    {
        GameTurnRequest req = new GameTurnRequest
        {
            choice = choiceText,
            active_roommates = this.activeRoommates,
            current_evt_id = this.currentEvtId,
            is_transition = isTransition,
            chapter = this.currentChapter,
            turn = this.currentTurn,
            san = this.currentSan,
            money = this.currentMoney,
            gpa = this.currentGpa,
            arg_count = this.argCount,
            // 同步最新的微信聊天记录给后端，供大模型参考
            wechat_data_list = WeChatApp.Instance != null ? WeChatApp.Instance.ExportChatHistory() : new List<WeChatSession>()
        };

        // 发送网络请求 (请确保你的 NetworkService 中有 PlayTurnCoroutine 方法)
        StartCoroutine(NetworkService.Instance.PlayTurnCoroutine(
            req,
            (res) => HandleTurnResponse(res, choiceText), // 处理后端返回的剧情
            (err) => ShowSystemError("网络请求失败: " + err)
        ));
    }
}