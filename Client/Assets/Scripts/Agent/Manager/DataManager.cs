using System.Collections.Generic;

public class DataManager
{
    // ==========================================
    // 📊 核心游戏数据
    // ==========================================
    public int currentSlotId = -1;
    public List<string> activeRoommates = new List<string>();
    
    public int currentSan = 100;
    public float currentMoney = 2000f;
    public float currentGpa = 4.0f;
    public int argCount = 0;
    
    public int currentChapter = 1;
    public int currentTurn = 0;
    public string currentEvtId = "";
    public bool isAwaitingTransition = false;
    
    public string currentScene = "宿舍";

    // ==========================================
    // 🔄 数据重置与覆盖
    // ==========================================
    public void ResetForNewGame()
    {
        currentSlotId = -1;
        currentSan = 100;
        currentMoney = 2000f;
        currentGpa = 4.0f;
        argCount = 0;
        currentChapter = 1;
        currentTurn = 0;
        currentEvtId = "";
        activeRoommates.Clear();
        isAwaitingTransition = false;
    }

    public void OverwriteFromSave(SaveGameRequest data, int slotId)
    {
        currentSlotId = slotId;
        activeRoommates = data.active_roommates;
        currentEvtId = data.current_evt_id;
        currentChapter = data.chapter;
        currentTurn = data.turn;
        currentSan = data.san;
        currentMoney = data.money;
        currentGpa = data.gpa;
        argCount = data.arg_count;
    }

    public SaveGameRequest PackSaveData()
    {
        return new SaveGameRequest
        {
            slot_id = currentSlotId,
            active_roommates = activeRoommates,
            current_evt_id = currentEvtId,
            chapter = currentChapter,
            turn = currentTurn,
            san = currentSan,
            money = currentMoney,
            gpa = currentGpa,
            arg_count = argCount,
            wechat_data_list = PhoneManager.Instance != null ? PhoneManager.Instance.ExportChatHistory() : new List<WeChatSession>()
        };
    }

    // ==========================================
    // 📢 统一 UI 刷新
    // ==========================================
    public void BroadcastAllStats()
    {
        MsgCenter.SendMsg(MsgConst.INIT_ROOMMATES, activeRoommates);
        
        PlayerStatsData stats = new PlayerStatsData { san = currentSan, money = currentMoney, gpa = currentGpa };
        GameTimeData timeData = new GameTimeData { year = $"第 {currentChapter} 章", month = currentChapter, week = currentTurn };
        MsgCenter.SendMsg(MsgConst.STATS_REFRESHED, stats, timeData, currentEvtId);
    }
}