using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class WeChatApp : MonoBehaviour
{
    public static WeChatApp Instance { get; private set; }

    [Header("UI Views")]
    public GameObject chatListView; // Screen showing all active chats
    public GameObject chatRoomView; // Screen showing messages of one specific chat

    [Header("Chat List Elements")]
    public Transform chatListContent; // Where chat row prefabs go
    public GameObject chatRowPrefab;  // Prefab containing Text for chat name & last message

    [Header("Chat Room Elements")]
    public Text chatRoomTitleText;    // Top bar name
    public Transform messageContent;  // Where message bubble prefabs go
    public GameObject messageBubblePrefab; // Prefab for a single message

    // Internal Memory: Key = Chat Group Name
    private Dictionary<string, WeChatSession> chatMemories = new Dictionary<string, WeChatSession>();
    private string activeChatName = "";

    private void Awake()
    {
        if (Instance == null) Instance = this;
        else Destroy(gameObject);
    }

    private void Start()
    {
        // Subscribe to incoming messages
        if (GameManager.Instance != null)
        {
            GameManager.Instance.OnWeChatNotified += HandleIncomingMessages;
        }

        ShowChatList(); // Default view is the list
    }

    private void OnDestroy()
    {
        if (GameManager.Instance != null)
        {
            GameManager.Instance.OnWeChatNotified -= HandleIncomingMessages;
        }
    }

    /// <summary>
    /// Adds incoming AI-generated messages into local memory
    /// </summary>
    private void HandleIncomingMessages(List<WeChatNotification> notifications)
    {
        foreach (var notif in notifications)
        {
            if (!chatMemories.ContainsKey(notif.chat_name))
            {
                chatMemories[notif.chat_name] = new WeChatSession 
                { 
                    chat_name = notif.chat_name, 
                    messages = new List<WeChatMessageData>() 
                };
            }

            chatMemories[notif.chat_name].messages.Add(new WeChatMessageData 
            {
                sender = notif.sender,
                message = notif.message
            });
        }

        // If phone is open, refresh UI to show new messages
        if (gameObject.activeInHierarchy)
        {
            if (chatListView.activeSelf) 
                RefreshChatList();
            else if (chatRoomView.activeSelf && chatMemories.ContainsKey(activeChatName)) 
                RefreshChatRoom();
        }
    }

    /// <summary>
    /// Exports the full chat history into the structure required by Python AI Context
    /// </summary>
    public List<WeChatSession> ExportChatHistory()
    {
        List<WeChatSession> list = new List<WeChatSession>();
        foreach (var kvp in chatMemories)
        {
            list.Add(kvp.Value);
        }
        return list;
    }

    // --- UI Navigation ---

    public void ShowChatList()
    {
        chatListView.SetActive(true);
        chatRoomView.SetActive(false);
        RefreshChatList();
    }

    public void OpenChatRoom(string chatName)
    {
        activeChatName = chatName;
        chatListView.SetActive(false);
        chatRoomView.SetActive(true);
        RefreshChatRoom();
    }

    // --- UI Rendering (Requires Unity Prefab Setup) ---

    // Public method so PhoneManager can update it when opened
    public void RefreshChatList()
    {
        if (chatListContent == null || chatRowPrefab == null) return;

        // Clear existing
        foreach (Transform child in chatListContent) Destroy(child.gameObject);

        foreach (var kvp in chatMemories)
        {
            string sessionName = kvp.Key;
            WeChatSession session = kvp.Value;

            GameObject row = Instantiate(chatRowPrefab, chatListContent);
            
            // Assuming your prefab has 2 Text components: Name and Last Message
            Text[] texts = row.GetComponentsInChildren<Text>();
            if (texts.Length > 0) texts[0].text = sessionName;
            if (texts.Length > 1 && session.messages.Count > 0) 
            {
                var last = session.messages[session.messages.Count - 1];
                texts[1].text = $"{last.sender}: {last.message}";
            }

            // Add click listener to button
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
        if (!chatMemories.ContainsKey(activeChatName)) return;

        if (chatRoomTitleText != null) chatRoomTitleText.text = activeChatName;

        // Clear existing
        foreach (Transform child in messageContent) Destroy(child.gameObject);

        var session = chatMemories[activeChatName];
        foreach (var msg in session.messages)
        {
            GameObject bubble = Instantiate(messageBubblePrefab, messageContent);
            
            // Format: [Sender Name] Message Content
            Text bubbleText = bubble.GetComponentInChildren<Text>();
            if (bubbleText != null)
            {
                bubbleText.text = $"<b>{msg.sender}</b>\n{msg.message}";
            }
        }
    }
}
