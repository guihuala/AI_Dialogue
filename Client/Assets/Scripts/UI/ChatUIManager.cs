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

    [Header("Status UI")]
    [SerializeField] private Text balanceText; // 余额
    [SerializeField] private Text sanityText;  // 心情
    [SerializeField] private Text gpaText;     // 绩点
    [SerializeField] private Text dateText;    // 日期时间

    private CharacterPresenter currentPresenter;
    private List<CharacterPresenter> instantiatedCharacters = new List<CharacterPresenter>();

    private void Awake()
    {
        MsgCenter.RegisterMsg(MsgConst.MSG_GAME_UPDATE_STATS, OnUpdateStats);
        MsgCenter.RegisterMsgAct(MsgConst.MSG_GAME_BUBBLE_CREATE, CreateAIBubble);
        MsgCenter.RegisterMsg(MsgConst.MSG_GAME_BUBBLE_UPDATE, OnUpdateBubble);
        MsgCenter.RegisterMsgAct(MsgConst.MSG_GAME_BUBBLE_DESTROY, DestroyCurrentStreamingBubble);
        MsgCenter.RegisterMsg(MsgConst.MSG_GAME_ADD_MESSAGE, OnAddMessage);
        MsgCenter.RegisterMsg(MsgConst.MSG_GAME_SHOW_OPTIONS, OnShowOptions);
        MsgCenter.RegisterMsgAct(MsgConst.MSG_GAME_CLEAR_OPTIONS, ClearOptions);
    }

    private void OnDestroy()
    {
        MsgCenter.UnregisterMsg(MsgConst.MSG_GAME_UPDATE_STATS, OnUpdateStats);
        MsgCenter.UnregisterMsgAct(MsgConst.MSG_GAME_BUBBLE_CREATE, CreateAIBubble);
        MsgCenter.UnregisterMsg(MsgConst.MSG_GAME_BUBBLE_UPDATE, OnUpdateBubble);
        MsgCenter.UnregisterMsgAct(MsgConst.MSG_GAME_BUBBLE_DESTROY, DestroyCurrentStreamingBubble);
        MsgCenter.UnregisterMsg(MsgConst.MSG_GAME_ADD_MESSAGE, OnAddMessage);
        MsgCenter.UnregisterMsg(MsgConst.MSG_GAME_SHOW_OPTIONS, OnShowOptions);
        MsgCenter.UnregisterMsgAct(MsgConst.MSG_GAME_CLEAR_OPTIONS, ClearOptions);
    }

    // --- Event Handlers ---

    private void OnUpdateStats(params object[] args)
    {
        if (args.Length >= 5)
        {
            UpdateStats((float)args[0], (float)args[1], (float)args[2], (int)args[3], (string)args[4]);
        }
    }

    private void OnUpdateBubble(params object[] args)
    {
        if (args.Length > 0 && args[0] is string text) UpdateCurrentAIBubble(text);
    }

    private void OnAddMessage(params object[] args)
    {
        if (args.Length >= 2 && args[0] is string name && args[1] is string content)
        {
            if (name == "系统" || name == "旁白" || name == "突发事件") AddSystemMessage(content);
            else AddStaticAIBubble(name, content);
        }
    }

    private void OnShowOptions(params object[] args)
    {
        if (args.Length > 0 && args[0] is List<StoryOption> options) ShowOptions(options);
    }

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
        if (name == "唐梦琪") return "tang_mengqi";
        if (name == "李一诺") return "li_yinuo";
        if (name == "赵鑫") return "zhao_xin";
        if (name == "林飒") return "lin_sa";
        if (name == "陈雨婷") return "chen_yuting";
        if (name == "苏浅") return "su_qian";
        return name; 
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
                // Decoupled Input
                MsgCenter.SendMsg(MsgConst.MSG_GAME_OPTION_CLICKED, opt);
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