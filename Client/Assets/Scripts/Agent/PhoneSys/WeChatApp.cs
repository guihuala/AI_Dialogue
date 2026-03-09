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
    public GameObject messageBubblePrefab; 
    
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

    // --- UI Rendering (从 PhoneManager 读取数据) ---

    // 开放给 PhoneManager 调用的统一刷新入口
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

        // 自己不存数据，直接从 PhoneManager 的大脑里拿数据渲染
        var memories = PhoneManager.Instance.ChatMemories;

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

            Button btn = row.GetComponent<Button>();
            if (btn != null)
            {
                btn.onClick.AddListener(() => OpenChatRoom(sessionName));
            }
        }
    }

    private void RefreshChatRoom()
    {
        if (messageContent == null || messageBubblePrefab == null) return;
        
        var memories = PhoneManager.Instance.ChatMemories;
        if (!memories.ContainsKey(activeChatName)) return;

        if (chatRoomTitleText != null) chatRoomTitleText.text = activeChatName;

        foreach (Transform child in messageContent) Destroy(child.gameObject);

        var session = memories[activeChatName];
        foreach (var msg in session.messages)
        {
            GameObject bubble = Instantiate(messageBubblePrefab, messageContent);
            
            Text bubbleText = bubble.GetComponentInChildren<Text>();
            if (bubbleText != null)
            {
                // 同样只负责渲染
                bubbleText.text = $"<b>{msg.sender}</b>\n{msg.message}";
            }
        }
    }
}