using UnityEngine;
using TMPro;
using UnityEngine.UI;

public class TopBarController : MonoBehaviour
{
    [Header("Stats")]
    [SerializeField] private TMP_Text moneyText;
    [SerializeField] private TMP_Text sanText;
    [SerializeField] private TMP_Text gpaText;

    [Header("Time & Event")]
    [SerializeField] private TMP_Text timeText;  // 显示 "大一 9月 第1周"
    [SerializeField] private TMP_Text eventText; // 显示 "当前事件：入学报到"

    [Header("Settings")]
    [SerializeField] private Button phoneButton;
    
    private void Start()
    {
        if (phoneButton) phoneButton.onClick.AddListener(() => {
            if (PhoneManager.Instance != null) PhoneManager.Instance.TogglePhone();
        });
        
        MsgCenter.RegisterMsg(MsgConst.STATS_REFRESHED, Refresh);
    }

    private void OnDestroy()
    {
        MsgCenter.UnregisterMsg(MsgConst.STATS_REFRESHED, Refresh);
    }

    // 更新所有状态
    public void Refresh(params object[] args)
    {
        PlayerStatsData stats = args[0] as PlayerStatsData;
        GameTimeData time = args[1] as GameTimeData;
        string eventName = (string)args[2];
        
        if (stats != null)
        {
            moneyText.text = $"$ {stats.money:F0}";
            moneyText.color = Color.black; 
            
            sanText.text = $"SAN: {stats.san}";
            sanText.color = stats.san < 40 ? Color.red : Color.black;

            gpaText.text = $"GPA: {stats.gpa:F2}";
            gpaText.color = stats.gpa < 2.0f ? Color.red : (stats.gpa > 3.5f ? new Color(0, 0.5f, 0) : Color.black);
        }

        if (time != null && !string.IsNullOrEmpty(time.year))
        {
            // Now time.year holds the chapter string like "第 1 章"
            timeText.text = $"{time.year} | 回合 {time.week}";
            timeText.color = Color.black;
        }

        if (!string.IsNullOrEmpty(eventName))
        {
            eventText.text = eventName;
            eventText.color = eventName.Contains("日常") ? Color.black : new Color(1f, 0.5f, 0f);
        }
    }
}