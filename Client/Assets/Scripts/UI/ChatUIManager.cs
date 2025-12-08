using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class ChatUIManager : MonoBehaviour
{
    [Header("Visual Novel UI")]
    [SerializeField] private CharacterArtManager artManager;
    [SerializeField] private GameObject vnDialogueBox; // The fixed panel at bottom
    [SerializeField] private Text vnNameText;
    [SerializeField] private Text vnContentText;

    [Header("Options UI")]
    [SerializeField] private Transform optionContainer;
    [SerializeField] private GameObject optionButtonPrefab;

    [Header("Character Prefabs UI")]
    [SerializeField] private Transform characterRoot; // Parent for character prefabs
    [SerializeField] private List<CharacterPresenter> characterPrefabs; // Assign prefabs here
    [SerializeField] private CharacterPresenter playerPrefab; // Special prefab for player
    [SerializeField] private CharacterPresenter systemPrefab; // Special prefab for system

    private CharacterPresenter currentPresenter;
    private List<CharacterPresenter> instantiatedCharacters = new List<CharacterPresenter>();

    [Header("Status UI")]
    [SerializeField] private Text balanceText; // 余额
    [SerializeField] private Text sanityText;  // 心情
    [SerializeField] private Text gpaText;     // 绩点
    [SerializeField] private Text dateText;    // 日期时间

    public Action<StoryOption> OnOptionClicked;

    private void Start()
    {
        if (ObjectPool.Instance == null)
        {
            GameObject poolObj = new GameObject("ObjectPool");
            poolObj.AddComponent<ObjectPool>();
        }
        
        // Instantiate all prefabs hidden at start
        foreach (var prefab in characterPrefabs)
        {
            var instance = Instantiate(prefab, characterRoot);
            instance.Hide();
            instantiatedCharacters.Add(instance);
        }
        
        if (playerPrefab != null)
        {
            var instance = Instantiate(playerPrefab, characterRoot);
            instance.Hide();
            instantiatedCharacters.Add(instance);
            // Re-assign to use the instance
            playerPrefab = instance; 
        }

        if (systemPrefab != null)
        {
            var instance = Instantiate(systemPrefab, characterRoot);
            instance.Hide();
            instantiatedCharacters.Add(instance);
            systemPrefab = instance;
        }
    }

    // --- 状态更新 ---
    public void UpdateStats(float money, float sanity, float gpa, int day, string timePeriod)
    {
        // 1. 金钱
        if (balanceText != null) 
        {
            balanceText.text = $"余额: ￥{money:F0}";
            balanceText.color = money < 200 ? Color.red : Color.black;
        }

        // 2. 心情
        if (sanityText != null) 
        {
            sanityText.text = $"心情: {sanity:F0}";
            sanityText.color = sanity < 30 ? Color.red : Color.black;
        }

        // 3. GPA
        if (gpaText != null) 
        {
            gpaText.text = $"GPA: {gpa:F2}";
            gpaText.color = gpa < 1.8f ? Color.red : Color.black;
        }

        // 4. 日期
        if (dateText != null)
        {
            dateText.text = $"第 {day} 天  {timePeriod}";
            dateText.color = day >= 7 ? Color.red : Color.black;
        }
    }

    // --- 对话显示 (Character Prefabs) ---

    public void CreateAIBubble()
    {
        // For streaming start, we assume the current presenter is already set by AddStaticAIBubble 
        // OR we need to know who is speaking. 
        // But streaming usually comes after a "Thinking..." or is the start of a turn.
        // If we don't know who, we might use a default or the last one.
        if (currentPresenter != null)
        {
            currentPresenter.Show("...");
        }
    }

    public void UpdateCurrentAIBubble(string text)
    {
        if (currentPresenter != null)
        {
            currentPresenter.UpdateText(text);
        }
    }

    public void DestroyCurrentStreamingBubble()
    {
        // Do nothing
    }

    public void AddStaticAIBubble(string name, string content)
    {
        HideAllCharacters();

        // Find character by ID (using name mapping for now)
        string id = GetIdByName(name);
        var presenter = instantiatedCharacters.Find(x => x.characterId == id);
        
        if (presenter != null)
        {
            currentPresenter = presenter;
            currentPresenter.Show(content, name);
        }
        else
        {
            // Fallback: Use system or log error
            Debug.LogWarning($"No prefab found for character: {name} (ID: {id})");
            if (systemPrefab != null)
            {
                currentPresenter = systemPrefab;
                currentPresenter.Show($"{name}: {content}", "System");
            }
        }
    }

    public void AddPlayerMessage(string text)
    {
        HideAllCharacters();
        if (playerPrefab != null)
        {
            currentPresenter = playerPrefab;
            currentPresenter.Show(text, "我");
        }
    }

    public void AddSystemMessage(string text)
    {
        HideAllCharacters();
        if (systemPrefab != null)
        {
            currentPresenter = systemPrefab;
            currentPresenter.Show(text, "系统");
        }
    }

    private void HideAllCharacters()
    {
        foreach (var c in instantiatedCharacters) c.Hide();
        if (playerPrefab != null) playerPrefab.Hide();
        if (systemPrefab != null) systemPrefab.Hide();
    }

    private string GetIdByName(string name)
    {
        // Simple mapping helper
        if (name == "唐梦琪") return "tang_mengqi";
        if (name == "李一诺") return "li_yinuo";
        if (name == "赵鑫") return "zhao_xin";
        if (name == "林飒") return "lin_sa";
        if (name == "陈雨婷") return "chen_yuting";
        if (name == "苏浅") return "su_qian";
        return name; // Fallback
    }

    // --- 选项显示 ---

    public void ShowOptions(List<StoryOption> options)
    {
        ClearOptions();
        if (options == null || options.Count == 0) return;

        foreach (var opt in options)
        {
            GameObject btnObj = ObjectPool.Instance.Spawn(optionButtonPrefab, optionContainer);
            btnObj.GetComponentInChildren<Text>().text = opt.text;
            Button btn = btnObj.GetComponent<Button>();
            btn.onClick.RemoveAllListeners(); 
            btn.onClick.AddListener(() => {
                OnOptionClicked?.Invoke(opt);
                ClearOptions(); 
            });
        }
    }

    public void ClearOptions()
    {
        List<GameObject> children = new List<GameObject>();
        foreach (Transform child in optionContainer) children.Add(child.gameObject);
        foreach (var child in children) ObjectPool.Instance.Despawn(child, optionButtonPrefab);
    }
}