using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class StageController : MonoBehaviour
{
    [Header("Data")] [SerializeField] private CharacterArtLibrary artLibrary;

    [Header("Stage Settings")] [SerializeField]
    private RectTransform stageContainer; // 角色立绘父节点

    [SerializeField] private GameObject characterPrefab; // CharacterPortrait Prefab

    [Header("Dialogue UI")] [SerializeField]
    private TMP_Text speakerNameText;

    [SerializeField] private TextAnimator textAnimator;
    [SerializeField] private GameObject dialoguePanel;

    [Header("Options UI")] [SerializeField]
    private GameObject optionsContainer;

    [SerializeField] private Button[] optionButtons;

    [Header("Buttons")] [SerializeField] private Button historyButton;

    // 运行时数据
    private Dictionary<string, CharacterPortrait> activeCharacters = new Dictionary<string, CharacterPortrait>();

    // 事件
    public System.Action<string> OnOptionSelected;

    private readonly Vector2 POS_LEFT = new Vector2(-400, 0);
    private readonly Vector2 POS_CENTER = new Vector2(0, 0);
    private readonly Vector2 POS_RIGHT = new Vector2(400, 0);

    private void Start()
    {
        if (historyButton) historyButton.onClick.AddListener(() => UIManager.Instance.OpenPanel("HistoryPanel"));
        if (optionsContainer) optionsContainer.SetActive(false);

        // 订阅 GameManager 事件
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

    private void HandlePlayDialogueSequence(List<DialogueTurn> sequence, System.Action onComplete)
    {
        StartCoroutine(PlayDialogueSequence(sequence, onComplete));
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
                    // 修改：直接调用单例的方法，不再抛出委托
                    GameManager.Instance.HandlePlayerChoice(selectedContent);
                });
            }
            else
            {
                optionButtons[i].gameObject.SetActive(false);
            }
        }
    }

    // --- 角色立绘管理 ---
    public void InitializeRoommates(List<string> activeRoommates)
    {
        foreach (var charCtrl in activeCharacters.Values)
        {
            if (charCtrl != null) Destroy(charCtrl.gameObject);
        }

        activeCharacters.Clear();

        if (activeRoommates != null && activeRoommates.Count > 0)
        {
            List<Vector2> positions = GetStandPositions(activeRoommates.Count);
            for (int i = 0; i < activeRoommates.Count; i++)
            {
                SpawnCharacter(activeRoommates[i], positions[i]);
            }
        }
    }

    private void SpawnCharacter(string id, Vector2 targetPos)
    {
        var data = artLibrary.GetCharacter(id);
        if (data == null) return;

        GameObject go = Instantiate(characterPrefab, stageContainer);
        CharacterPortrait portrait = go.GetComponent<CharacterPortrait>();

        portrait.Initialize(id, data.portrait);
        portrait.SetPosition(targetPos, instant: true);
        portrait.Enter();

        activeCharacters[id.ToLower()] = portrait;
    }

    private List<Vector2> GetStandPositions(int count)
    {
        List<Vector2> pos = new List<Vector2>();
        if (count == 1) pos.Add(POS_CENTER);
        else if (count == 2)
        {
            pos.Add(new Vector2(-300, 0));
            pos.Add(new Vector2(300, 0));
        }
        else
        {
            pos.Add(POS_LEFT);
            pos.Add(POS_CENTER);
            pos.Add(POS_RIGHT);
        }

        return pos;
    }

    // --- 对话播放 ---
    public IEnumerator PlayDialogueSequence(List<DialogueTurn> sequence, System.Action onComplete)
    {
        foreach (var turn in sequence)
        {
            if (turn.speaker == "System" || turn.speaker == "Narrator" || turn.speaker == "GM")
            {
                speakerNameText.text = "";
            }
            else
            {
                speakerNameText.text = turn.speaker;
            }

            UpdatePortraitFocus(turn.speaker);

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

    // 显示单条消息 (例如玩家的选择，或系统错误)
    public void ShowImmediateMessage(string speaker, string content, Color color)
    {
        speakerNameText.text = speaker;
        speakerNameText.color = color;
        if (textAnimator) textAnimator.ShowText(content);
        UpdatePortraitFocus(speaker);
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