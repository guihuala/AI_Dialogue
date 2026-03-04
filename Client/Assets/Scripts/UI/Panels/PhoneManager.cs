using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;

public class PhoneManager : MonoBehaviour
{
    public static PhoneManager Instance { get; private set; }

    [Header("Phone OS Views")]
    public GameObject phoneContainer; // The entire phone UI
    public GameObject homeScreen;    // The app grid
    
    [Header("Apps UI Panels")]
    public GameObject wechatAppPanel;
    public GameObject settingsAppPanel;

    [Header("App Icon Buttons (On Home Screen)")]
    public Button wechatButton;
    public Button settingsButton;

    private void Awake()
    {
        if (Instance == null) Instance = this;
        else Destroy(gameObject);
        
        // Starts hidden
        ClosePhone();
    }

    private void Start()
    {
        // 自动绑定主屏幕上的 App 图标点击事件
        if (wechatButton != null) wechatButton.onClick.AddListener(OpenWeChat);
        if (settingsButton != null) settingsButton.onClick.AddListener(OpenSettings);
    }

    // Toggle the entire phone overlay
    public void TogglePhone()
    {
        if (phoneContainer.activeSelf) ClosePhone();
        else OpenPhone();
    }

    public void OpenPhone()
    {
        phoneContainer.SetActive(true);
        GoToHome(); // Default to home screen
    }

    public void ClosePhone()
    {
        phoneContainer.SetActive(false);
    }

    // Returns to the App Grid
    public void GoToHome()
    {
        homeScreen.SetActive(true);
        if (wechatAppPanel != null) wechatAppPanel.SetActive(false);
        if (settingsAppPanel != null) settingsAppPanel.SetActive(false);
    }

    // Open Specific Apps
    public void OpenWeChat()
    {
        homeScreen.SetActive(false);
        if (settingsAppPanel != null) settingsAppPanel.SetActive(false);
        
        if (wechatAppPanel != null)
        {
            wechatAppPanel.SetActive(true);
            // Optional: call initialize on WeChatApp if needed
            var wechat = wechatAppPanel.GetComponent<WeChatApp>();
            if (wechat != null) wechat.RefreshChatList();
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
