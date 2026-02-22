using System.Collections.Generic;

/// <summary>
/// 跨场景数据总线，用于存放临时全局数据
/// </summary>
public static class GameContext
{
    // 存储玩家在选人界面选中的室友ID
    public static List<string> SelectedRoommates = new List<string>();
}