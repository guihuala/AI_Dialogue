using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class SaveSelectionPanel : BasePanel
{
    [Header("UI 引用")]
    public SaveSlotItem[] slotItems; 
    public Button backButton;

    // 【新增】缓存槽位状态，用来判断玩家点的是空档还是有数据的档
    private List<SaveSlotInfo> _cachedSlots = new List<SaveSlotInfo>();
    
    public override void OpenPanel(string name)
    {
        base.OpenPanel(name);
        
        backButton.onClick.RemoveAllListeners(); 
        backButton.onClick.AddListener(() => UIManager.Instance.ClosePanel(name));
  
        StartCoroutine(NetworkService.Instance.GetSavesInfoCoroutine(OnGetSavesSuccess, OnGetSavesFailure));
    }

    private void OnGetSavesSuccess(SavesInfoResponse res)
    {
        if (res.slots != null)
        {
            _cachedSlots = res.slots; // 缓存下来

            for (int i = 0; i < slotItems.Length; i++)
            {
                if (i < res.slots.Count)
                {
                    slotItems[i].Setup(res.slots[i], OnSlotClicked);
                }
            }
        }
    }

    private void OnGetSavesFailure(string err)
    {
        Debug.LogError("获取存档列表失败: " + err);
    }

    private void OnSlotClicked(int slotId)
    {
        // 1. 判断点击的槽位是不是空档
        bool isEmpty = true;
        var slotInfo = _cachedSlots.Find(s => s.slot_id == slotId);
        if (slotInfo != null)
        {
            isEmpty = slotInfo.is_empty;
        }

        // 2. 将数据写入跨场景的 GameContext
        GameContext.SelectedSaveSlot = slotId;
        GameContext.IsContinuingGame = !isEmpty; // 如果不是空的，那就是继续游戏

        // 3. 跳转到核心玩法场景
        // 注意：统一使用你在 TitleUIController 里的 SceneLoader 来跳转
        SceneLoader.Instance.LoadScene(GameScene.Gameplay);
    }
}