using System.Collections.Generic;
using UnityEngine;
using System.Text.RegularExpressions;
using Newtonsoft.Json;
using UnityEngine.SceneManagement;

public class GameDirector : MonoBehaviour
{
    [Header("Components")]
    [SerializeField] private LLMClient llmClient;
    [SerializeField] private ChatUIManager uiManager;

    [Header("Game State")]
    [SerializeField] private float currentMoney = 1500f;
    [SerializeField] private float currentSanity = 100f; 
    [SerializeField] private float currentGPA = 4.0f;    

    [Header("Time System")]
    [SerializeField] private int currentDay = 1;
    [SerializeField] private int maxDays = 7;
    private string[] timeSlots = new string[] { "上午", "下午", "晚上" };
    private int timeIndex = 0; 
    
    private bool isGameOver = false;

    // --- 模块化 Prompt 设置 ---
    [Header("Prompt Modules (Drag .txt files here)")]
    [SerializeField] private TextAsset rulesPrompt;      // 对应 Prompt_CoreRules.txt
    [SerializeField] private TextAsset worldPrompt;      // 对应 Prompt_World.txt
    [SerializeField] private TextAsset characterPrompt;  // 对应 Prompt_Characters.txt

    private List<ChatMessage> chatHistory = new List<ChatMessage>();

    private void Start()
    {
        // 1. 初始化数值
        currentMoney = 1500f;
        currentSanity = 100f;
        currentGPA = 4.0f;
        currentDay = 1;
        timeIndex = 0;
        isGameOver = false;

        uiManager.UpdateStats(currentMoney, currentSanity, currentGPA, currentDay, timeSlots[timeIndex]);
        uiManager.OnOptionClicked += HandlePlayerChoice;

        // 2. 拼接 Prompt
        string fullSystemPrompt = BuildSystemPrompt();
        if (string.IsNullOrEmpty(fullSystemPrompt))
        {
            Debug.LogError("Prompt 文件未赋值！请检查 Inspector。");
            return;
        }

        chatHistory.Add(new ChatMessage { role = "system", content = fullSystemPrompt });

        // 3. 发送开场
        SendRequestToAI("游戏开始。现在是第1天上午。请生成开场剧情（比如刚开学，或者刚睡醒），并给出第一组行动选项。");
    }

    // 将三个文件的内容拼成一个大的字符串
    private string BuildSystemPrompt()
    {
        if (rulesPrompt == null || worldPrompt == null || characterPrompt == null) return null;
        
        // 使用换行符拼接，确保 AI 能分清段落
        return rulesPrompt.text + "\n\n" + worldPrompt.text + "\n\n" + characterPrompt.text;
    }

    private void HandlePlayerChoice(StoryOption option)
    {
        if (isGameOver && option.id != "RESTART") return;
        
        if (option.id == "RESTART")
        {
            SceneManager.LoadScene(SceneManager.GetActiveScene().name);
            return;
        }

        uiManager.AddPlayerMessage(option.content);
        AdvanceTime();

        if (isGameOver) return; 

        // 构造提示词
        string timeStr = $"第{currentDay}天 {timeSlots[timeIndex]}";
        string statsStr = $"余额:{currentMoney}, 心情:{currentSanity}, GPA:{currentGPA}";
        
        string hiddenPrompt = $"\n(系统: 玩家选择[{option.text}]。时间[{timeStr}]。状态[{statsStr}]。请生成剧情，并严格输出包含3个属性变化的JSON。)";

        if (currentDay == maxDays && timeIndex == 2)
        {
            hiddenPrompt += " (警告：这是最后的夜晚，请在剧情中营造结局前的紧张感！)";
        }

        SendRequestToAI(option.content + hiddenPrompt);
    }

    private void AdvanceTime()
    {
        timeIndex++;
        if (timeIndex >= timeSlots.Length)
        {
            timeIndex = 0;
            currentDay++;
        }

        if (currentDay > maxDays)
        {
            TriggerFinalEnding();
            return;
        }

        uiManager.UpdateStats(currentMoney, currentSanity, currentGPA, currentDay, timeSlots[timeIndex]);
    }

    private async void SendRequestToAI(string userMessage)
    {
        AddToHistory("user", userMessage);
        uiManager.CreateAIBubble();

        await llmClient.ChatStreamAsync(
            chatHistory,
            (streamText) => { uiManager.UpdateCurrentAIBubble(streamText); },
            (finalText) => {
                if (string.IsNullOrEmpty(finalText)) return;

                // 1. 处理数值 (可能触发 Game Over)
                string textNoCmd = ProcessGameCommands(finalText);
                
                // 2. 处理选项 (剔除标签)
                string textClean = ProcessOptions(textNoCmd, out List<StoryOption> options);

                // 3. 渲染干净的文本 (即使死了也要让玩家看到死因)
                uiManager.DestroyCurrentStreamingBubble();
                RenderDialogue(textClean); 
                AddToHistory("assistant", finalText);

                // 4. 如果死了，停止后续逻辑
                if (isGameOver) return; 

                // 5. 如果活着，显示选项
                uiManager.ShowOptions(options);
            }
        );
    }

