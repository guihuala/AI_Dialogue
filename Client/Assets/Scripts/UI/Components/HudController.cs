using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class HudController : MonoBehaviour
{
    public Button pauseButton;

    [Header("Chat Components")]
    [SerializeField] private TMP_Text chatLogText;
    [SerializeField] private TMP_InputField inputField;
    [SerializeField] private Button sendButton;
    [SerializeField] private TMP_Dropdown characterDropdown;

    [Header("Stats Display")]
    [SerializeField] private TMP_Text moneyText;
    [SerializeField] private TMP_Text sanText;
    [SerializeField] private TMP_Text gpaText;

    // 事件：当用户点击发送时触发
    public System.Action<string, string> OnSendRequest; 

    private void Start()
    {
        pauseButton.onClick.AddListener(OnPauseButtonClicked);
        sendButton.onClick.AddListener(HandleSendClick);
    }

    public void InitializeRoommates(List<string> activeRoommates)
    {
        if (activeRoommates == null || activeRoommates.Count == 0) return;

        characterDropdown.ClearOptions();
        characterDropdown.AddOptions(activeRoommates);
        
        // 重置选中项为第一个
        characterDropdown.value = 0;
        characterDropdown.RefreshShownValue();
        
        Debug.Log($"HUD Dropdown updated with: {string.Join(", ", activeRoommates)}");
    }

    private void HandleSendClick()
    {
        if (string.IsNullOrEmpty(inputField.text)) return;

        string content = inputField.text;
        string targetId = characterDropdown.options[characterDropdown.value].text.ToLower();
        
        // 通知控制器去处理逻辑
        OnSendRequest?.Invoke(content, targetId);

        // 清空输入框，显示“思考中”
        inputField.text = "";
        AppendMessage("System", $"Speaking to {targetId}...", Color.gray);
    }

    // 更新对话框
    public void AppendMessage(string speaker, string content, Color color)
    {
        string hexColor = ColorUtility.ToHtmlStringRGB(color);
        // 简单的追加模式，你也可以改成生成 Prefab
        chatLogText.text = $"<color=#{hexColor}><b>[{speaker}]</b></color>: {content}";
    }

    // 更新玩家属性面板
    public void UpdatePlayerStats(PlayerStatsData stats)
    {
        if (stats == null) return;

        moneyText.text = $"$ {stats.money:F0}";
        
        sanText.text = $"SAN: {stats.san}";
        // SAN 值低变红
        sanText.color = stats.san < 40 ? Color.red : Color.white; 

        gpaText.text = $"GPA: {stats.gpa:F2}";
        // GPA 高变绿
        gpaText.color = stats.gpa > 3.8f ? Color.green : Color.white;
    }

    public void ShowError(string error)
    {
        AppendMessage("Error", error, Color.red);
    }
    
    private void OnPauseButtonClicked()
    {
        GameManager.Instance.PauseGame();
    }
}