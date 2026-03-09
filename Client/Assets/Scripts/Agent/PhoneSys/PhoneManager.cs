using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;

[System.Serializable]
public class TransactionRecord
{
    public float amount;
    public string description;
    public string chapterInfo; // 记录是在哪一章发生的
}

public class PhoneManager : Singleton<PhoneManager>
{
    [Header("Phone OS Views")] public GameObject phoneContainer; // 手机整个外壳
    public GameObject homeScreen; // 桌面网格

    [Header("Apps UI Panels")] 
    public GameObject wechatAppPanel;
    public GameObject settingsAppPanel;
    public GameObject alipayAppPanel;
    public GameObject calendarAppPanel;

    [Header("App Icon Buttons (On Home Screen)")]
    public Button wechatButton;
    public Button settingsButton;
    public Button alipayButton;
    public Button calendarButton;


    // ==========================================
    // 独立数据层
    // ==========================================
    public Dictionary<string, WeChatSession> ChatMemories { get; private set; } = new Dictionary<string, WeChatSession>();
    public List<TransactionRecord> Transactions { get; private set; } = new List<TransactionRecord>();

    protected override void Awake()
    {
        base.Awake();
        ClosePhone();
        
        MsgCenter.RegisterMsg(MsgConst.WECHAT_NOTIFIED, HandleIncomingMessages);
        MsgCenter.RegisterMsg(MsgConst.ADD_TRANSACTION, HandleNewTransaction);
    }

    private void OnDestroy()
    {
        MsgCenter.UnregisterMsg(MsgConst.WECHAT_NOTIFIED, HandleIncomingMessages);
        MsgCenter.UnregisterMsg(MsgConst.ADD_TRANSACTION, HandleNewTransaction);
    }

    private void Start()
    {
        if (wechatButton != null) wechatButton.onClick.AddListener(OpenWeChat);
        if (settingsButton != null) settingsButton.onClick.AddListener(OpenSettings);
        if (alipayButton != null) alipayButton.onClick.AddListener(OpenAlipay);
        if (calendarButton != null) calendarButton.onClick.AddListener(OpenCalendar);
    }

    // ==========================================
    // 数据处理与存档对接
    // ==========================================
// 1. 拦截底层数据，加上 Debug 探针
    private void HandleIncomingMessages(params object[] args)
    {
        List<WeChatNotification> notifications = args[0] as List<WeChatNotification>;
    
        // 探针 A：确认事件中心是否成功派发了数据
        if (notifications == null) 
        {
            Debug.LogError("[PhoneManager] 收到了微信广播，但数据是空的或类型转换失败！");
            return;
        }

        Debug.Log($"[PhoneManager] 成功接收到 {notifications.Count} 条新消息准备写入内存！");

        foreach (var notif in notifications)
        {
            if (!ChatMemories.ContainsKey(notif.chat_name))
            {
                ChatMemories[notif.chat_name] = new WeChatSession 
                { 
                    chat_name = notif.chat_name, 
                    messages = new List<WeChatMessageData>() 
                };
            }
        
            ChatMemories[notif.chat_name].messages.Add(new WeChatMessageData 
            {
                sender = notif.sender,
                message = notif.message
            });
        }

        // 依然保留：如果玩家正在看手机，实时刷新
        if (wechatAppPanel != null && wechatAppPanel.activeInHierarchy)
        {
            wechatAppPanel.GetComponent<WeChatApp>()?.RefreshCurrentView();
        }
    }
    
    private void HandleNewTransaction(params object[] args)
    {
        float amount = (float)args[0];
        string desc = (string)args[1];
        string chapter = (string)args[2];

        Transactions.Add(new TransactionRecord { 
            amount = amount, 
            description = desc,
            chapterInfo = chapter
        });
    }

    public List<WeChatSession> ExportChatHistory()
    {
        return new List<WeChatSession>(ChatMemories.Values);
    }

    public void ImportChatHistory(List<WeChatSession> importedHistory)
    {
        ChatMemories.Clear();
        if (importedHistory != null)
        {
            foreach (var session in importedHistory)
            {
                ChatMemories[session.chat_name] = session;
            }
        }

        if (wechatAppPanel != null && wechatAppPanel.activeInHierarchy)
        {
            wechatAppPanel.GetComponent<WeChatApp>()?.RefreshCurrentView();
        }
    }

    // ==========================================
    // 系统 UI 导航逻辑
    // ==========================================
    public void TogglePhone()
    {
        if (phoneContainer.activeSelf) ClosePhone();
        else OpenPhone();
    }

    public void OpenPhone()
    {
        phoneContainer.SetActive(true);
        GoToHome();
    }

    public void ClosePhone()
    {
        phoneContainer.SetActive(false);
    }

    public void GoToHome()
    {
        homeScreen.SetActive(true);
        if (wechatAppPanel != null) wechatAppPanel.SetActive(false);
        if (settingsAppPanel != null) settingsAppPanel.SetActive(false);
        if (alipayAppPanel != null) alipayAppPanel.SetActive(false);
        if (calendarAppPanel != null) calendarAppPanel.SetActive(false);
    }

    public void OpenAlipay()
    {
        GoToHome(); // 先全部关闭
        homeScreen.SetActive(false);
        if (alipayAppPanel != null) alipayAppPanel.SetActive(true);
    }

    public void OpenCalendar()
    {
        GoToHome();
        homeScreen.SetActive(false);
        if (calendarAppPanel != null) calendarAppPanel.SetActive(true);
    }

    
    public void OpenWeChat()
    {
        homeScreen.SetActive(false);
        if (settingsAppPanel != null) settingsAppPanel.SetActive(false);
    
        if (wechatAppPanel != null)
        {
            wechatAppPanel.SetActive(true);
            
            var appScript = wechatAppPanel.GetComponent<WeChatApp>();
            if (appScript != null)
            {
                appScript.ShowChatList(); 
            }
            else
            {
                Debug.LogError("[PhoneManager] wechatAppPanel 上没有挂载 WeChatApp.cs 脚本！");
            }
        }
    }

    public void OpenSettings()
    {
        homeScreen.SetActive(false);
        if (wechatAppPanel != null) wechatAppPanel.SetActive(false);
        
        if (settingsAppPanel != null)
        {
            settingsAppPanel.SetActive(true);
        }
    }
}