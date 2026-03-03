using UnityEngine;
using TMPro;
using DG.Tweening;
using UnityEngine.UI;

using System.Collections.Generic;

public class EventNotification : MonoBehaviour
{
    [SerializeField] private CanvasGroup canvasGroup;
    [SerializeField] private TMP_Text eventText;
    [SerializeField] private Image bgImage;

    private void Awake()
    {
        canvasGroup.alpha = 0;
        canvasGroup.blocksRaycasts = false;
    }
    
    private void Start()
    {
        if (GameManager.Instance != null)
        {
            GameManager.Instance.OnEventNotified += ShowEvent;
            GameManager.Instance.OnWeChatNotified += ShowWechat;
        }
    }

    private void OnDestroy()
    {
        if (GameManager.Instance != null)
        {
            GameManager.Instance.OnEventNotified -= ShowEvent;
            GameManager.Instance.OnWeChatNotified -= ShowWechat;
        }
    }

    public void ShowEvent(string eventName)
    {
        if (string.IsNullOrEmpty(eventName) || eventName.Contains("日常")) return;

        eventText.text = eventName;
        
        Sequence s = DOTween.Sequence();
        s.Append(canvasGroup.DOFade(1, 0.5f));
        s.Append(transform.DOScale(1.1f, 0.5f).From(1.0f));
        s.AppendInterval(2.0f);
        s.Append(canvasGroup.DOFade(0, 0.5f));
    }

    public void ShowWechat(List<WeChatNotification> notifications)
    {
        if (notifications == null || notifications.Count == 0) return;

        // Just show the first/latest one for simplicity in this notification bubble
        var notif = notifications[0];
        eventText.text = $"📱 微信消息\n[{notif.chat_name}] {notif.sender}: {notif.message}";
        eventText.color = new Color(0.2f, 0.8f, 0.2f); // 微信绿

        Sequence s = DOTween.Sequence();
        s.Append(canvasGroup.DOFade(1, 0.5f));
        s.Append(transform.DOScale(1.05f, 0.2f).From(1.0f));
        s.AppendInterval(3.5f);
        s.Append(canvasGroup.DOFade(0, 0.5f));
        s.OnComplete(() => eventText.color = Color.white); // reset
    }
}