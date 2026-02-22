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

// --- 请求/响应数据结构 ---

[Serializable]
public class GetOptionsRequest // 【修改点】重命名，对齐后端
{
    public List<string> active_roommates; // 字段名对齐 active_roommates
}

[Serializable]
public class GetOptionsResponse // 对应原 SuggestOptionsResponse
{
    public List<string> options;
}

[Serializable]
public class PerformActionRequest
{
    public string choice;                 // 字段名对齐 choice
    public List<string> active_roommates; // 字段名对齐 active_roommates
}

[Serializable]
public class PerformActionResponse
{
    public List<DialogueTurn> dialogue_sequence;
    public PlayerStatsData player_stats;
    public GameTimeData game_time;
    public string current_event;
}