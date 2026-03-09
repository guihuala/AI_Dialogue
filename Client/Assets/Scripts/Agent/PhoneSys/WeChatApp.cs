using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class WeChatApp : MonoBehaviour
{
    [Header("UI Views")]
    public GameObject chatListView; 
    public GameObject chatRoomView; 

    [Header("Chat List Elements")]
    public Transform chatListContent; 
    public GameObject chatRowPrefab;  

    [Header("Chat Room Elements")]
    public Text chatRoomTitleText;    
    public Transform messageContent;  
    
    // 用于自动滚动的 ScrollRect 组件
    [Header("Auto Scroll")]
    public ScrollRect chatRoomScrollRect; 

    // 左右气泡拆分
    [Header("Chat Bubbles")]
    public GameObject leftBubblePrefab;  // 别人的消息（通常放左边，白气泡）
    public GameObject rightBubblePrefab; // 自己的消息（通常放右边，绿气泡）
    
    private string activeChatName = "";
    
    // --- UI Navigation ---
    public void ShowChatList()
    {
        if (chatListView) chatListView.SetActive(true);
        if (chatRoomView) chatRoomView.SetActive(false);
        RefreshChatList();
    }

    public void OpenChatRoom(string chatName)
    {
        activeChatName = chatName;
        if (chatListView) chatListView.SetActive(false);
        if (chatRoomView) chatRoomView.SetActive(true);
        RefreshChatRoom();
    }

    // --- UI Rendering ---
    public void RefreshCurrentView()
    {
        if (chatListView != null && chatListView.activeSelf) 
            RefreshChatList();
        else if (chatRoomView != null && chatRoomView.activeSelf) 
            RefreshChatRoom();
    }

    private void RefreshChatList()
    {
        if (chatListContent == null || chatRowPrefab == null) return;

        foreach (Transform child in chatListContent) Destroy(child.gameObject);

        var memories = PhoneManager.Instance.ChatMemories;
        
        // 检查数据是否成功传入手机大脑
        Debug.Log($"[WeChatApp Debug] 当前内存中有 {memories.Count} 个聊天会话。"); 

        foreach (var kvp in memories)
        {
            string sessionName = kvp.Key;
            WeChatSession session = kvp.Value;

            GameObject row = Instantiate(chatRowPrefab, chatListContent);
            
            Text[] texts = row.GetComponentsInChildren<Text>();
            if (texts.Length > 0) texts[0].text = sessionName;
            if (texts.Length > 1 && session.messages.Count > 0) 
            {
                var last = session.messages[session.messages.Count - 1];
                texts[1].text = $"{last.sender}: {last.message}";
            }
            else if (texts.Length == 0)
            {
                Debug.LogWarning("[WeChatApp Debug] ChatRowPrefab 上找不到 Text 组件！如果你用了 TextMeshPro，请看下方的排查指南。");
            }

            Button btn = row.GetComponent<Button>();
            if (btn != null)
            {
                btn.onClick.AddListener(() => OpenChatRoom(sessionName));
            }
        }
    }

    private void RefreshChatRoom()
    {
        // 确保两个气泡 Prefab 都已赋值
        if (messageContent == null || leftBubblePrefab == null || rightBubblePrefab == null) return;
        
        var memories = PhoneManager.Instance.ChatMemories;
        if (!memories.ContainsKey(activeChatName)) return;

        if (chatRoomTitleText != null) chatRoomTitleText.text = activeChatName;

        foreach (Transform child in messageContent) Destroy(child.gameObject);

        var session = memories[activeChatName];
        
        // 🐛 排错点 3：检查当前聊天室的数据量
        Debug.Log($"[WeChatApp Debug] 正在渲染聊天室 [{activeChatName}]，包含 {session.messages.Count} 条消息。");

        foreach (var msg in session.messages)
        {
            // 【左右气泡区分逻辑】判断发送者是否是玩家（设定为陆陈安然）
            bool isMe = (msg.sender == "陆陈安然" || msg.sender == "Player");
            GameObject prefabToUse = isMe ? rightBubblePrefab : leftBubblePrefab;

            GameObject bubble = Instantiate(prefabToUse, messageContent);
            
            Text bubbleText = bubble.GetComponentInChildren<Text>();
            if (bubbleText != null)
            {
                bubbleText.text = $"<b>{msg.sender}</b>\n{msg.message}";
            }
            else
            {
                Debug.LogWarning("[WeChatApp Debug] 气泡 Prefab 上找不到 Text 组件！");
            }
        }

        // 自动滚动逻辑
        // 必须确保在 UI 激活状态下调用协程
        if (gameObject.activeInHierarchy)
        {
            StartCoroutine(ScrollToBottom());
        }
    }

    // 等待 UI 排版完成后，再将滚动条拉到底部
    private IEnumerator ScrollToBottom()
    {
        // 等待一帧，让 ContentSizeFitter 和 VerticalLayoutGroup 计算完最新的高度
        yield return new WaitForEndOfFrame();
        
        if (chatRoomScrollRect != null)
        {
            chatRoomScrollRect.verticalNormalizedPosition = 0f;
        }
    }
}