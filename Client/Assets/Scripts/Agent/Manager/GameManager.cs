using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class GameManager : Singleton<GameManager>
{
    [Header("Config")]
    public DialogueSequence introSequenceSO;
    
    public enum GameState { Playing, Paused, GameOver }
    public GameState CurrentState { get; private set; }
    
    public DataManager Data { get; private set; }
    public SaveManager Save { get; private set; }
    
    public float CurrentMoney => Data != null ? Data.currentMoney : 0;
    public int CurrentChapter => Data != null ? Data.currentChapter : 1;
    public int CurrentTurn => Data != null ? Data.currentTurn : 0;

    protected override void Awake()
    {
        base.Awake();
        Data = new DataManager();
        Save = new SaveManager(this);
    }

    private IEnumerator Start()
    {
        yield return null; 

        // 根据 GameContext 的标记决定是走读档流程，还是播片流程
        if (GameContext.IsContinuingGame)
        {
            Save.LoadGameFromSlot(GameContext.SelectedSaveSlot);
            
            // 防御性编程：读档结束后，强行再把当前选中的槽位号绑回去
            // （防止读取的旧废档里 slot_id 是 0，导致覆盖后又无法自动存档）
            Data.currentSlotId = GameContext.SelectedSaveSlot;
        }
        else
        {
            // 如果点的是空槽位，进入新游戏播片流程
            StartNewGameIntro();
        }
    }

    public void StartNewGameIntro()
    {
        // 重置所有新游戏数据
        Data.ResetForNewGame();
        
        Data.currentSlotId = GameContext.SelectedSaveSlot;

        if (PhoneManager.Instance != null)
            PhoneManager.Instance.ImportChatHistory(new List<WeChatSession>());
        
        Data.BroadcastAllStats();

        List<DialogueTurn> seq = introSequenceSO != null ? introSequenceSO.sequence : new List<DialogueTurn>();
        
        MsgCenter.SendMsg(MsgConst.TOGGLE_SKIP_BUTTON, true); 

        MsgCenter.SendMsg(MsgConst.PLAY_DIALOGUE_SEQUENCE, seq,
            (System.Action)(() => { 
                MsgCenter.SendMsg(MsgConst.TOGGLE_SKIP_BUTTON, false); 
                UIManager.Instance.OpenPanel("CharacterSelectionPanel"); 
            }));
    }
    public void SkipIntro()
    {
        Debug.Log("[GameManager] 玩家选择跳过开场剧情。");

        MsgCenter.SendMsg(MsgConst.STOP_DIALOGUE);
        
        // 玩家按了跳过，立刻隐藏跳过按钮
        MsgCenter.SendMsg(MsgConst.TOGGLE_SKIP_BUTTON, false); 
        
        UIManager.Instance.OpenPanel("CharacterSelectionPanel");
    }
    
    // 3. 真正联络后端
    public void StartBackendGame(List<string> selectedRoommates)
    {
        Data.activeRoommates = selectedRoommates;

        // 向后端发车
        StartCoroutine(NetworkService.Instance.StartGameCoroutine(
            selectedRoommates,
            (res) => {
                Save.RestartAutoSave();
                // 收到后端回复后，正式接入 AI 剧情
                HandleTurnResponse(res, "【推开寝室的门】");
            },
            (err) => ShowSystemError("网络请求失败: " + err)
        ));
    }

    // ==========================================
    // 网络回合流转
    // ==========================================
    public void SendTurnRequest(string choiceText, bool isTransition = false)
    {
        Data.isAwaitingTransition = isTransition;
        GameTurnRequest req = new GameTurnRequest
        {
            choice = choiceText,
            active_roommates = Data.activeRoommates,
            current_evt_id = Data.currentEvtId,
            is_transition = isTransition,
            chapter = Data.currentChapter,
            turn = Data.currentTurn,
            san = Data.currentSan,
            money = Data.currentMoney,
            hygiene = Data.currentHygiene,
            reputation = Data.currentReputation,
            gpa = Data.currentGpa,
            arg_count = Data.argCount,
            wechat_data_list = PhoneManager.Instance != null ? PhoneManager.Instance.ExportChatHistory() : new List<WeChatSession>()
        };

        StartCoroutine(NetworkService.Instance.PlayTurnCoroutine(
            req,
            (res) => HandleTurnResponse(res, choiceText),
            (err) => ShowSystemError("网络请求失败: " + err)
        ));
    }

    private void HandleTurnResponse(GameTurnResponse res, string choiceText)
    {
        if (res.is_game_over)
        {
            CurrentState = GameState.GameOver;
            MsgCenter.SendMsg(MsgConst.SHOW_IMMEDIATE_MESSAGE, "系统", "游戏通关或结束！", Color.yellow);
            return;
        }

        // 1. 账单系统拦截与记录
        float moneyDelta = res.money - Data.currentMoney;
        if (Mathf.Abs(moneyDelta) > 0.01f)
        {
            string desc = moneyDelta > 0 ? "剧情变动" : "剧情消费/扣除";
            MsgCenter.SendMsg(MsgConst.ADD_TRANSACTION, moneyDelta, desc, $"第{Data.currentChapter}章");
        }
        
        if (res.active_roommates != null && res.active_roommates.Count > 0)
        {
            Data.activeRoommates = res.active_roommates;
            MsgCenter.SendMsg(MsgConst.INIT_ROOMMATES, Data.activeRoommates);
        }

        // 2. 指挥数据系统更新并广播
        Data.currentSan = res.san;
        Data.currentMoney = res.money;
        Data.currentGpa = res.gpa;
        Data.currentHygiene = res.hygiene; 
        Data.currentReputation = res.reputation;
        Data.currentChapter = res.chapter;
        Data.currentTurn = res.turn;
        Data.argCount = res.arg_count;
        Data.currentEvtId = res.current_evt_id;
        Data.isAwaitingTransition = res.is_end;
        
        Data.BroadcastAllStats();

        // 3. 各种 UI 广播事件分发
        if (res.wechat_notifications != null && res.wechat_notifications.Count > 0)
            MsgCenter.SendMsg(MsgConst.WECHAT_NOTIFIED, res.wechat_notifications);

        if (!string.IsNullOrEmpty(res.current_evt_id))
            MsgCenter.SendMsg(MsgConst.EVENT_NOTIFIED, res.current_evt_id);
        
        // 提取场景并广播给 UI
        if (!string.IsNullOrEmpty(res.current_scene) && res.current_scene != Data.currentScene)
        {
            Data.currentScene = res.current_scene;
            MsgCenter.SendMsg(MsgConst.CHANGE_SCENE, Data.currentScene);
        }

        // 4. 对话序列播放
        var dts = res.dialogue_sequence ?? new List<DialogueTurn>();
        if (!string.IsNullOrEmpty(res.narrator_transition))
            dts.Insert(0, new DialogueTurn { speaker = "系统", content = res.narrator_transition, mood = "平静" });

        MsgCenter.SendMsg(MsgConst.PLAY_DIALOGUE_SEQUENCE, dts, (System.Action)(() => { 
            if (res.next_options != null && res.next_options.Count > 0)
                MsgCenter.SendMsg(MsgConst.SHOW_OPTIONS, res.next_options);
        }));

        // 5. 剧情节点完成，自动存档
        if (res.is_end) Save.AutoSaveGame();
        
        // 6. 反思反馈处理
        if (res.reflection_triggered)
        {
            string logSummary = res.reflection_logs != null ? string.Join("\n", res.reflection_logs) : "无详细记录";
            Debug.Log($"<color=cyan>[AI 反思完成]</color> 总结如下：\n{logSummary}");
    
            // 发送消息通知 UI 层展示（例如弹出一个小气泡或系统消息）
            MsgCenter.SendMsg(MsgConst.SHOW_IMMEDIATE_MESSAGE, "系统", "室友们对最近发生的事情有了新的看法...", Color.cyan);
        }
    }

    public void HandlePlayerChoice(string choice)
    {
        MsgCenter.SendMsg(MsgConst.SHOW_IMMEDIATE_MESSAGE, "Player", choice, Color.cyan);
        SendTurnRequest(choice, Data.isAwaitingTransition);
    }

    public void ShowSystemError(string error)
    {
        Debug.LogError($"[GameManager Error] {error}");
        MsgCenter.SendMsg(MsgConst.SHOW_IMMEDIATE_MESSAGE, "System Error", $"<color=red>{error}</color>", Color.red);
    }
}