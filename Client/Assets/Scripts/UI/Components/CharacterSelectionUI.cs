using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class CharacterSelectionUI : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private GameObject characterItemPrefab; // 预制体：包含头像Image, 名字Text, Toggle组件
    [SerializeField] private Transform gridContainer;        // Grid Layout Group
    [SerializeField] private Button startGameButton;
    [SerializeField] private TMP_Text warningText;

    [Header("Data")]
    [SerializeField] private List<CharacterData> allCharacters; // 拖入那6个ScriptableObject

    private List<string> selectedIds = new List<string>();
    private const int MAX_SELECTION = 3;

    void Start()
    {
        GenerateGrid();
        startGameButton.onClick.AddListener(OnStartGameClicked);
        UpdateUIState();
    }

    void GenerateGrid()
    {
        // 清空容器
        foreach (Transform child in gridContainer) Destroy(child.gameObject);

        foreach (var data in allCharacters)
        {
            GameObject item = Instantiate(characterItemPrefab, gridContainer);
            
            item.transform.Find("Name").GetComponent<TMP_Text>().text = data.displayName;
            item.transform.Find("Portrait").GetComponent<Image>().sprite = data.portrait;

            // 监听 Toggle
            Toggle toggle = item.GetComponentInChildren<Toggle>();
            toggle.onValueChanged.AddListener((isOn) => 
            {
                OnCharacterToggled(data.id, isOn);
            });
        }
    }

    void OnCharacterToggled(string charId, bool isOn)
    {
        if (isOn)
        {
            if (selectedIds.Count >= MAX_SELECTION)
            {
                // 如果已经选了3个，强制取消当前的勾选（或者禁用其他的）
                // 这里简单处理：不允许选第4个，或者顶掉第一个，看你逻辑
                // 这里我们做简单限制：
                // 实际项目中建议把 Toggle Group 关掉，用代码控制
            }
            if (!selectedIds.Contains(charId)) selectedIds.Add(charId);
        }
        else
        {
            if (selectedIds.Contains(charId)) selectedIds.Remove(charId);
        }
        
        UpdateUIState();
    }

    void UpdateUIState()
    {
        int count = selectedIds.Count;
        startGameButton.interactable = (count == MAX_SELECTION);
        warningText.text = $"已选择: {count} / {MAX_SELECTION}";
    }

    void OnStartGameClicked()
    {
        // 把选好的名单传给 GameManager
        GameManager.Instance.StartNewGame(selectedIds);
        
        // 隐藏自己，显示游戏主界面
        this.gameObject.SetActive(false);
    }
}