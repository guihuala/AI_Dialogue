using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
using TMPro;
using UnityEngine.UI;

public class GameAgent : MonoBehaviour
{
    [Header("Settings")]
    [SerializeField] private string serverUrl = "http://127.0.0.1:8000/group_chat"; // 注意 URL 变了
    [SerializeField] private string userName = "Adventurer";

    [Header("Target Selection")]
    // 简单的下拉框模拟选择对象 (zhuge / vic)
    [SerializeField] private TMP_Dropdown targetDropdown; 

    [Header("UI")]
    [SerializeField] private TMP_InputField inputField;
    [SerializeField] private Button sendButton;
    [SerializeField] private TMP_Text outputText;

    private void Start()
    {
        sendButton.onClick.AddListener(OnSendClick);
        
        targetDropdown.ClearOptions(); // 先清空默认的 Option A/B/C
        var options = new System.Collections.Generic.List<string> { "zhuge", "vic" };
        targetDropdown.AddOptions(options);
    }

    private void OnSendClick()
    {
        if (string.IsNullOrEmpty(inputField.text)) return;
        
        // 获取当前选中的角色 ID
        string selectedId = targetDropdown.options[targetDropdown.value].text;
        
        StartCoroutine(PostGroupChat(inputField.text, selectedId));
        inputField.text = "";
        outputText.text = $"Speaking to {selectedId}...";
    }

    IEnumerator PostGroupChat(string text, string targetId)
    {
        GroupChatRequest data = new GroupChatRequest
        {
            user_input = text,
            target_char_id = targetId,
            user_name = userName
        };

        string json = JsonUtility.ToJson(data);

        using (UnityWebRequest request = new UnityWebRequest(serverUrl, "POST"))
        {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");

            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                outputText.text = "Error: " + request.error + "\n" + request.downloadHandler.text;
            }
            else
            {
                var res = JsonUtility.FromJson<GroupChatResponse>(request.downloadHandler.text);
                // 显示格式： [诸葛亮]: ......
                outputText.text = $"<color=yellow>[{res.speaker}]</color>: {res.response}";
            }
        }
    }

    [System.Serializable]
    public class GroupChatRequest
    {
        public string user_input;
        public string target_char_id;
        public string user_name;
    }

    [System.Serializable]
    public class GroupChatResponse
    {
        public string response;
        public string speaker;
        public string context_sync;
    }
}