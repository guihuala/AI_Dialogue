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
    [SerializeField] private Button settingsButton;
    [SerializeField] private Button helpButton;

    private void Start()
    {
        // 可以在这里绑定设置按钮的事件
        if(settingsButton) settingsButton.onClick.AddListener(() => { /* Open Settings */ });
    }

    // 更新所有状态
    public void Refresh(PlayerStatsData stats, GameTimeData time, string eventName)
    {
        if (stats != null)
        {
            moneyText.text = $"$ {stats.money:F0}";
            moneyText.color = Color.black; 
            
            sanText.text = $"SAN: {stats.san}";
            sanText.color = stats.san < 40 ? Color.red : Color.black;

            gpaText.text = $"GPA: {stats.gpa:F2}";
            gpaText.color = stats.gpa < 2.0f ? Color.red : (stats.gpa > 3.5f ? new Color(0, 0.5f, 0) : Color.black);
        }

        if (time != null)
        {
            timeText.text = $"第{time.year}年 | {time.month}月 | 第{time.week}周";
            timeText.color = Color.black;
        }

        if (!string.IsNullOrEmpty(eventName))
        {
            eventText.text = eventName;
            eventText.color = eventName.Contains("日常") ? Color.black : new Color(1f, 0.5f, 0f);
        }
    }
}