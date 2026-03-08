using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class CharacterSelectionPanel : BasePanel
{
    [Header("UI References")]
    [SerializeField] private GameObject characterItemPrefab;
    [SerializeField] private Transform gridContainer;
    [SerializeField] private Button startGameButton;
    // [新增] 随机选择按钮的引用
    [SerializeField] private Button randomSelectButton; 
    [SerializeField] private TMP_Text warningText;

    [Header("Data")]
    [SerializeField] private List<CharacterData> allCharacters;

    private List<string> selectedIds = new List<string>();
    private const int MAX_SELECTION = 3;
    private Dictionary<string, Toggle> characterToggles = new Dictionary<string, Toggle>();

    public override void OpenPanel(string name)
    {
        base.OpenPanel(name);
        selectedIds.Clear();
        GenerateGrid();
        
        startGameButton.onClick.RemoveAllListeners();
        startGameButton.onClick.AddListener(OnStartGameClicked);

        // [新增] 绑定随机选择按钮的事件
        if (randomSelectButton != null)
        {
            randomSelectButton.onClick.RemoveAllListeners();
            randomSelectButton.onClick.AddListener(OnRandomSelectClicked);
        }

        UpdateUIState();
    }

    void GenerateGrid()
    {
        foreach (Transform child in gridContainer) Destroy(child.gameObject);
        characterToggles.Clear();

        foreach (var data in allCharacters)
        {
            GameObject item = Instantiate(characterItemPrefab, gridContainer);
            item.transform.Find("Name").GetComponent<TMP_Text>().text = data.displayName;
            item.transform.Find("Portrait").GetComponent<Image>().sprite = data.defaultPortrait;

            Toggle toggle = item.GetComponentInChildren<Toggle>();
            toggle.isOn = false;
            characterToggles.Add(data.id, toggle);

            toggle.onValueChanged.AddListener((isOn) => 
            {
                OnCharacterToggled(data.id, isOn, toggle);
            });
        }
    }

    void OnCharacterToggled(string charId, bool isOn, Toggle toggle)
    {
        if (isOn)
        {
            if (selectedIds.Count >= MAX_SELECTION)
            {
                // Revert toggle if max limit reached
                toggle.isOn = false; 
                return;
            }
            if (!selectedIds.Contains(charId)) selectedIds.Add(charId);
        }
        else
        {
            if (selectedIds.Contains(charId)) selectedIds.Remove(charId);
        }
        
        UpdateUIState();
    }

    // 随机选择的核心逻辑
    void OnRandomSelectClicked()
    {
        // 如果总角色数小于需要选择的数量，则直接返回防报错
        if (allCharacters.Count < MAX_SELECTION) return;

        // 1. 清空当前所有选中状态 (使用 WithoutNotify 防止触发 OnCharacterToggled 导致逻辑混乱)
        foreach (var toggle in characterToggles.Values)
        {
            toggle.SetIsOnWithoutNotify(false);
        }
        selectedIds.Clear();

        // 2. 创建一个备选池以防重复抽取
        List<CharacterData> pool = new List<CharacterData>(allCharacters);

        // 3. 随机抽取 MAX_SELECTION 名角色
        for (int i = 0; i < MAX_SELECTION; i++)
        {
            int randomIndex = Random.Range(0, pool.Count);
            CharacterData selectedChar = pool[randomIndex];
            
            // 将选中的角色添加至列表并更新 Toggle UI
            selectedIds.Add(selectedChar.id);
            if (characterToggles.TryGetValue(selectedChar.id, out Toggle toggle))
            {
                toggle.SetIsOnWithoutNotify(true);
            }

            // 从备选池中移除已选角色，确保不重复
            pool.RemoveAt(randomIndex);
        }

        // 4. 更新底部的开始按钮和计数文本状态
        UpdateUIState();
    }

    void UpdateUIState()
    {
        int count = selectedIds.Count;
        startGameButton.interactable = (count == MAX_SELECTION);
        warningText.text = $"已选择: {count} / {MAX_SELECTION}";
    }

    private void OnStartGameClicked()
    {
        // 防御检查：必须选满才能开局
        if (selectedIds.Count < MAX_SELECTION) return;
        
        // 🌟 1. 存入跨场景中转站
        GameContext.SelectedRoommates = new List<string>(selectedIds);
        
        // 🌟 2. 标记为新游戏
        PlayerPrefs.SetInt("IsContinuingGame", 0);
        PlayerPrefs.Save();
        
        startGameButton.interactable = false;
    }
}