    // --- 结局逻辑 ---

    private void TriggerFinalEnding()
    {
        isGameOver = true;
        string endingType = "普通幸存者";
        if (currentMoney <= 0) endingType = "破产乞讨";
        else if (currentGPA >= 3.5f && currentMoney > 1000) endingType = "完美赢家";
        else if (currentGPA < 1.5f) endingType = "挂科退学";

        uiManager.AddSystemMessage($"【7天期满】达成结局：{endingType}");
        StartCoroutine(GenerateEnding($"时间到。状态：金钱{currentMoney}, GPA{currentGPA}。结局：{endingType}。请写结局总结。"));
    }

    private void TriggerImmediateEnding(string reason)
    {
        isGameOver = true;
        uiManager.ClearOptions();
        uiManager.AddSystemMessage($"【突发恶耗】{reason}");
        StartCoroutine(GenerateEnding($"玩家因为【{reason}】导致游戏提前结束。请根据最后发生的事件，写一段悲惨或讽刺的结局描述。"));
    }

    private System.Collections.IEnumerator GenerateEnding(string instruction)
    {
        yield return null; 
        uiManager.CreateAIBubble();
        var endHistory = new List<ChatMessage>(chatHistory);
        endHistory.Add(new ChatMessage { role = "system", content = instruction });

        var task = llmClient.ChatStreamAsync(endHistory,
            (s) => uiManager.UpdateCurrentAIBubble(s),
            (f) => {
                uiManager.DestroyCurrentStreamingBubble();
                uiManager.AddStaticAIBubble("系统", f);
                
                List<StoryOption> ops = new List<StoryOption>();
                ops.Add(new StoryOption { id = "RESTART", text = "重新开始", content = "" });
                uiManager.ShowOptions(ops);
            }
        );
    }

    // --- 数据解析 ---

    private string ProcessGameCommands(string rawText)
    {
        string pattern = @"<cmd>(.*?)</cmd>";
        MatchCollection matches = Regex.Matches(rawText, pattern, RegexOptions.Singleline);
        foreach (Match match in matches)
        {
            try
            {
                var cmd = JsonConvert.DeserializeObject<GameEventCommand>(match.Groups[1].Value);
                if (cmd != null)
                {
                    currentMoney += cmd.money_change;
                    
                    currentSanity += cmd.sanity_change;
                    currentSanity = Mathf.Clamp(currentSanity, 0, 100);

                    currentGPA += cmd.gpa_change;
                    currentGPA = Mathf.Clamp(currentGPA, 0f, 4.0f);

                    uiManager.UpdateStats(currentMoney, currentSanity, currentGPA, currentDay, timeSlots[timeIndex]);

                    if (!isGameOver) 
                    {
                        if (currentMoney <= 0) { TriggerImmediateEnding("破产！余额归零"); }
                        else if (currentSanity <= 0) { TriggerImmediateEnding("精神崩溃！SAN值归零"); }
                        else if (currentGPA <= 0.8f) { TriggerImmediateEnding("学业预警！绩点过低"); }
                    }
                }
            }
            catch { }
        }
        return Regex.Replace(rawText, pattern, "").Trim();
    }

    private string ProcessOptions(string rawText, out List<StoryOption> options)
    {
        options = new List<StoryOption>();
        string pattern = @"<options>(.*?)</options>";
        Match match = Regex.Match(rawText, pattern, RegexOptions.Singleline);

        if (match.Success)
        {
            try
            {
                options = JsonConvert.DeserializeObject<List<StoryOption>>(match.Groups[1].Value);
            }
            catch { } 
            return rawText.Replace(match.Value, "").Trim();
        }
        return rawText;
    }

    private void RenderDialogue(string rawText)
    {
        string[] lines = rawText.Split(new char[] { '\n' }, System.StringSplitOptions.RemoveEmptyEntries);
        foreach (string line in lines)
        {
            string trimLine = line.Trim();
            if (string.IsNullOrWhiteSpace(trimLine)) continue;

            string charName = "旁白";
            string body = trimLine;
            string[] parts = trimLine.Split(new char[] { '：', ':' }, 2);
            if (parts.Length == 2) { charName = parts[0].Trim(); body = parts[1].Trim(); }

            if (charName == "突发事件" || charName == "旁白" || charName == "系统")
                uiManager.AddSystemMessage(body);
            else
                uiManager.AddStaticAIBubble(charName, body);
        }
    }

    private void AddToHistory(string role, string content)
    {
        chatHistory.Add(new ChatMessage { role = role, content = content });
        if (chatHistory.Count > 20) chatHistory.RemoveAt(1);
    }
}