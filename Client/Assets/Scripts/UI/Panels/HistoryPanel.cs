using UnityEngine;
using UnityEngine.UI;
using TMPro;
using System.Collections.Generic;

public class HistoryPanel : BasePanel
{
    [Header("UI References")]
    [SerializeField] private Transform contentRoot; // ScrollView 的 Content 节点
    [SerializeField] private GameObject historyItemPrefab; // 预制体：包含 SpeakerText 和 ContentText
    [SerializeField] private Button closeButton;

    protected override void Awake()
    {
        base.Awake();
        closeButton.onClick.AddListener(() => ClosePanel());
    }

    public override void OpenPanel(string name)
    {
        base.OpenPanel(name);
        RefreshHistory();
    }

    private void RefreshHistory()
    {
        // 1. 清空旧数据
        foreach (Transform child in contentRoot) Destroy(child.gameObject);

        // 2. 从 GameManager 获取历史数据并生成
        var history = GameManager.Instance.GetChatHistory();
        foreach (var log in history)
        {
            GameObject item = Instantiate(historyItemPrefab, contentRoot);
            
            // 假设 Prefab 里有两个 Text 组件
            // 简单处理：你可以写个脚本挂在 Prefab 上，这里用 Find 演示
            var texts = item.GetComponentsInChildren<TMP_Text>();
            if (texts.Length >= 2)
            {
                texts[0].text = log.speaker; // 名字
                texts[1].text = log.content; // 内容
                
                // 简单的颜色区分
                if (log.speaker == "Player") texts[0].color = Color.cyan;
                else texts[0].color = Color.yellow;
            }
        }
    }
}