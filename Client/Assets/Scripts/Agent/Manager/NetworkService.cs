using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;

public class NetworkService : SingletonPersistent<NetworkService>
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
        
        using (UnityWebRequest request = new UnityWebRequest($"{baseUrl}/game/turn", "POST"))
        {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            
            System.Diagnostics.Stopwatch stopwatch = new System.Diagnostics.Stopwatch();
            stopwatch.Start();
            
            yield return request.SendWebRequest();
            
            stopwatch.Stop();
            float elapsedSeconds = stopwatch.ElapsedMilliseconds / 1000f;
            
            Debug.Log($"<color=orange><b>[性能监控] AI 思考总耗时: {elapsedSeconds:F2} 秒</b></color>");

            if (request.result != UnityWebRequest.Result.Success) 
            {
                Debug.LogError($"[NetworkService] Turn 请求失败: {request.error}");
                onFailure?.Invoke(request.error);
            }
            else 
            {
                string rawText = request.downloadHandler.text;
                onSuccess?.Invoke(JsonUtility.FromJson<GameTurnResponse>(rawText));
            }
        }
    }
    
    public IEnumerator TriggerReflectionCoroutine(List<string> roommates, string eventHistory, Action<ReflectionResponse> onSuccess)
    {
        ReflectionRequest req = new ReflectionRequest 
        { 
            active_roommates = roommates, 
            recent_events = eventHistory 
        };
        string json = JsonUtility.ToJson(req);
    
        Debug.Log($"<color=cyan>[System] 正在触发 AI 深度反思: {eventHistory}</color>");

        using (UnityWebRequest request = new UnityWebRequest($"{baseUrl}/game/reflect", "POST"))
        {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");

            yield return request.SendWebRequest();

            if (request.result == UnityWebRequest.Result.Success)
            {
                var res = JsonUtility.FromJson<ReflectionResponse>(request.downloadHandler.text);
                onSuccess?.Invoke(res);
            }
            else
            {
                Debug.LogWarning("[NetworkService] 反思请求失败，但不影响游戏继续执行。");
            }
        }
    }
    
    // ============================================
    // 存档与读档网络请求
    // ============================================

    /// <summary>
    /// 请求保存游戏进度到指定槽位
    /// </summary>
    public IEnumerator SaveGameCoroutine(SaveGameRequest req, Action<SaveGameResponse> onSuccess, Action<string> onFailure)
    {
        string json = JsonUtility.ToJson(req);
        Debug.Log($"[NetworkService] 发送存档请求: {json}");

        using (UnityWebRequest request = new UnityWebRequest($"{baseUrl}/game/save", "POST"))
        {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError($"[NetworkService] 存档请求失败: {request.error}");
                onFailure?.Invoke(request.error);
            }
            else
            {
                string rawText = request.downloadHandler.text;
                Debug.Log($"[NetworkService] 存档成功返回: {rawText}");
                onSuccess?.Invoke(JsonUtility.FromJson<SaveGameResponse>(rawText));
            }
        }
    }

    /// <summary>
    /// 请求从指定槽位加载游戏进度
    /// </summary>
    public IEnumerator LoadGameCoroutine(int slotId, Action<LoadGameResponse> onSuccess, Action<string> onFailure)
    {
        Debug.Log($"[NetworkService] 请求读取槽位 {slotId} 的数据...");
        
        using (UnityWebRequest request = UnityWebRequest.Get($"{baseUrl}/game/load/{slotId}"))
        {
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError($"[NetworkService] 读档请求失败: {request.error}");
                onFailure?.Invoke(request.error);
            }
            else
            {
                string rawText = request.downloadHandler.text;
                Debug.Log($"[NetworkService] 读档成功返回: {rawText}");
                onSuccess?.Invoke(JsonUtility.FromJson<LoadGameResponse>(rawText));
            }
        }
    }

    /// <summary>
    /// 获取所有 3 个存档槽位的摘要信息 (用于 UI 面板展示)
    /// </summary>
    public IEnumerator GetSavesInfoCoroutine(Action<SavesInfoResponse> onSuccess, Action<string> onFailure)
    {
        Debug.Log("[NetworkService] 请求获取所有存档槽位信息...");

        using (UnityWebRequest request = UnityWebRequest.Get($"{baseUrl}/game/saves_info"))
        {
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError($"[NetworkService] 获取槽位信息失败: {request.error}");
                onFailure?.Invoke(request.error);
            }
            else
            {
                string rawText = request.downloadHandler.text;
                Debug.Log($"[NetworkService] 槽位信息返回: {rawText}");
                onSuccess?.Invoke(JsonUtility.FromJson<SavesInfoResponse>(rawText));
            }
        }
    }
    
    // ============================================
    // 系统设置
    // ============================================

    public IEnumerator RebuildKnowledgeCoroutine(Action<string> onSuccess, Action<string> onFailure)
    {
        using (UnityWebRequest request = new UnityWebRequest($"{baseUrl}/system/rebuild_knowledge", "POST"))
        {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes("{}");
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success) 
                onFailure?.Invoke(request.error);
            else 
            {
                // 解析返回的 JSON (可以复用 SaveGameResponse 的结构，因为都有 status 和 message)
                var res = JsonUtility.FromJson<SaveGameResponse>(request.downloadHandler.text);
                if (res.status == "success") onSuccess?.Invoke(res.message);
                else onFailure?.Invoke(res.message);
            }
        }
    }

    public IEnumerator UpdateSettingsCoroutine(float temp, int tokens, string apiKey, string baseUrl, string modelName, Action<SettingsResponse> onSuccess, Action<string> onFailure)
    {
        SettingsRequest req = new SettingsRequest 
        { 
            temperature = temp, 
            max_tokens = tokens,
            api_key = apiKey,
            base_url = baseUrl,
            model_name = modelName
        };
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