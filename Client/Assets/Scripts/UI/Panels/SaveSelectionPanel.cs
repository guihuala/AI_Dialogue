using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class SaveSelectionPanel : BasePanel
{
    [Header("UI 引用")]
    public SaveSlotItem[] slotItems; // 拖入 3 个 Slot 预制体实例
    public Button backButton;
    public GameObject loadingOverlay; // 加载中的遮罩

    public override void OpenPanel(string name)
    {
        base.OpenPanel(name);
        
        backButton.onClick.AddListener(() => UIManager.Instance.ClosePanel(name));
        
        // 初始显示加载中
        loadingOverlay.SetActive(true);
        
        // 请求后端存档信息
        StartCoroutine(NetworkService.Instance.GetSavesInfoCoroutine(OnGetSavesSuccess, OnGetSavesFailure));
    }

    private void OnGetSavesSuccess(SavesInfoResponse res)
    {
        loadingOverlay.SetActive(false);
        
        if (res.slots != null)
        {
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
        loadingOverlay.SetActive(false);
        Debug.LogError("获取存档列表失败: " + err);
    }

    private void OnSlotClicked(int slotId)
    {
        // 1. 设置标记，告诉下个场景的 GameManager 要读哪个档
        PlayerPrefs.SetInt("IsContinuingGame", 1);
        PlayerPrefs.SetInt("SelectedSlotID", slotId);
        PlayerPrefs.Save();

        // 2. 跳转场景
        SceneLoader.Instance.LoadScene(GameScene.Gameplay);
    }
}