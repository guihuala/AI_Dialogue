using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class HudController : MonoBehaviour
{
    [Header("Data")]
    [SerializeField] private CharacterArtLibrary artLibrary;

    [Header("Stage Settings (Dynamic Tachie)")]
    [SerializeField] private RectTransform stageContainer; // 角色立绘的父节点
    [SerializeField] private GameObject characterPrefab;   // CharacterTachie Prefab
    
    // 简单的站位定义
    private readonly Vector2 POS_LEFT = new Vector2(-400, 0);
    private readonly Vector2 POS_CENTER = new Vector2(0, 0);
    private readonly Vector2 POS_RIGHT = new Vector2(400, 0);

    [Header("Dialogue UI")]
    [SerializeField] private TMP_Text speakerNameText;
    [SerializeField] private TextAnimator textAnimator; 
    [SerializeField] private GameObject dialoguePanel; 

    [Header("Options UI (New)")]
    [SerializeField] private GameObject optionsContainer; // 放3个按钮的父节点
    [SerializeField] private Button[] optionButtons;      // 3个按钮

    [Header("Interactions")]
    [SerializeField] private Button historyButton; 
    [SerializeField] private Button pauseButton;

    [Header("Stats")]
    [SerializeField] private TMP_Text moneyText;
    [SerializeField] private TMP_Text sanText;
    [SerializeField] private TMP_Text gpaText;

    // 运行时数据：ID -> 实例控制器
    private Dictionary<string, CharacterPortrait> activeCharacters = new Dictionary<string, CharacterPortrait>();

    // 事件：当玩家点击某个选项时触发
    public System.Action<string> OnOptionSelected; 

    private void Start()
    {
        // 绑定基础按钮
        if(historyButton) historyButton.onClick.AddListener(() => UIManager.Instance.OpenPanel("HistoryPanel"));
        if(pauseButton) pauseButton.onClick.AddListener(() => GameManager.Instance.PauseGame());
        
        // 初始隐藏选项
        if(optionsContainer) optionsContainer.SetActive(false);
    }

    // --- 1. 动态生成角色 ---
    public void InitializeRoommates(List<string> activeRoommates)
    {
        // 清理旧角色
        foreach (var charCtrl in activeCharacters.Values)
        {
            if(charCtrl != null) Destroy(charCtrl.gameObject);
        }
        activeCharacters.Clear();

        // 生成新角色
        if (activeRoommates != null && activeRoommates.Count > 0)
        {
            List<Vector2> positions = GetStandPositions(activeRoommates.Count);
            for (int i = 0; i < activeRoommates.Count; i++)
            {
                SpawnCharacter(activeRoommates[i], positions[i]);
            }
        }
    }

    private List<Vector2> GetStandPositions(int count)
    {
        List<Vector2> pos = new List<Vector2>();
        if (count == 1) pos.Add(POS_CENTER);
        else if (count == 2) { pos.Add(new Vector2(-300, 0)); pos.Add(new Vector2(300, 0)); }
        else { pos.Add(POS_LEFT); pos.Add(POS_CENTER); pos.Add(POS_RIGHT); }
        return pos;
    }

    private void SpawnCharacter(string id, Vector2 targetPos)
    {
        var data = artLibrary.GetCharacter(id);
        if (data == null) return;

        GameObject go = Instantiate(characterPrefab, stageContainer);
        CharacterPortrait tachie = go.GetComponent<CharacterPortrait>();

        tachie.Initialize(id, data.portrait); 
        tachie.SetPosition(targetPos, instant: true); 
        tachie.Enter();

        activeCharacters[id.ToLower()] = tachie;
    }

    // --- 2. 显示选项 (核心新功能) ---
    public void ShowOptions(List<string> options)
    {
        optionsContainer.SetActive(true);

        for (int i = 0; i < optionButtons.Length; i++)
        {
            if (i < options.Count)
            {
                optionButtons[i].gameObject.SetActive(true);
                var btnText = optionButtons[i].GetComponentInChildren<TMP_Text>();
                if(btnText) btnText.text = options[i];
                
                string selectedContent = options[i];
                
                // 移除旧监听，添加新监听
                optionButtons[i].onClick.RemoveAllListeners();
                optionButtons[i].onClick.AddListener(() => {
                    optionsContainer.SetActive(false); // 点击后隐藏选项
                    OnOptionSelected?.Invoke(selectedContent);
                });
            }
            else
            {
                optionButtons[i].gameObject.SetActive(false);
            }
        }
    }

    // --- 3. 播放对话序列 (核心新功能) ---
    public IEnumerator PlayDialogueSequence(List<DialogueTurn> sequence, System.Action onComplete)
    {
        foreach (var turn in sequence)
        {
            // A. 显示名字和颜色
            // 简单的颜色逻辑：玩家蓝色，NPC黄色
            Color nameColor = turn.speaker == "Player" ? Color.cyan : Color.yellow;
            speakerNameText.text = turn.speaker;
            speakerNameText.color = nameColor;

            // B. 高亮说话者立绘
            UpdatePortraitFocus(turn.speaker);

            // C. 播放文字 (等待打字机完成)
            bool finished = false;
            if (textAnimator != null)
            {
                textAnimator.ShowText(turn.content, () => finished = true);
            }
            else
            {
                // 如果没有 TextAnimator，直接显示并等待一下
                Debug.LogWarning("TextAnimator missing");
                finished = true; 
            }

            // D. 存入历史
            GameManager.Instance.AddChatLog(turn.speaker, turn.content);

            // E. 等待本句结束 (打字完成 + 额外停顿)
            while (!finished) yield return null;
            yield return new WaitForSeconds(1.0f); // 读完后停顿1秒，节奏感
        }
        
        // 序列播放完毕
        onComplete?.Invoke();
    }

    // --- 辅助显示方法 ---
    
    public void AppendMessage(string speaker, string content, Color color)
    {
        // 单条显示（用于显示玩家自己的选择，或者系统消息）
        speakerNameText.text = speaker;
        speakerNameText.color = color;
        if (textAnimator) textAnimator.ShowText(content);
        GameManager.Instance.AddChatLog(speaker, content);
        UpdatePortraitFocus(speaker);
    }

    public void ShowError(string error)
    {
        Debug.LogError($"[Game Error] {error}");
        AppendMessage("System Error", $"<color=red>{error}</color>", Color.red);
    }

    public void UpdatePlayerStats(PlayerStatsData stats)
    {
        if (stats == null) return;
        moneyText.text = $"$ {stats.money:F0}";
        sanText.text = $"SAN: {stats.san}";
        sanText.color = stats.san < 40 ? Color.red : Color.white; 
        gpaText.text = $"GPA: {stats.gpa:F2}";
        gpaText.color = stats.gpa > 3.8f ? Color.green : Color.white;
    }

    private void UpdatePortraitFocus(string speakerName)
    {
        string speakerKey = speakerName.ToLower();
        foreach (var kvp in activeCharacters)
        {
            if (kvp.Key == speakerKey) kvp.Value.SetFocus(true);
            else kvp.Value.SetFocus(false);
        }
    }
}