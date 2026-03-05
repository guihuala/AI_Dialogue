using UnityEngine;
using UnityEngine.UI;

public class AlipayApp : MonoBehaviour
{
    public Text balanceText;
    public Transform historyContent;
    public GameObject historyRowPrefab;

    private void OnEnable()
    {
        // 从 GameManager 获取当前余额 (假设你已经把 currentMoney 暴露出去了)
        balanceText.text = $"¥ {GameManager.Instance.CurrentMoney:F2}";

        // 清理旧列表
        foreach (Transform child in historyContent) Destroy(child.gameObject);

        // 倒序渲染账单（最新的在最上面）
        var trans = PhoneManager.Instance.Transactions;
        for (int i = trans.Count - 1; i >= 0; i--)
        {
            var record = trans[i];
            GameObject row = Instantiate(historyRowPrefab, historyContent);
            Text[] texts = row.GetComponentsInChildren<Text>();
            
            if (texts.Length >= 2)
            {
                texts[0].text = $"[{record.chapterInfo}] {record.description}";
                // 正数显示绿色，负数显示红色
                texts[1].text = record.amount > 0 ? $"+{record.amount:F2}" : $"{record.amount:F2}";
                texts[1].color = record.amount > 0 ? new Color(0, 0.6f, 0) : Color.red;
            }
        }
    }
}