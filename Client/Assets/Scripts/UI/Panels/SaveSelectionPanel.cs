using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class SaveSelectionPanel : BasePanel
{
    [Header("UI 引用")]
    public SaveSlotItem[] slotItems; // 拖入 3 个 Slot 预制体实例
    public Button backButton;
    
    public override void OpenPanel(string name)
    {
        base.OpenPanel(name);
        
        backButton.onClick.RemoveAllListeners(); // 养成好习惯，防止重复注册
        backButton.onClick.AddListener(() => UIManager.Instance.ClosePanel(name));
  
        StartCoroutine(NetworkService.Instance.GetSavesInfoCoroutine(OnGetSavesSuccess, OnGetSavesFailure));
    }

    private void OnGetSavesSuccess(SavesInfoResponse res)
    {
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
        Debug.LogError("获取存档列表失败: " + err);
    }

    private void OnSlotClicked(int slotId)
    {
        // 1. 设置标记，告诉下个场景的 GameManager 要读哪个档
        PlayerPrefs.SetInt("IsContinuingGame", 1);
        PlayerPrefs.SetInt("SelectedSlotID", slotId);
        PlayerPrefs.Save();

        // 2. 跳转场景 (假定你的场景加载管理器是这么写的)
        // 如果你的场景管理叫别的名字，请替换为你自己的跳转代码，比如 SceneManager.LoadScene("MainGameScene");
        UnityEngine.SceneManagement.SceneManager.LoadScene("MainGameScene");
    }
}