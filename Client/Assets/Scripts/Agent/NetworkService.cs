using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;

public class NetworkService : MonoBehaviour
{
    [SerializeField] private string optionsUrl = "http://127.0.0.1:8000/suggest_options";
    [SerializeField] private string actionUrl = "http://127.0.0.1:8000/perform_action";

    // 获取选项
    public IEnumerator GetOptionsCoroutine(List<string> activeChars, Action<SuggestOptionsResponse> onSuccess, Action<string> onFailure)
    {
        SuggestOptionsRequest req = new SuggestOptionsRequest { active_char_ids = activeChars };
        string json = JsonUtility.ToJson(req);
        
        using (UnityWebRequest request = new UnityWebRequest(optionsUrl, "POST"))
        {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success) onFailure?.Invoke(request.error);
            else onSuccess?.Invoke(JsonUtility.FromJson<SuggestOptionsResponse>(request.downloadHandler.text));
        }
    }

    // 执行动作 (返回一连串对话)
    public IEnumerator PerformActionCoroutine(string actionContent, List<string> activeChars, Action<PerformActionResponse> onSuccess, Action<string> onFailure)
    {
        PerformActionRequest req = new PerformActionRequest { action_content = actionContent, active_char_ids = activeChars };
        string json = JsonUtility.ToJson(req);

        using (UnityWebRequest request = new UnityWebRequest(actionUrl, "POST"))
        {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success) onFailure?.Invoke(request.error + "\n" + request.downloadHandler.text);
            else onSuccess?.Invoke(JsonUtility.FromJson<PerformActionResponse>(request.downloadHandler.text));
        }
    }
}