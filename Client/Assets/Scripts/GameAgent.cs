using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
using TMPro;
using UnityEngine.UI;

public class GameAgent : MonoBehaviour
{
    [Header("Server Config")]
    [SerializeField] private string serverUrl = "http://127.0.0.1:8000/chat"; 
    [SerializeField] private string userName = "Adventurer";

    [Header("UI References")]
    [SerializeField] private TMP_InputField inputField;
    [SerializeField] private Button sendButton;
    [SerializeField] private TMP_Text outputText;
    
    // 显示角色状态 UI (可选)
    [SerializeField] private TMP_Text statusText; 

    private void Start()
    {
        sendButton.onClick.AddListener(OnSendClick);
    }

    private void OnSendClick()
    {
        if (string.IsNullOrEmpty(inputField.text)) return;
        StartCoroutine(PostToBackend(inputField.text));
        inputField.text = ""; 
        outputText.text = "Thinking...";
    }

    IEnumerator PostToBackend(string text)
    {
        // 1. 构建请求数据 (对应 Python 的 ChatRequest)
        ChatRequestData data = new ChatRequestData
        {
            user_input = text,
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
                outputText.text = "Error: " + request.error;
            }
            else
            {
                // 2. 解析 Python 返回的数据
                string responseJson = request.downloadHandler.text;
                ServerResponse res = JsonUtility.FromJson<ServerResponse>(responseJson);

                outputText.text = res.response;
                
                // 更新状态面板 (如果有)
                if(statusText != null)
                {
                    statusText.text = $"Mood: {res.current_mood} | HP: {res.hp}";
                }
            }
        }
    }

    [System.Serializable]
    public class ChatRequestData
    {
        public string user_input;
        public string user_name;
    }

    [System.Serializable]
    public class ServerResponse
    {
        public string response;
        public string current_mood;
        public int hp;
    }
}