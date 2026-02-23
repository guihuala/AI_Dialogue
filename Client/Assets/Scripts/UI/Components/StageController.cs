using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class StageController : MonoBehaviour
{
    [Header("Data")] 
    [SerializeField] private CharacterArtLibrary artLibrary;
    [SerializeField] private CharacterData playerData;

    [Header("Stage Settings")] 
    [SerializeField] private RectTransform stageContainer; 
    [SerializeField] private GameObject characterPrefab;

    [Header("Dialogue UI")] 
    [SerializeField] private TMP_Text speakerNameText;
    [SerializeField] private TextAnimator textAnimator;
    [SerializeField] private GameObject dialoguePanel;

    [Header("Options UI")] 
    [SerializeField] private GameObject optionsContainer;
    [SerializeField] private Button[] optionButtons;

    [Header("Buttons")] 
    [SerializeField] private Button historyButton;

    // 运行时数据
    private Dictionary<string, CharacterPortrait> activeCharacters = new Dictionary<string, CharacterPortrait>();
    public System.Action<string> OnOptionSelected;

    private void Start()
    {
        if (historyButton) historyButton.onClick.AddListener(() => UIManager.Instance.OpenPanel("HistoryPanel"));
        if (optionsContainer) optionsContainer.SetActive(false);

        if (GameManager.Instance != null)
        {
            GameManager.Instance.OnInitRoommates += InitializeRoommates;
            GameManager.Instance.OnShowOptions += ShowOptions;
            GameManager.Instance.OnShowImmediateMessage += ShowImmediateMessage;
            GameManager.Instance.OnPlayDialogueSequence += HandlePlayDialogueSequence;
        }
    }

    private void OnDestroy()
    {
        if (GameManager.Instance != null)
        {
            GameManager.Instance.OnInitRoommates -= InitializeRoommates;
            GameManager.Instance.OnShowOptions -= ShowOptions;
            GameManager.Instance.OnShowImmediateMessage -= ShowImmediateMessage;
            GameManager.Instance.OnPlayDialogueSequence -= HandlePlayDialogueSequence;
        }
    }

    public void InitializeRoommates(List<string> roommateIds)
    {
        // 1. 清理上一局/上一个场景遗留的立绘
        foreach (var kvp in activeCharacters)
        {
            if (kvp.Value != null) Destroy(kvp.Value.gameObject);
        }
        activeCharacters.Clear();

        // 2. 初始状态下，让主角站在画面正中央
        if (playerData != null)
        {
            SpawnPlayer(Vector2.zero); 
        }
    }

    // 动态生成主角
    private void SpawnPlayer(Vector2 targetPos)
    {
        GameObject playerObj = Instantiate(characterPrefab, stageContainer);
        CharacterPortrait pPortrait = playerObj.GetComponent<CharacterPortrait>();
        pPortrait.Initialize(playerData);
        pPortrait.SetPosition(targetPos, instant: true);
        pPortrait.Enter();
        
        string pId = playerData.id.ToLower();
        activeCharacters[pId] = pPortrait;
        activeCharacters["player"] = pPortrait;
        activeCharacters["我"] = pPortrait;
        activeCharacters["安然"] = pPortrait;
        activeCharacters["陆陈安然"] = pPortrait;
    }

    // 动态生成室友
    private void SpawnCharacter(string identifier, Vector2 targetPos)
    {
        var data = artLibrary.GetCharacter(identifier);
        if (data == null) return;

        GameObject go = Instantiate(characterPrefab, stageContainer);
        CharacterPortrait portrait = go.GetComponent<CharacterPortrait>();

        portrait.Initialize(data);
        portrait.SetPosition(targetPos, instant: true);
        portrait.Enter();

        activeCharacters[data.id.ToLower()] = portrait;
        activeCharacters[data.displayName.ToLower()] = portrait;
    }

    // 【核心新增】根据在场人数，自动等分计算舞台站位
    private List<Vector2> GetDynamicPositions(int count)
    {
        List<Vector2> pos = new List<Vector2>();
        if (count == 0) return pos;
        
        // 1个人时，永远在正中央
        if (count == 1) 
        {
            pos.Add(Vector2.zero);
            return pos;
        }

        // 多人时计算等分布局
        float totalWidth = 800f; // 你可以根据屏幕宽度调整这个值，值越大角色站得越开
        if (count >= 4) totalWidth = 1000f; 

        float startX = -totalWidth / 2f;
        float spacing = totalWidth / (count - 1);

        for (int i = 0; i < count; i++)
        {
            pos.Add(new Vector2(startX + i * spacing, 0));
        }

        return pos;
    }

    // 判断身份的辅助方法
    private bool IsPlayer(string spk)
    {
        spk = spk.ToLower();
        return spk == "player" || spk == "我" || spk == "陆陈安然" || spk == "安然" || (playerData != null && spk == playerData.id.ToLower());
    }

    public void HandlePlayDialogueSequence(List<DialogueTurn> sequence, System.Action onComplete)
    {
        // 1. 扫描本轮对话，找出所有需要出场的角色规范 ID
        HashSet<string> currentSpeakerIDs = new HashSet<string>();
        foreach (var turn in sequence)
        {
            string spk = turn.speaker.ToLower();
            if (spk == "system" || spk == "narrator" || spk == "gm") continue;

            string canonicalId = spk;
            if (IsPlayer(spk)) 
            {
                canonicalId = playerData.id.ToLower();
            }
            else
            {
                var data = artLibrary.GetCharacter(spk);
                if (data != null) canonicalId = data.id.ToLower();
            }
            currentSpeakerIDs.Add(canonicalId);
        }

        // 2. 决定谁应该留在台上
        List<string> charactersOnStage = new List<string>();
        
        foreach (var kvp in activeCharacters)
        {
            string cId = kvp.Value.CharacterID.ToLower();
            if (currentSpeakerIDs.Contains(cId) && !charactersOnStage.Contains(cId))
            {
                charactersOnStage.Add(cId);
            }
        }

        foreach (var spkId in currentSpeakerIDs)
        {
            if (!charactersOnStage.Contains(spkId)) charactersOnStage.Add(spkId);
        }

        // 3. 请退没有参与本轮对话的角色（包括主角如果没说话也会退场）
        List<string> keysToRemove = new List<string>();
        foreach (var kvp in activeCharacters)
        {
            string cId = kvp.Value.CharacterID.ToLower();
            if (!charactersOnStage.Contains(cId))
            {
                kvp.Value.Exit(); 
                keysToRemove.Add(kvp.Key);
            }
        }
        foreach (var key in keysToRemove) activeCharacters.Remove(key);

        // 4. 获取动态等分站位，并指挥角色移动或生成
        List<Vector2> positions = GetDynamicPositions(charactersOnStage.Count);
        for (int i = 0; i < charactersOnStage.Count; i++)
        {
            string cid = charactersOnStage[i]; 
            Vector2 targetPos = (i < positions.Count) ? positions[i] : Vector2.zero;

            // 寻找现存的立绘对象
            CharacterPortrait existingPortrait = null;
            foreach (var kvp in activeCharacters)
            {
                if (kvp.Value.CharacterID.ToLower() == cid) existingPortrait = kvp.Value;
            }

            if (existingPortrait != null)
            {
                // 已经在舞台上，平滑滑行到新分配的等分位置
                existingPortrait.SetPosition(targetPos, instant: false);
            }
            else
            {
                // 不在舞台上，生成并播放淡入动画
                if (playerData != null && cid == playerData.id.ToLower()) SpawnPlayer(targetPos);
                else SpawnCharacter(cid, targetPos);
            }
        }

        // 5. 舞台调度完成，开始逐句播放对话
        StartCoroutine(PlayDialogueSequence(sequence, onComplete));
    }

    public IEnumerator PlayDialogueSequence(List<DialogueTurn> sequence, System.Action onComplete)
    {
        foreach (var turn in sequence)
        {
            string spk = turn.speaker.ToLower();
            bool isPlayerTurn = IsPlayer(spk);

            if (spk == "system" || spk == "narrator" || spk == "gm")
            {
                speakerNameText.text = "";
            }
            else
            {
                // 只要是主角说话，名字强制显示为“我”
                speakerNameText.text = isPlayerTurn ? "我" : turn.speaker;

                // 寻找在场的立绘来切换表情
                string targetId = isPlayerTurn ? playerData.id.ToLower() : spk;
                CharacterPortrait targetPortrait = null;
                
                if (activeCharacters.ContainsKey(targetId)) targetPortrait = activeCharacters[targetId];
                else 
                {
                    var data = artLibrary.GetCharacter(targetId);
                    if (data != null && activeCharacters.ContainsKey(data.id.ToLower())) 
                    {
                        targetPortrait = activeCharacters[data.id.ToLower()];
                    }
                }

                if (targetPortrait != null) targetPortrait.ChangeExpression(turn.mood);
            }

            UpdatePortraitFocus(isPlayerTurn ? playerData.id.ToLower() : spk);

            bool finished = false;
            if (textAnimator != null) textAnimator.ShowText(turn.content, () => finished = true);
            else finished = true;

            GameManager.Instance.AddChatLog(isPlayerTurn ? "我" : turn.speaker, turn.content);

            while (!finished) yield return null;
            yield return new WaitForSeconds(1.0f);
        }

        onComplete?.Invoke();
    }

    public void ShowImmediateMessage(string speaker, string content, Color color)
    {
        bool isPlayer = IsPlayer(speaker);
        speakerNameText.text = isPlayer ? "我" : speaker;
        speakerNameText.color = color;
        if (textAnimator) textAnimator.ShowText(content);
        UpdatePortraitFocus(isPlayer ? playerData.id.ToLower() : speaker);
    }

    public void ShowOptions(List<string> options)
    {
        optionsContainer.SetActive(true);
        for (int i = 0; i < optionButtons.Length; i++)
        {
            if (i < options.Count)
            {
                optionButtons[i].gameObject.SetActive(true);
                var btnText = optionButtons[i].GetComponentInChildren<TMP_Text>();
                if (btnText) btnText.text = options[i];

                string selectedContent = options[i];
                optionButtons[i].onClick.RemoveAllListeners();
                optionButtons[i].onClick.AddListener(() =>
                {
                    optionsContainer.SetActive(false);
                    GameManager.Instance.HandlePlayerChoice(selectedContent);
                });
            }
            else
            {
                optionButtons[i].gameObject.SetActive(false);
            }
        }
    }

    private void UpdatePortraitFocus(string speakerName)
    {
        string canonicalId = IsPlayer(speakerName) ? playerData.id.ToLower() : speakerName.ToLower();
        
        if (!IsPlayer(speakerName)) 
        {
            var data = artLibrary.GetCharacter(speakerName);
            if (data != null) canonicalId = data.id.ToLower();
        }

        foreach (var kvp in activeCharacters)
        {
            if (kvp.Value.CharacterID.ToLower() == canonicalId) kvp.Value.SetFocus(true);
            else kvp.Value.SetFocus(false);
        }
    }
    
    // 专门播放固定剧本的重载方法
    public void PlayFixedDialogue(FixedDialogueData fixedData, System.Action onComplete = null)
    {
        if (fixedData != null && fixedData.sequence != null)
        {
            HandlePlayDialogueSequence(fixedData.sequence, onComplete);
        }
    }
}