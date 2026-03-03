using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;

public class NetworkService : MonoBehaviour
{
    private string baseUrl = "http://127.0.0.1:8000/api";

    // ============================================
    // 基础核心流程
    // ============================================

    public IEnumerator StartGameCoroutine(List<string> roommates, Action<GameTurnResponse> onSuccess, Action<string> onFailure)
    {
        StartGameRequest req = new StartGameRequest { roommates = roommates };
        string json = JsonUtility.ToJson(req);
        
        Debug.Log($"[NetworkService] 发送初始游戏请求: {json}");

        using (UnityWebRequest request = new UnityWebRequest($"{baseUrl}/game/start", "POST"))
        {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success) 
            {
                Debug.LogError($"[NetworkService] 初始游戏报错: {request.error}");
                onFailure?.Invoke(request.error);
            }
            else 
            {
                string rawText = request.downloadHandler.text;
                Debug.Log($"[NetworkService] 后端返回初始状态 JSON: {rawText}");
                
                GameTurnResponse res = JsonUtility.FromJson<GameTurnResponse>(rawText);
                onSuccess?.Invoke(res);
            }
        }
    }

    public IEnumerator PlayTurnCoroutine(GameTurnRequest req, Action<GameTurnResponse> onSuccess, Action<string> onFailure)
    {
        string json = JsonUtility.ToJson(req);
        
        Debug.Log($"[NetworkService] 发送回合推演请求: {json}");

        using (UnityWebRequest request = new UnityWebRequest($"{baseUrl}/game/turn", "POST"))
        {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success) 
            {
                Debug.LogError($"[NetworkService] 回合推演报错: {request.error}\n详情: {request.downloadHandler.text}");
                onFailure?.Invoke(request.error);
            }
            else 
            {
                string rawText = request.downloadHandler.text;
                Debug.Log($"[NetworkService] 后端返回回合结算JSON: {rawText}");
                
                GameTurnResponse res = JsonUtility.FromJson<GameTurnResponse>(rawText);
                if (res == null)
                {
                    Debug.LogError("[NetworkService] 严重错误：回合数据解析为空！");
                }
                onSuccess?.Invoke(res);
            }
        }
    }

    // ============================================
    // 存档、读档与系统接口
    // ============================================
    
    public IEnumerator SaveGameCoroutine(string slotId, SaveGameState gameState, Action<SaveGameResponse> onSuccess, Action<string> onFailure)
    {
        SaveGameRequest req = new SaveGameRequest { slot_id = slotId, game_state = gameState };
        string json = JsonUtility.ToJson(req);
        
        using (UnityWebRequest request = new UnityWebRequest($"{baseUrl}/game/save", "POST"))
        {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success) onFailure?.Invoke(request.error);
            else onSuccess?.Invoke(JsonUtility.FromJson<SaveGameResponse>(request.downloadHandler.text));
        }
    }

    public IEnumerator LoadGameCoroutine(string slotId, Action<LoadGameResponse> onSuccess, Action<string> onFailure)
    {
        using (UnityWebRequest request = new UnityWebRequest($"{baseUrl}/game/load/{slotId}", "GET"))
        {
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success) onFailure?.Invoke(request.error);
            else onSuccess?.Invoke(JsonUtility.FromJson<LoadGameResponse>(request.downloadHandler.text));
        }
    }

    public IEnumerator ResetGameCoroutine(Action<ResetGameResponse> onSuccess, Action<string> onFailure)
    {
        using (UnityWebRequest request = new UnityWebRequest($"{baseUrl}/game/reset", "POST"))
        {
            // Empty body for reset POST
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes("{}");
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success) onFailure?.Invoke(request.error);
            else onSuccess?.Invoke(JsonUtility.FromJson<ResetGameResponse>(request.downloadHandler.text));
        }
    }

    public IEnumerator UpdateSettingsCoroutine(float temp, int tokens, Action<SettingsResponse> onSuccess, Action<string> onFailure)
    {
        SettingsRequest req = new SettingsRequest { temperature = temp, max_tokens = tokens };
        string json = JsonUtility.ToJson(req);
        
        using (UnityWebRequest request = new UnityWebRequest($"{baseUrl}/system/settings", "POST"))
        {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success) onFailure?.Invoke(request.error);
            else onSuccess?.Invoke(JsonUtility.FromJson<SettingsResponse>(request.downloadHandler.text));
        }
    }
}