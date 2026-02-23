using System.Collections.Generic;
using UnityEngine;

[System.Serializable]
public struct ExpressionData
{
    public string mood;    // 对应 LLM 返回的 mood，如 "happy", "angry", "sad"
    public Sprite sprite;  // 对应的差分立绘
}

[CreateAssetMenu(fileName = "NewCharacter", menuName = "Game/Character Data")]
public class CharacterData : ScriptableObject
{
    public string id;
    public string displayName;
    [TextArea] public string description;
    
    [Header("Art Assets")]
    public Sprite defaultPortrait; // 默认立绘
    public List<ExpressionData> expressions; // 表情差分列表

    // 辅助方法：根据心情获取对应立绘
    public Sprite GetSpriteByMood(string mood)
    {
        if (string.IsNullOrEmpty(mood)) return defaultPortrait;
        
        foreach (var exp in expressions)
        {
            if (exp.mood.ToLower() == mood.ToLower()) return exp.sprite;
        }
        return defaultPortrait; // 如果没找到对应表情，返回默认立绘防报错
    }
}