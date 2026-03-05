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
            MsgCenter.RegisterMsg(MsgConst.EVENT_NOTIFIED, ShowEvent);
            MsgCenter.RegisterMsg(MsgConst.WECHAT_NOTIFIED, ShowWechat);
        }
    }

    private void OnDestroy()
    {
        if (GameManager.Instance != null)
        {
            MsgCenter.UnregisterMsg(MsgConst.EVENT_NOTIFIED, ShowEvent);
            MsgCenter.UnregisterMsg(MsgConst.WECHAT_NOTIFIED, ShowWechat);
        }
    }

    private void ShowEvent(params object[] args)
    {
        string eventName = (string)args[0];
        
        if (string.IsNullOrEmpty(eventName) || eventName.Contains("日常")) return;

        eventText.text = eventName;
        
        Sequence s = DOTween.Sequence();
        s.Append(canvasGroup.DOFade(1, 0.5f));
        s.Append(transform.DOScale(1.1f, 0.5f).From(1.0f));
        s.AppendInterval(2.0f);
        s.Append(canvasGroup.DOFade(0, 0.5f));
    }

    private void ShowWechat(params object[] args)
    {
        List<WeChatNotification> notifications = args[0] as List<WeChatNotification>;
        
        if (notifications == null || notifications.Count == 0) return;
        
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