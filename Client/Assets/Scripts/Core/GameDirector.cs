using System.Collections.Generic;
using UnityEngine;
using System.Text.RegularExpressions;
using Newtonsoft.Json;
using UnityEngine.SceneManagement;
using SaveSystem; // Using new namespace

public class GameDirector : MonoBehaviour
{
    [Header("Components")]
    [SerializeField] private LLMClient llmClient;
    // [SerializeField] private ChatUIManager uiManager; // Decoupled

    [Header("Game State")]
    [SerializeField] private float _currentMoney = 1500f;
    [SerializeField] private float _currentSanity = 100f; 
    [SerializeField] private float _currentGPA = 4.0f;    

    [Header("Time System")]
    [SerializeField] private int _currentDay = 1;
    [SerializeField] private int _maxDays = 7;
    private string[] _timeSlots = new string[] { "上午", "下午", "晚上" };
    private int _timeIndex = 0; 
    
    private bool _isGameOver = false;

    private List<ChatMessage> _chatHistory = new List<ChatMessage>();

    [Header("Persistence")]
    [SerializeField] private SaveController saveController; 

    private void Awake()
    {
        MsgCenter.RegisterMsg(MsgConst.MSG_GAME_OPTION_CLICKED, OnOptionClickedEvent);
    }

    private void OnDestroy()
    {
        MsgCenter.UnregisterMsg(MsgConst.MSG_GAME_OPTION_CLICKED, OnOptionClickedEvent);
    }

    private void OnOptionClickedEvent(params object[] args)
    {
        if (args.Length > 0 && args[0] is StoryOption option)
        {
            HandlePlayerChoice(option);
        }
    }

    private async void Start()
    {
        if (saveController == null) saveController = gameObject.AddComponent<SaveController>(); 
        
        var data = await saveController.LoadGameAsync();
        
        if (data != null)
        {
            Debug.Log("[GameDirector] Found Save Data. Loading...");
            RestoreGameState(data);
        }
        else
        {
            Debug.Log("[GameDirector] No Save Data. Starting New Game...");
            StartNewGame();
        }
        
        // uiManager.OnOptionClicked removed
    }

    private void StartNewGame()
    {
        _currentMoney = 1500f;
        _currentSanity = 100f;
        _currentGPA = 4.0f;
        _currentDay = 1;
        _maxDays = 12; 
        _timeIndex = 0;
        _isGameOver = false;

        // Update Stats
        MsgCenter.SendMsg(MsgConst.MSG_GAME_UPDATE_STATS, _currentMoney, _currentSanity, _currentGPA, _currentDay, _timeSlots[_timeIndex]);

        string selectedIds = PlayerPrefs.GetString("SelectedRoommates", "");
        
        string dynamicContext = BuildDynamicContext(selectedIds);
        _chatHistory.Add(new ChatMessage { role = "system", content = dynamicContext });

        SendRequestToAI($"游戏开始。现在是第1天上午。你的室友是：{selectedIds}。请描述寝室当前的状况（观察阶段），并给出玩家的行动选项。");
    }

    private void RestoreGameState(SaveModel.SaveData data)
    {
        try 
        {
            _currentMoney = data.Money;
            _currentSanity = data.Sanity;
            _currentGPA = data.GPA;
            _currentDay = data.Day;
            _timeIndex = data.TimeIndex;
            _chatHistory = data.History ?? new List<ChatMessage>();
            
            // Update Stats
            MsgCenter.SendMsg(MsgConst.MSG_GAME_UPDATE_STATS, _currentMoney, _currentSanity, _currentGPA, _currentDay, _timeSlots[_timeIndex]);
            
            if (_chatHistory.Count > 0)
            {
                var lastMsg = _chatHistory[_chatHistory.Count - 1];
                if (lastMsg.role == "assistant")
                {
                    RenderDialogue(lastMsg.content);
                }
            }
        }
        catch (System.Exception e)
        {
            Debug.LogError($"Failed to restore save: {e}");
            StartNewGame();
        }
    }

    // ... SaveGame and Context building same ...

    public async void SaveGame()
    {
        await saveController.SaveGameAsync(_currentMoney, _currentSanity, _currentGPA, _currentDay, _timeIndex, _chatHistory);
    }

    private string BuildDynamicContext(string selectedIds)
    {
        string charContext = $"玩家选择了以下室友 ID: {selectedIds}。未选择的角色将作为外部事件出现。";
        return charContext;
    }

    private void HandlePlayerChoice(StoryOption option)
    {
        if (_isGameOver && option.id != "RESTART") return;
        
        if (option.id == "RESTART")
        {
            PlayerPrefs.DeleteKey("CurrentSessionID"); 
            PlayerPrefs.SetString("CurrentSessionID", System.Guid.NewGuid().ToString());
            SceneManager.LoadScene(SceneManager.GetActiveScene().name);
            return;
        }

        // Add Player Message
        MsgCenter.SendMsg(MsgConst.MSG_GAME_ADD_MESSAGE, "我", option.content);

        AdvanceTime();
        
        SaveGame();

        if (_isGameOver) return; 
        
        string timeStr = $"第{_currentDay}天 {_timeSlots[_timeIndex]}";
        string statsStr = $"余额:{_currentMoney}, 心情:{_currentSanity}, GPA:{_currentGPA}";
        
        string hiddenPrompt = $"\n(系统: 玩家选择[{option.text}]。时间[{timeStr}]。状态[{statsStr}]。请生成剧情，并严格输出包含3个属性变化的JSON。)";

        if (_currentDay == _maxDays && _timeIndex == 2)
        {
            hiddenPrompt += " (警告：这是最后的夜晚，请在剧情中营造结局前的紧张感！)";
        }

        SendRequestToAI(option.content + hiddenPrompt);
    }

