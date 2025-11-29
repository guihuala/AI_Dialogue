using System;
using System.Collections.Generic;

[Serializable]
public class ChatMessage
{
    public string role;
    public string content;
}

public class OpenAIStreamResponse
{
    public List<StreamChoice> choices;
}
public class StreamChoice
{
    public StreamDelta delta;
}
public class StreamDelta
{
    public string content;
}

// 确保字段名为 money_change, sanity_change, gpa_change
public class GameEventCommand
{
    public float money_change;
    public float sanity_change;
    public float gpa_change;
    public string note;
}

[Serializable]
public class StoryOption
{
    public string id;      
    public string text;    
    public string content; 
}

public class OptionPackage
{
    public List<StoryOption> options;
}