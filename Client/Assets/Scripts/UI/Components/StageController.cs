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
    
    private readonly Vector2 POS_PLAYER = new Vector2(-550, -100); // 主角位置(偏左下)
    private readonly Vector2 POS_RIGHT_1 = new Vector2(100, 0);    // 仅1个室友时
    private readonly Vector2 POS_RIGHT_2_L = new Vector2(-100, 0); // 2个室友-左
    private readonly Vector2 POS_RIGHT_2_R = new Vector2(350, 0);  // 2个室友-右
    private readonly Vector2 POS_RIGHT_3_L = new Vector2(-200, 0); // 3个室友-左
    private readonly Vector2 POS_RIGHT_3_C = new Vector2(100, 0);  // 3个室友-中
    private readonly Vector2 POS_RIGHT_3_R = new Vector2(400, 0);  // 3个室友-右

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
        // 1. 清理
        foreach (var kvp in activeCharacters)
        {
            if (kvp.Value != null) Destroy(kvp.Value.gameObject);
        }
        activeCharacters.Clear();

        // 2. 【新增】生成主角立绘
        if (playerData != null)
        {
            GameObject playerObj = Instantiate(characterPrefab, stageContainer);
            CharacterPortrait pPortrait = playerObj.GetComponent<CharacterPortrait>();
            pPortrait.Initialize(playerData);
            pPortrait.SetPosition(POS_PLAYER, instant: true);
            pPortrait.Enter();
            
            // 为了兼容 LLM 可能返回的不同主角称呼，多注册几个Key
            activeCharacters["player"] = pPortrait;
            activeCharacters["陆陈安然"] = pPortrait;
            activeCharacters["安然"] = pPortrait;
            activeCharacters["我"] = pPortrait;
        }

        if (roommateIds == null || roommateIds.Count == 0) return;

        // 3. 生成室友
        List<Vector2> positions = GetStandPositions(roommateIds.Count);
        for (int i = 0; i < roommateIds.Count; i++)
        {
            string cid = roommateIds[i];
            Vector2 targetPos = (i < positions.Count) ? positions[i] : Vector2.zero;
            SpawnCharacter(cid, targetPos);
        }
    }

    private void SpawnCharacter(string id, Vector2 targetPos)
    {
        var data = artLibrary.GetCharacter(id);
        if (data == null) return;

        GameObject go = Instantiate(characterPrefab, stageContainer);
        CharacterPortrait portrait = go.GetComponent<CharacterPortrait>();

        portrait.Initialize(data);
        portrait.SetPosition(targetPos, instant: true);
        portrait.Enter();

        activeCharacters[id.ToLower()] = portrait;
    }

    // 【修改】根据室友数量返回靠右侧的站位
    private List<Vector2> GetStandPositions(int count)
    {
        List<Vector2> pos = new List<Vector2>();
        if (count == 1) pos.Add(POS_RIGHT_1);
        else if (count == 2)
        {
            pos.Add(POS_RIGHT_2_L);
            pos.Add(POS_RIGHT_2_R);
        }
        else
        {
            pos.Add(POS_RIGHT_3_L);
            pos.Add(POS_RIGHT_3_C);
            pos.Add(POS_RIGHT_3_R);
        }
        return pos;
    }

    private void HandlePlayDialogueSequence(List<DialogueTurn> sequence, System.Action onComplete)
    {
        StartCoroutine(PlayDialogueSequence(sequence, onComplete));
    }

    public IEnumerator PlayDialogueSequence(List<DialogueTurn> sequence, System.Action onComplete)
    {
        foreach (var turn in sequence)
        {
            string speakerKey = turn.speaker.ToLower();

            if (turn.speaker == "System" || turn.speaker == "Narrator" || turn.speaker == "GM")
            {
                speakerNameText.text = "";
            }
            else
            {
                // 如果是主角，可以选择把名字显示为“我”或者“陆陈安然”
                speakerNameText.text = (speakerKey == "player" || speakerKey == "我") ? "陆陈安然" : turn.speaker;

                if (activeCharacters.ContainsKey(speakerKey))
                {
                    activeCharacters[speakerKey].ChangeExpression(turn.mood);
                }
            }

            UpdatePortraitFocus(speakerKey);

            bool finished = false;
            if (textAnimator != null)
                textAnimator.ShowText(turn.content, () => finished = true);
            else
                finished = true;

            GameManager.Instance.AddChatLog(turn.speaker, turn.content);

            while (!finished) yield return null;
            yield return new WaitForSeconds(1.0f);
        }

        onComplete?.Invoke();
    }

    public void ShowImmediateMessage(string speaker, string content, Color color)
    {
        speakerNameText.text = speaker;
        speakerNameText.color = color;
        if (textAnimator) textAnimator.ShowText(content);
        UpdatePortraitFocus(speaker);
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
                if(btnText) btnText.text = options[i];
                
                string selectedContent = options[i];
                optionButtons[i].onClick.RemoveAllListeners();
                optionButtons[i].onClick.AddListener(() => {
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

    private void UpdatePortraitFocus(string speakerKey)
    {
        speakerKey = speakerKey.ToLower();
        foreach (var kvp in activeCharacters)
        {
            // 匹配到当前说话人时高亮，其余变暗
            if (kvp.Key == speakerKey) kvp.Value.SetFocus(true);
            else kvp.Value.SetFocus(false);
        }
    }
}