    private void AdvanceTime()
    {
        _timeIndex++;
        if (_timeIndex >= _timeSlots.Length)
        {
            _timeIndex = 0;
            _currentDay++;
        }

        if (_currentDay > _maxDays)
        {
            TriggerFinalEnding();
            return;
        }

        MsgCenter.SendMsg(MsgConst.MSG_GAME_UPDATE_STATS, _currentMoney, _currentSanity, _currentGPA, _currentDay, _timeSlots[_timeIndex]);
    }

    private async void SendRequestToAI(string userMessage)
    {
        AddToHistory("user", userMessage);
        
        // Create Bubble
        MsgCenter.SendMsgAct(MsgConst.MSG_GAME_BUBBLE_CREATE);

        await llmClient.ChatStreamAsync(
            _chatHistory,
            (streamText) => { 
                // Update Bubble
                MsgCenter.SendMsg(MsgConst.MSG_GAME_BUBBLE_UPDATE, streamText);
            },
            (finalText) => {
                if (string.IsNullOrEmpty(finalText)) return;

                string textNoCmd = ProcessGameCommands(finalText);
                string textClean = ProcessOptions(textNoCmd, out List<StoryOption> options);

                // Destroy Bubble
                MsgCenter.SendMsgAct(MsgConst.MSG_GAME_BUBBLE_DESTROY);

                RenderDialogue(textClean); 
                AddToHistory("assistant", finalText);

                if (_isGameOver) return; 

                // Show Options
                MsgCenter.SendMsg(MsgConst.MSG_GAME_SHOW_OPTIONS, options);
            }
        );
    }

    private void TriggerFinalEnding()
    {
        _isGameOver = true;
        string endingType = "普通幸存者";
        if (_currentMoney <= 0) endingType = "破产乞讨";
        else if (_currentGPA >= 3.5f && _currentMoney > 1000) endingType = "完美赢家";
        else if (_currentGPA < 1.5f) endingType = "挂科退学";

        MsgCenter.SendMsg(MsgConst.MSG_GAME_ADD_MESSAGE, "系统", $"【7天期满】达成结局：{endingType}");
        StartCoroutine(GenerateEnding($"时间到。状态：金钱{_currentMoney}, GPA{_currentGPA}。结局：{endingType}。请写结局总结。"));
    }

    private void TriggerImmediateEnding(string reason)
    {
        _isGameOver = true;
        MsgCenter.SendMsgAct(MsgConst.MSG_GAME_CLEAR_OPTIONS);
        
        MsgCenter.SendMsg(MsgConst.MSG_GAME_ADD_MESSAGE, "系统", $"【突发恶耗】{reason}");
        
        StartCoroutine(GenerateEnding($"玩家因为【{reason}】导致游戏提前结束。请根据最后发生的事件，写一段悲惨或讽刺的结局描述。"));
    }

    private System.Collections.IEnumerator GenerateEnding(string instruction)
    {
        yield return null; 
        
        MsgCenter.SendMsgAct(MsgConst.MSG_GAME_BUBBLE_CREATE);

        var endHistory = new List<ChatMessage>(_chatHistory);
        endHistory.Add(new ChatMessage { role = "system", content = instruction });

        var task = llmClient.ChatStreamAsync(endHistory,
            (s) => MsgCenter.SendMsg(MsgConst.MSG_GAME_BUBBLE_UPDATE, s),
            (f) => {
                MsgCenter.SendMsgAct(MsgConst.MSG_GAME_BUBBLE_DESTROY);
                
                MsgCenter.SendMsg(MsgConst.MSG_GAME_ADD_MESSAGE, "系统", f);
                
                List<StoryOption> ops = new List<StoryOption>();
                ops.Add(new StoryOption { id = "RESTART", text = "重新开始", content = "" });
                
                MsgCenter.SendMsg(MsgConst.MSG_GAME_SHOW_OPTIONS, ops);
            }
        );
    }

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
                    _currentMoney += cmd.money_change;
                    
                    _currentSanity += cmd.sanity_change;
                    _currentSanity = Mathf.Clamp(_currentSanity, 0, 100);

                    _currentGPA += cmd.gpa_change;
                    _currentGPA = Mathf.Clamp(_currentGPA, 0f, 4.0f);

                    MsgCenter.SendMsg(MsgConst.MSG_GAME_UPDATE_STATS, _currentMoney, _currentSanity, _currentGPA, _currentDay, _timeSlots[_timeIndex]);

                    if (!_isGameOver) 
                    {
                        if (_currentMoney <= 0) { TriggerImmediateEnding("破产！余额归零"); }
                        else if (_currentSanity <= 0) { TriggerImmediateEnding("精神崩溃！SAN值归零"); }
                        else if (_currentGPA <= 0.8f) { TriggerImmediateEnding("学业预警！绩点过低"); }
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

            // Unified Message
            MsgCenter.SendMsg(MsgConst.MSG_GAME_ADD_MESSAGE, charName, body);
        }
    }

    private void AddToHistory(string role, string content)
    {
        _chatHistory.Add(new ChatMessage { role = role, content = content });
        if (_chatHistory.Count > 20) _chatHistory.RemoveAt(1);
    }
}