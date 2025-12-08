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
    [SerializeField] private string apiKey = "dummy";
    [SerializeField] private string apiUrl = "http://localhost:8000/v1/chat/completions";
    [SerializeField] private string modelName = "gpt-3.5-turbo";

    // 发送请求，onTokenReceived 是每收到一个字的回调，onComplete 是完成后的回调
    public async Task ChatStreamAsync(List<ChatMessage> history, Action<string> onTokenReceived, Action<string> onComplete)
    {
        var requestData = new
        {
            model = modelName,
            messages = history,
            stream = true
        };

        string json = JsonConvert.SerializeObject(requestData);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiKey}");
            
            // 发送请求
            using (var request = new HttpRequestMessage(HttpMethod.Post, apiUrl))
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