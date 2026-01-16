using System;
using System.Collections.Generic;

[Serializable]
public class PlayerStatsData
{
    public float money;
    public int san;
    public float gpa;
}

// --- 时间数据 ---
[Serializable]
public class GameTimeData
{
    public int year;
    public int month;
    public int week;
}

[Serializable]
public class DialogueTurn
{
    public string speaker;
    public string content;
    public string mood;
}

[Serializable]
public class PerformActionRequest
{
    public string action_content;
    public List<string> active_char_ids;
    public string user_name;
}

[Serializable]
public class PerformActionResponse
{
    public List<DialogueTurn> dialogue_sequence;
    public PlayerStatsData player_stats;
    public GameTimeData game_time;
    public string current_event;
}

[Serializable]
public class SuggestOptionsRequest
{
    public string user_name;
    public List<string> active_char_ids;
}

[Serializable]
public class SuggestOptionsResponse
{
    public List<string> options;
}