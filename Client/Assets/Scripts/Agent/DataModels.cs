using System;

// 对应 Python 的 PlayerStats
[Serializable]
public class PlayerStatsData
{
    public float money;
    public int san;
    public float gpa;
}

// 对应 Python 接收的 Request
[Serializable]
public class GroupChatRequest
{
    public string user_input;
    public string target_char_id;
    public string user_name;
}

// 对应 Python 返回的 Response
[Serializable]
public class GroupChatResponse
{
    public string response;
    public string speaker;
    public string mood;
    public PlayerStatsData player_stats; // 嵌套的 JSON 对象
}