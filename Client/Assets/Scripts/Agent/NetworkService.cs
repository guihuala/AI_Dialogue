using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;

public class NetworkService : MonoBehaviour
{
    [Header("Config")]
    [SerializeField] private string serverUrl = "http://127.0.0.1:8000/group_chat";
    [SerializeField] private string observeUrl = "http://127.0.0.1:8000/npc_chat"; // 新接口

    public IEnumerator SendObserveRequest(List<string> activeChars, Action<GroupChatResponse> onSuccess, Action<string> onFailure)
    {
        // 构建请求数据
        NpcChatRequest reqData = new NpcChatRequest
        {
            active_char_ids = activeChars
        };
        string json = JsonUtility.ToJson(reqData);

        using (UnityWebRequest request = new UnityWebRequest(observeUrl, "POST"))
        {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");

            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                onFailure?.Invoke($"Network Error: {request.error}\n{request.downloadHandler.text}");
            }
            else
            {
                try
                {
                    var responseData = JsonUtility.FromJson<GroupChatResponse>(request.downloadHandler.text);
                    onSuccess?.Invoke(responseData);
                }
                catch (Exception e)
                {
                    onFailure?.Invoke($"JSON Parse Error: {e.Message}");
                }
            }
        }
    }

    // 发送消息，使用 Action 回调来处理结果，而不是直接改 UI
    public IEnumerator SendMessageCoroutine(string content, string targetId, string userName, Action<GroupChatResponse> onSuccess, Action<string> onFailure)
    {
        // 1. 构建 JSON
        GroupChatRequest reqData = new GroupChatRequest
        {
            user_input = content,
            target_char_id = targetId,
            user_name = userName
        };
        string json = JsonUtility.ToJson(reqData);

        // 2. 发送请求
        using (UnityWebRequest request = new UnityWebRequest(serverUrl, "POST"))
        {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");

            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                onFailure?.Invoke($"Network Error: {request.error}\n{request.downloadHandler.text}");
            }
            else
            {
                // 3. 解析 JSON 并回调
                try
                {
                    var responseData = JsonUtility.FromJson<GroupChatResponse>(request.downloadHandler.text);
                    onSuccess?.Invoke(responseData);
                }
                catch (Exception e)
                {
                    onFailure?.Invoke($"JSON Parse Error: {e.Message}");
                }
            }
        }
    }
}