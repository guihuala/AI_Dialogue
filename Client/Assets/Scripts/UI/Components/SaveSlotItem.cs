using UnityEngine;
using UnityEngine.UI;

public class SaveSlotItem : MonoBehaviour
{
    public int slotId;
    public Text slotTitleText;      // 槽位标题（如：槽位 1）
    public Text chapterInfoText;    // 章节信息（如：第2章 - 第3回合）
    public Text timestampText;      // 时间戳（如：2023-10-27 15:30）
    public Button selectButton;
    public GameObject emptyTag;     // “空存档”提示

    private System.Action<int> onSlotSelected;

    public void Setup(SaveSlotInfo info, System.Action<int> onSelect)
    {
        slotId = info.slot_id;
        onSlotSelected = onSelect;
        
        slotTitleText.text = $"存档槽位 {slotId}";
        
        if (info.is_empty)
        {
            chapterInfoText.text = "---";
            timestampText.text = "暂无数据";
            emptyTag.SetActive(true);
        }
        else
        {
            chapterInfoText.text = info.chapter_info;
            timestampText.text = info.timestamp;
            emptyTag.SetActive(false);
        }

        selectButton.onClick.RemoveAllListeners();
        selectButton.onClick.AddListener(() => onSlotSelected?.Invoke(slotId));
    }
}