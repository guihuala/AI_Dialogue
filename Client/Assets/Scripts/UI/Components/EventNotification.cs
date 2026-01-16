using UnityEngine;
using TMPro;
using DG.Tweening;
using UnityEngine.UI;

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
}