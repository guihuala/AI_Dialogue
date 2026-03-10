using System.Collections.Generic;

/// <summary>
/// 跨场景数据总线，用于存放临时全局数据
/// </summary>
public static class GameContext
{
    // 存储玩家在选人界面选中的室友ID
    public static List<string> SelectedRoommates = new List<string>();

    // 记录玩家点击了哪个存档槽位 (默认给个1)
    public static int SelectedSaveSlot = 1;

    // 标记玩家点的是不是一个“有旧数据”的槽位
    public static bool IsContinuingGame = false;
}