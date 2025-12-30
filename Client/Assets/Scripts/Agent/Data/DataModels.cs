using System;
using System.Collections.Generic;

[Serializable]
public class PlayerStatsData
{
    public float money;
    public int san;
    public float gpa;
}

// 单条对话数据
[Serializable]
public class DialogueTurn
{
    public string speaker; // 说话人名字 (如 "Alice")
    public string content; // 内容 (支持 <shake> 等标签)
    public string mood;    // 心情 (可选)
}

// 玩家请求执行某个动作/选项
[Serializable]
public class PerformActionRequest
{
    public string action_content; // 玩家选的话
    public List<string> active_char_ids; // 在场的人
    public string user_name;
}

// 后端返回的完整演出数据
[Serializable]
public class PerformActionResponse
{
    public List<DialogueTurn> dialogue_sequence; // 对话序列 (Alice说->Bella说->Clara说)
    public PlayerStatsData player_stats;
}

// 获取选项的请求
[Serializable]
public class SuggestOptionsRequest
{
    public string user_name;
    public List<string> active_char_ids;
}

// 获取选项的返回
[Serializable]
public class SuggestOptionsResponse
{
    public List<string> options; // ["打招呼", "借钱", "无视"]
}