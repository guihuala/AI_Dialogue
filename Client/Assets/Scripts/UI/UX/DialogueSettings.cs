using UnityEngine;

public static class DialogueSettings
{
    // === 配置项 ===
    
    // 是否启用打字机效果 (false = 瞬间显示)
    public static bool EnableTypewriter = true;

    // 是否启用文字特效 (震动、波浪等)
    public static bool EnableTextEffects = true;

    // 文字显示速度倍率 (0.5 = 慢, 1.0 = 正常, 2.0 = 快)
    public static float TextSpeedMultiplier = 1.0f;

    // 自动播放等待时间倍率 (0.5 = 等待时间减半/更快, 1.0 = 正常)
    public static float AutoPlaySpeedMultiplier = 1.0f;

    // 是否播放打字音效
    public static bool EnableTypingSound = true;

    // === 默认值重置 ===
    public static void ResetToDefaults()
    {
        EnableTypewriter = true;
        EnableTextEffects = true;
        TextSpeedMultiplier = 1.0f;
        AutoPlaySpeedMultiplier = 1.0f;
        EnableTypingSound = true;
    }
}
