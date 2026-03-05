using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;

public class PhoneManager : Singleton<PhoneManager>
{
    [Header("Phone OS Views")]
    public GameObject phoneContainer; // 手机整个外壳
    public GameObject homeScreen;    // 桌面网格
    
    [Header("Apps UI Panels")]
    public GameObject wechatAppPanel;
    public GameObject settingsAppPanel;

    [Header("App Icon Buttons (On Home Screen)")]
    public Button wechatButton;
    public Button settingsButton;

    // ==========================================
    // 💾 独立数据层 (Data Models)
    // ==========================================
    // 🌟 手机系统的底层数据库，App 们只管从这里读取
    public Dictionary<string, WeChatSession> ChatMemories { get; private set; } = new Dictionary<string, WeChatSession>();

    protected override void Awake()
    {
        base.Awake();
        ClosePhone();
        
        // 🌟 将原本挂在 WeChatApp 里的事件拦截移到系统层
        MsgCenter.RegisterMsg(MsgConst.WECHAT_NOTIFIED, HandleIncomingMessages);
    }

    private void OnDestroy()
    {
        MsgCenter.UnregisterMsg(MsgConst.WECHAT_NOTIFIED, HandleIncomingMessages);
    }

    private void Start()
    {
        if (wechatButton != null) wechatButton.onClick.AddListener(OpenWeChat);
        if (settingsButton != null) settingsButton.onClick.AddListener(OpenSettings);
    }

    // ==========================================
    // 💬 数据处理与存档对接
    // ==========================================
    private void HandleIncomingMessages(params object[] args)
    {
        List<WeChatNotification> notifications = args[0] as List<WeChatNotification>;
        if (notifications == null) return;

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

            // 仅仅修改底层数据
            ChatMemories[notif.chat_name].messages.Add(new WeChatMessageData 
            {
                sender = notif.sender,
                message = notif.message
            });
        }

        // 如果玩家正在看微信，通知 UI 重新渲染最新数据
        if (wechatAppPanel != null && wechatAppPanel.activeInHierarchy)
        {
            wechatAppPanel.GetComponent<WeChatApp>()?.RefreshCurrentView();
        }
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
    // 📱 系统 UI 导航逻辑
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
    }

    public void OpenWeChat()
    {
        homeScreen.SetActive(false);
        if (settingsAppPanel != null) settingsAppPanel.SetActive(false);
        
        if (wechatAppPanel != null)
        {
            wechatAppPanel.SetActive(true);
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