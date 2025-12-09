using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.IO;
using UnityEngine;
using Newtonsoft.Json;
using System;

public class LLMClient : MonoBehaviour
{
    [Header("API Config")]
    [SerializeField] private string _apiKey = "dummy";
    [SerializeField] private string _apiUrl = "http://localhost:8000/v1/chat/completions";
    [SerializeField] private string _modelName = "gpt-3.5-turbo";

    [Header("Session Config")]
    [SerializeField] private string _currentSessionId = "default";
    
    public void SetSessionId(string sessionId)
    {
        _currentSessionId = sessionId;
    }

    // --- Save / Load API ---

    public async Task<bool> SaveGameAsync(string jsonState)
    {
        var requestData = new { slot_id = _currentSessionId, game_data = JsonConvert.DeserializeObject(jsonState) };
        string json = JsonConvert.SerializeObject(requestData);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("X-Session-ID", _currentSessionId);
            string url = _apiUrl.Replace("/v1/chat/completions", "/game/save"); // Hacky but works for now

            try 
            {
                var response = await client.PostAsync(url, content);
                return response.IsSuccessStatusCode;
            }
            catch (Exception e)
            {
                Debug.LogError($"Save Failed: {e.Message}");
                return false;
            }
        }
    }

    public async Task<string> LoadGameAsync()
    {
        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("X-Session-ID", _currentSessionId);
            string url = _apiUrl.Replace("/v1/chat/completions", "/game/load");

            try
            {
                var response = await client.GetAsync(url);
                if (response.IsSuccessStatusCode)
                {
                    string json = await response.Content.ReadAsStringAsync();
                    // Extract game_data
                    var data = JsonConvert.DeserializeObject<Dictionary<string, object>>(json);
                    if (data != null && data.ContainsKey("game_data") && data["game_data"] != null)
                    {
                        return JsonConvert.SerializeObject(data["game_data"]);
                    }
                }
                return null;
            }
            catch (Exception e)
            {
                Debug.LogError($"Load Failed: {e.Message}");
                return null;
            }
        }
    }

    // 发送请求，onTokenReceived 是每收到一个字的回调，onComplete 是完成后的回调
    public async Task ChatStreamAsync(List<ChatMessage> history, Action<string> onTokenReceived, Action<string> onComplete)
    {
        var requestData = new
        {
            model = _modelName,
            messages = history,
            stream = true
        };

        string json = JsonConvert.SerializeObject(requestData);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", $"Bearer {_apiKey}");
            client.DefaultRequestHeaders.Add("X-Session-ID", _currentSessionId); // Add Session ID Header
            
            // 发送请求
            using (var request = new HttpRequestMessage(HttpMethod.Post, _apiUrl))
            {
                request.Content = content;
                using (var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead))
                {
                    if (!response.IsSuccessStatusCode)
                    {
                        Debug.LogError($"API Error: {response.StatusCode}");
                        onComplete?.Invoke(null); // 失败返回 null
                        return;
                    }

                    using (var stream = await response.Content.ReadAsStreamAsync())
                    using (var reader = new StreamReader(stream))
                    {
                        StringBuilder fullContent = new StringBuilder();
                        
                        while (!reader.EndOfStream)
                        {
                            string line = await reader.ReadLineAsync();
                            if (string.IsNullOrWhiteSpace(line)) continue;
                            if (line.Trim() == "data: [DONE]") break;

                            if (line.StartsWith("data: "))
                            {
                                try
                                {
                                    string jsonStr = line.Substring(6);
                                    var chunk = JsonConvert.DeserializeObject<OpenAIStreamResponse>(jsonStr);
                                    
                                    if (chunk?.choices != null && chunk.choices.Count > 0)
                                    {
                                        string delta = chunk.choices[0].delta.content;
                                        if (!string.IsNullOrEmpty(delta))
                                        {
                                            fullContent.Append(delta);
                                            // 触发回调：告诉上层收到了新内容
                                            onTokenReceived?.Invoke(fullContent.ToString());
                                        }
                                    }
                                }
                                catch { /* 忽略解析错误 */ }
                            }
                        }
                        // 完成，返回完整内容
                        onComplete?.Invoke(fullContent.ToString());
                    }
                }
            }
        }
    }
}