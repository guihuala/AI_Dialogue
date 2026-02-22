using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;

public class NetworkService : MonoBehaviour
{
    private string optionsUrl = "http://127.0.0.1:8000/api/get_options";
    private string actionUrl = "http://127.0.0.1:8000/api/perform_action";

    public IEnumerator GetOptionsCoroutine(List<string> activeChars, Action<GetOptionsResponse> onSuccess, Action<string> onFailure)
    {
        GetOptionsRequest req = new GetOptionsRequest { active_roommates = activeChars };
        string json = JsonUtility.ToJson(req);
        
        Debug.Log($"[NetworkService] 发送获取选项请求: {json}");

        using (UnityWebRequest request = new UnityWebRequest(optionsUrl, "POST"))
        {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success) 
            {
                Debug.LogError($"[NetworkService] 请求选项报错: {request.error}");
                onFailure?.Invoke(request.error);
            }
            else 
            {
                string rawText = request.downloadHandler.text;
                Debug.Log($"[NetworkService] 后端返回选项原始JSON: {rawText}");
                
                GetOptionsResponse res = JsonUtility.FromJson<GetOptionsResponse>(rawText);
                if (res == null || res.options == null)
                {
                    Debug.LogError("[NetworkService] 严重错误：JSON解析后数据为空！请检查 DataModels.cs 中的字段名是否与上方JSON严格一致。");
                }
                onSuccess?.Invoke(res);
            }
        }
    }

    public IEnumerator PerformActionCoroutine(string actionContent, List<string> activeChars, Action<PerformActionResponse> onSuccess, Action<string> onFailure)
    {
        PerformActionRequest req = new PerformActionRequest { 
            choice = actionContent, 
            active_roommates = activeChars 
        };
        string json = JsonUtility.ToJson(req);
        
        Debug.Log($"[NetworkService] 发送执行动作请求: {json}");

        using (UnityWebRequest request = new UnityWebRequest(actionUrl, "POST"))
        {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success) 
            {
                Debug.LogError($"[NetworkService] 执行动作报错: {request.error}\n可能的原因: {request.downloadHandler.text}");
                onFailure?.Invoke(request.error);
            }
            else 
            {
                string rawText = request.downloadHandler.text;
                Debug.Log($"[NetworkService] 后端返回动作原始JSON: {rawText}");
                
                PerformActionResponse res = JsonUtility.FromJson<PerformActionResponse>(rawText);
                if (res == null || res.dialogue_sequence == null)
                {
                    Debug.LogError("[NetworkService] 严重错误：JSON解析失败！请检查 DataModels 中的 DialogueTurn 等嵌套类是否打上了 [Serializable] 标签。");
                }
                onSuccess?.Invoke(res);
            }
        }
    }
}