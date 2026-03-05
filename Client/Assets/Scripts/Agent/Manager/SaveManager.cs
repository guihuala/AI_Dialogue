using System.Collections;
using UnityEngine;

public class SaveManager
{
    private GameManager hub; // 枢纽引用

    // 自动存档配置
    public bool enableTimerAutoSave = true;
    public float autoSaveInterval = 300f; 
    private Coroutine autoSaveCoroutine;

    public SaveManager(GameManager hub)
    {
        this.hub = hub;
    }

    // ==========================================
    // 💾 存读档逻辑
    // ==========================================
    public void LoadGameFromSlot(int slotId)
    {
        hub.StartCoroutine(NetworkService.Instance.LoadGameCoroutine(slotId, (res) =>
        {
            Debug.Log($"[Load] 读取槽位 {slotId} 成功，正在恢复游戏状态...");
            
            // 1. 覆盖数据层
            hub.Data.OverwriteFromSave(res.data, slotId);
            PlayerPrefs.SetInt("LastPlayedSlot", slotId);

            // 2. 恢复手机系统数据
            if (PhoneManager.Instance != null && res.data.wechat_data_list != null)
                PhoneManager.Instance.ImportChatHistory(res.data.wechat_data_list);

            // 3. 强制刷新所有 UI
            hub.Data.BroadcastAllStats();

            // 4. 重启定时存档，并发送继续指令
            RestartAutoSave();
            hub.SendTurnRequest("【继续游戏】", true);
        }, 
        (err) => 
        {
            hub.ShowSystemError("读取存档失败: " + err);
        }));
    }

    public void SaveGameToSlot(int slotId)
    {
        if (slotId < 1 || slotId > 3) return;
        
        hub.Data.currentSlotId = slotId; // 更新当前绑定的槽位
        SaveGameRequest req = hub.Data.PackSaveData();

        hub.StartCoroutine(NetworkService.Instance.SaveGameCoroutine(req, (res) =>
        {
            Debug.Log($"[Save] 槽位 {slotId} 存档成功!");
            PlayerPrefs.SetInt("LastPlayedSlot", slotId);
            PlayerPrefs.Save();
            MsgCenter.SendMsg(MsgConst.SHOW_IMMEDIATE_MESSAGE, "系统", $"游戏已保存至槽位 {slotId}。", Color.green);
        }, 
        (err) => hub.ShowSystemError("存档失败: " + err)));
    }

    public void AutoSaveGame()
    {
        if (hub.Data.currentSlotId < 1 || hub.Data.currentSlotId > 3) return;

        SaveGameRequest req = hub.Data.PackSaveData();
        hub.StartCoroutine(NetworkService.Instance.SaveGameCoroutine(req, (res) =>
        {
            Debug.Log($"[AutoSave] 已静默保存至槽位 {hub.Data.currentSlotId}。");
        }, 
        (err) => Debug.LogWarning($"[AutoSave] 失败: {err}")));
    }

    // ==========================================
    // ⏱️ 定时器控制
    // ==========================================
    public void RestartAutoSave()
    {
        if (autoSaveCoroutine != null) hub.StopCoroutine(autoSaveCoroutine);
        if (enableTimerAutoSave) autoSaveCoroutine = hub.StartCoroutine(TimerAutoSaveRoutine());
    }

    private IEnumerator TimerAutoSaveRoutine()
    {
        while (enableTimerAutoSave)
        {
            yield return new WaitForSeconds(autoSaveInterval);
            if (hub.CurrentState == GameManager.GameState.Playing) 
            {
                AutoSaveGame();
            }
        }
    }
}