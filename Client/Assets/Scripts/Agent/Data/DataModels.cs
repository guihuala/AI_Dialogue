using System;
using System.Collections.Generic;

[Serializable]
public class PlayerStatsData
{
    public float money;
    public int san;
    public float gpa;
}

[Serializable]
public class GameTimeData
{
    public string year; // 【修改点】改为 string，适配后端返回的 "一"
    public int month;
    public int week;
}

[Serializable]
public class DialogueTurn
{
    public string speaker;
    public string content;
    public string mood; // Mock接口暂时没返回，但保留没关系，会是null
}


// --- 新增请求/响应数据结构 ---

[Serializable]
public class StartGameRequest
{
    public List<string> roommates; // optional, can be empty
}

// 模拟 Python 中的 Dict[str, float]
[Serializable]
public class StringFloatDictionary
{
    public List<string> keys;
    public List<float> values;
}

[Serializable]
public class WeChatNotification
{
    public string chat_name;
    public string sender;
    public string message;
}

[Serializable]
public class GameTurnRequest 
{
    public string choice;                 
    public List<string> active_roommates; 
    public string current_evt_id;
    public bool is_transition;
    public int chapter;
    public int turn;
    public int san;
    public float money;
    public float gpa;
    public int arg_count;
    // 适配 Unity JsonUtility 无法序列化字典的问题，改为传递 List
    public List<WeChatSession> wechat_data_list; 
}

[Serializable]
public class WeChatSession
{
    public string chat_name;
    public List<WeChatMessageData> messages;
}

[Serializable]
public class WeChatMessageData
{
    public string sender;
    public string message;
}

[Serializable]
public class GameTurnResponse
{
    public bool is_game_over;
    public string msg; // game over message
    public string display_text; // The whole text to display (or dialogue lines)

    public int san;
    public float money;
    public float gpa;
    public int arg_count;
    public int chapter;
    public int turn;
    public string current_evt_id;

    public bool is_end;
    public List<string> next_options;

    public List<WeChatNotification> wechat_notifications;
    public List<DialogueTurn> dialogue_sequence; // ADDED THIS BACK
    public string narrator_transition; // ADDED THIS BACK
    public string error; // Backend Exception message
}

[Serializable]
public class SaveGameState // 对应后端的 game_state 字典
{
    public PlayerStatsData player_stats;
    public GameTimeData game_time;

    public string current_event;
    // 未来可扩充
}

[Serializable]
public class ResetGameResponse
{
    public string status;
    public string message;
}

[Serializable]
public class SettingsRequest
{
    public float temperature;

    public int max_tokens;
    // 可以添加 custom_model
}

[Serializable]
public class SettingsCurrentState
{
    public float temperature;
    public int max_tokens;
}

[Serializable]
public class SettingsResponse
{
    public string status;
    public SettingsCurrentState current_settings;
}

// ==========================================
// 💾 存档系统相关数据结构
// ==========================================

[Serializable]
public class SaveSlotInfo
{
    public int slot_id;
    public bool is_empty;
    public string timestamp;
    public string chapter_info;
}

[Serializable]
public class SavesInfoResponse
{
    public string status;
    public List<SaveSlotInfo> slots;
}

// 请求保存游戏时，把所有必要的恢复状态打平传给后端
[Serializable]
public class SaveGameRequest
{
    public int slot_id;
    public List<string> active_roommates;
    public string current_evt_id;
    public int chapter;
    public int turn;
    public int san;
    public float money;
    public float gpa;
    public int arg_count;
    // 如果你有完整的微信系统模型 WeChatSession，加上这个
    public List<WeChatSession> wechat_data_list; 
}

[Serializable]
public class SaveGameResponse
{
    public string status;
    public int slot_id;
    public string message;
}

[Serializable]
public class LoadGameResponse
{
    public string status;
    // 后端读取时返回的 data 其实就是我们保存进去的 SaveGameRequest 的字段组合
    public SaveGameRequest data; 
}