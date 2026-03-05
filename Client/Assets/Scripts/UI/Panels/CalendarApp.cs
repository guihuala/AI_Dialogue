using UnityEngine;
using UnityEngine.UI;

public class CalendarApp : MonoBehaviour
{
    public Text dateText;     // 显示例如 "大二 上学期"
    public Text progressText; // 显示例如 "第 10 周"

    private void OnEnable()
    {
        // 假设 GameManager 暴露出去了 CurrentChapter 和 CurrentTurn
        dateText.text = $"当前章节：第 {GameManager.Instance.CurrentChapter} 章";
        progressText.text = $"当前进度：第 {GameManager.Instance.CurrentTurn} 回合";
    }
}