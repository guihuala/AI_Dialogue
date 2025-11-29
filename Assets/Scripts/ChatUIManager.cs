using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class ChatUIManager : MonoBehaviour
{
    [Header("Containers")]
    [SerializeField] private Transform chatContent;
    [SerializeField] private ScrollRect scrollRect;
    [SerializeField] private Transform optionContainer;
    
    [Header("Status UI")]
    [SerializeField] private Text balanceText; // 余额
    [SerializeField] private Text sanityText;  // 心情
    [SerializeField] private Text gpaText;     // 绩点
    [SerializeField] private Text dateText;    // 日期时间 (新增)
    
    [Header("Prefabs")]
    [SerializeField] private GameObject playerBubblePrefab;
    [SerializeField] private GameObject aiBubblePrefab;
    [SerializeField] private GameObject systemMessagePrefab;
    [SerializeField] private GameObject optionButtonPrefab;

    [Header("Optimization")]
    [SerializeField] private int maxMessages = 50;

    private Text currentStreamingText; 
    private Text currentNameText;
    private GameObject currentStreamingBubbleObj; 
    private List<Tuple<GameObject, GameObject>> activeMessageList = new List<Tuple<GameObject, GameObject>>();

    public Action<StoryOption> OnOptionClicked;

    private void Start()
    {
        if (ObjectPool.Instance == null)
        {
            GameObject poolObj = new GameObject("ObjectPool");
            poolObj.AddComponent<ObjectPool>();
        }
    }

    // --- 核心修改：支持更新所有状态 ---
    public void UpdateStats(float money, float sanity, float gpa, int day, string timePeriod)
    {
        // 1. 金钱
        if (balanceText != null) 
        {
            balanceText.text = $"余额: ￥{money:F0}";
            balanceText.color = money < 200 ? Color.red : Color.black;
        }

        // 2. 心情
        if (sanityText != null) 
        {
            sanityText.text = $"心情: {sanity:F0}";
            sanityText.color = sanity < 30 ? Color.red : Color.black;
        }

        // 3. GPA
        if (gpaText != null) 
        {
            gpaText.text = $"GPA: {gpa:F2}";
            gpaText.color = gpa < 1.8f ? Color.red : Color.black;
        }

        // 4. 日期 (格式：第 1 天  上午)
        if (dateText != null)
        {
            dateText.text = $"第 {day} 天  {timePeriod}";
            // 第7天标红，提醒玩家
            dateText.color = day >= 7 ? Color.red : Color.black;
        }
    }

    // --- 下面是标准的生成逻辑，保持原样 ---

    private GameObject SpawnBubble(GameObject prefab)
    {
        GameObject bubble = ObjectPool.Instance.Spawn(prefab, chatContent);
        activeMessageList.Add(new Tuple<GameObject, GameObject>(bubble, prefab));
        if (activeMessageList.Count > maxMessages)
        {
            var oldItem = activeMessageList[0];
            activeMessageList.RemoveAt(0);
            ObjectPool.Instance.Despawn(oldItem.Item1, oldItem.Item2);
        }
        return bubble;
    }

    public void AddPlayerMessage(string text)
    {
        GameObject bubble = SpawnBubble(playerBubblePrefab);
        bubble.GetComponentInChildren<Text>().text = text;
        ForceScrollToBottom();
    }

    public void AddSystemMessage(string text)
    {
        GameObject bubble = SpawnBubble(systemMessagePrefab);
        bubble.GetComponentInChildren<Text>().text = text;
        ForceScrollToBottom();
    }

    public void CreateAIBubble()
    {
        currentStreamingBubbleObj = SpawnBubble(aiBubblePrefab);
        var texts = currentStreamingBubbleObj.GetComponentsInChildren<Text>();
        if (texts.Length >= 2)
        {
            currentNameText = texts[0]; 
            currentStreamingText = texts[1]; 
        }
        else
        {
            currentStreamingText = texts[0];
            currentNameText = null;
        }
        currentStreamingText.text = "...";
        if (currentNameText != null) currentNameText.text = ""; 
        ForceScrollToBottom();
    }

    public void UpdateCurrentAIBubble(string text)
    {
        if (currentStreamingText != null)
        {
            currentStreamingText.text = text;
            ForceScrollToBottom();
        }
    }

    public void DestroyCurrentStreamingBubble()
    {
        if (currentStreamingBubbleObj != null)
        {
            int index = activeMessageList.FindIndex(x => x.Item1 == currentStreamingBubbleObj);
            if (index != -1) activeMessageList.RemoveAt(index);
            ObjectPool.Instance.Despawn(currentStreamingBubbleObj, aiBubblePrefab);
            currentStreamingBubbleObj = null;
            currentStreamingText = null;
            currentNameText = null;
        }
    }

    public void AddStaticAIBubble(string name, string content)
    {
        GameObject bubbleObj = SpawnBubble(aiBubblePrefab);
        var texts = bubbleObj.GetComponentsInChildren<Text>();
        if (texts.Length >= 2) { texts[0].text = name; texts[1].text = content; }
        else { texts[0].text = content; }
        ForceScrollToBottom();
    }

    public void ShowOptions(List<StoryOption> options)
    {
        ClearOptions();
        if (options == null || options.Count == 0) return;

        foreach (var opt in options)
        {
            GameObject btnObj = ObjectPool.Instance.Spawn(optionButtonPrefab, optionContainer);
            btnObj.GetComponentInChildren<Text>().text = opt.text;
            Button btn = btnObj.GetComponent<Button>();
            btn.onClick.RemoveAllListeners(); 
            btn.onClick.AddListener(() => {
                OnOptionClicked?.Invoke(opt);
                ClearOptions(); 
            });
        }
    }

    public void ClearOptions()
    {
        List<GameObject> children = new List<GameObject>();
        foreach (Transform child in optionContainer) children.Add(child.gameObject);
        foreach (var child in children) ObjectPool.Instance.Despawn(child, optionButtonPrefab);
    }

    private void ForceScrollToBottom()
    {
        Canvas.ForceUpdateCanvases();
        scrollRect.verticalNormalizedPosition = 0f;
        CancelInvoke("ScrollToZero");
        Invoke("ScrollToZero", 0.05f);
    }

    private void ScrollToZero()
    {
        scrollRect.verticalNormalizedPosition = 0f;
    }
}