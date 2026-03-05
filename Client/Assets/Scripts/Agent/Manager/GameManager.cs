using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class GameManager : Singleton<GameManager>
{
    public enum GameState { Playing, Paused, GameOver }
    public GameState CurrentState { get; private set; }

    // ==========================================
    // 🧩 子系统挂载 (Sub-Managers)
    // ==========================================
    public DataManager Data { get; private set; }
    public SaveManager Save { get; private set; }

    // ==========================================
    // 对外暴露的只读数据透传
    // ==========================================
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

        // 路由系统
        if (PlayerPrefs.GetInt("IsContinuingGame", 0) == 1)
        {
            int slotId = PlayerPrefs.GetInt("SelectedSlotID", 1);
            PlayerPrefs.SetInt("IsContinuingGame", 0);
            PlayerPrefs.Save();
            
            // 指挥存档系统干活
            Save.LoadGameFromSlot(slotId);
        }
        else
        {
            StartNewGame();
        }
    }

    public void StartNewGame()
    {
        // 指挥数据系统重置
        Data.ResetForNewGame();
        
        if (PhoneManager.Instance != null)
            PhoneManager.Instance.ImportChatHistory(new List<WeChatSession>());

        Data.BroadcastAllStats();
        Save.RestartAutoSave();
        SendTurnRequest("【开始大学生活】", true);
    }

    // ==========================================
    // 🔄 网络核心回合流转
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

        // 2. 指挥数据系统更新并广播
        Data.currentSan = res.san;
        Data.currentMoney = res.money;
        Data.currentGpa = res.gpa;
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