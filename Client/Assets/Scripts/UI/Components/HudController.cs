using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class HudController : MonoBehaviour
{
    [Header("Data")]
    [SerializeField] private CharacterArtLibrary artLibrary;

    [Header("Stage Settings")]
    [SerializeField] private RectTransform stageContainer;
    [SerializeField] private GameObject characterPrefab;

    private readonly Vector2 POS_LEFT = new Vector2(-500, 0);
    private readonly Vector2 POS_CENTER = new Vector2(0, 0);
    private readonly Vector2 POS_RIGHT = new Vector2(500, 0);

    [Header("Dialogue UI")]
    [SerializeField] private TMP_Text speakerNameText;
    [SerializeField] private TextAnimator textAnimator; 
    [SerializeField] private GameObject dialoguePanel; 

    [Header("Interactions")]
    [SerializeField] private TMP_InputField inputField;
    [SerializeField] private Button sendButton;
    [SerializeField] private TMP_Dropdown targetDropdown; 
    [SerializeField] private Button historyButton; 
    [SerializeField] private Button pauseButton;

    [Header("Stats")]
    [SerializeField] private TMP_Text moneyText;
    [SerializeField] private TMP_Text sanText;
    [SerializeField] private TMP_Text gpaText;

    // 核心数据结构：ID -> 实例控制器
    private Dictionary<string, CharacterPortrait> activeCharacters = new Dictionary<string, CharacterPortrait>();

    public System.Action<string, string> OnSendRequest;

    private void Start()
    {
        sendButton.onClick.AddListener(HandleSendClick);
        historyButton.onClick.AddListener(() => UIManager.Instance.OpenPanel("HistoryPanel"));
        pauseButton.onClick.AddListener(() => GameManager.Instance.PauseGame());
    }

    // --- 动态生成角色 ---
    public void InitializeRoommates(List<string> activeRoommates)
    {
        // 1. 清理当前舞台上的所有角色
        foreach (var charCtrl in activeCharacters.Values)
        {
            if(charCtrl != null) Destroy(charCtrl.gameObject);
        }
        activeCharacters.Clear();

        // 2. 更新下拉框
        targetDropdown.ClearOptions();
        targetDropdown.AddOptions(activeRoommates);

        // 3. 动态生成新角色
        if (activeRoommates.Count > 0)
        {
            // 根据人数决定站位策略
            // 这里演示简单的逻辑：按顺序放入 Left, Center, Right
            // 你可以写更复杂的逻辑，比如 2个人时站在 (-300, 300)
            
            List<Vector2> positions = GetStandPositions(activeRoommates.Count);

            for (int i = 0; i < activeRoommates.Count; i++)
            {
                string id = activeRoommates[i];
                SpawnCharacter(id, positions[i]);
            }
        }
    }

    // 根据人数计算站位坐标
    private List<Vector2> GetStandPositions(int count)
    {
        List<Vector2> pos = new List<Vector2>();
        if (count == 1)
        {
            pos.Add(POS_CENTER);
        }
        else if (count == 2)
        {
            pos.Add(new Vector2(-300, 0));
            pos.Add(new Vector2(300, 0));
        }
        else // 3人及以上
        {
            pos.Add(POS_LEFT);
            pos.Add(POS_CENTER);
            pos.Add(POS_RIGHT);
        }
        return pos;
    }
    
    private void SpawnCharacter(string id, Vector2 targetPos)
    {
        // 1. 获取数据 (现在返回的是 CharacterData ScriptableObject)
        CharacterData data = artLibrary.GetCharacter(id);
        
        if (data == null) 
        {
            Debug.LogWarning($"找不到 ID 为 {id} 的角色数据！");
            return;
        }

        // 实例化 Prefab
        GameObject go = Instantiate(characterPrefab, stageContainer);
        CharacterPortrait portrait = go.GetComponent<CharacterPortrait>();

        // 2. 初始化 (注意字段名的变化)
        // 以前是 art.portrait，现在是 data.portrait
        portrait.Initialize(id, data.portrait); 
        
        portrait.SetPosition(targetPos, instant: true); 
        portrait.Enter();

        activeCharacters[id.ToLower()] = portrait;
    }

    // --- 消息处理与演出 ---
    public void AppendMessage(string speaker, string content, Color color)
    {
        speakerNameText.text = speaker;
        speakerNameText.color = color;

        if (textAnimator != null) textAnimator.ShowText(content);
        
        GameManager.Instance.AddChatLog(speaker, content);

        UpdatePortraitFocus(speaker);
    }

    private void UpdatePortraitFocus(string speakerName)
    {
        string speakerKey = speakerName.ToLower();

        foreach (var kvp in activeCharacters)
        {
            string charId = kvp.Key;
            CharacterPortrait portrait = kvp.Value;

            if (charId == speakerKey)
            {
                portrait.SetFocus(true); // 高亮说话者
            }
            else
            {
                portrait.SetFocus(false); // 变暗其他人
            }
        }
    }

    public void HandleSendClick()
    {
        if (string.IsNullOrEmpty(inputField.text)) return;
        string content = inputField.text;
        string targetId = targetDropdown.options[targetDropdown.value].text.ToLower();
        
        // 玩家说话时，所有角色变暗，或者高亮目标
        foreach (var kvp in activeCharacters)
        {
            kvp.Value.SetFocus(kvp.Key == targetId);
        }

        OnSendRequest?.Invoke(content, targetId);
        AppendMessage("Player", content, Color.cyan);
        inputField.text = "";
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
}