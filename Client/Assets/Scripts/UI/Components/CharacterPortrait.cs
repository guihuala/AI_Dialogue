using UnityEngine;
using UnityEngine.UI;
using DG.Tweening;

[RequireComponent(typeof(CanvasGroup))]
public class CharacterPortrait : MonoBehaviour
{
    [Header("Components")]
    [SerializeField] private Image portraitImage;
    [SerializeField] private CanvasGroup canvasGroup;
    [SerializeField] private RectTransform rectTransform;

    [Header("Settings")]
    [SerializeField] private float moveDuration = 0.5f;
    [SerializeField] private float fadeDuration = 0.3f;
    [SerializeField] private Color dimColor = new Color(0.6f, 0.6f, 0.6f, 1f);
    
    public string CharacterID { get; private set; }

    // 初始化角色
    public void Initialize(string id, Sprite sprite)
    {
        CharacterID = id;
        portraitImage.sprite = sprite;
        portraitImage.SetNativeSize(); // 保持图片原始比例
        
        // 初始设为全透明
        canvasGroup.alpha = 0f;
    }

    // 设置位置（支持动画）
    public void SetPosition(Vector2 anchoredPosition, bool instant = false)
    {
        if (instant)
        {
            rectTransform.anchoredPosition = anchoredPosition;
        }
        else
        {
            rectTransform.DOAnchorPos(anchoredPosition, moveDuration).SetEase(Ease.OutCubic);
        }
    }

    // 入场
    public void Enter()
    {
        gameObject.SetActive(true);
        canvasGroup.DOFade(1f, fadeDuration);
        // 入场时可以加一点缩放弹跳效果
        transform.localScale = Vector3.one * 0.95f;
        transform.DOScale(1f, fadeDuration);
    }

    // 退场
    public void Exit()
    {
        canvasGroup.DOFade(0f, fadeDuration).OnComplete(() => 
        {
            Destroy(gameObject); // 或者回收到对象池
        });
    }

    // 高亮/聚焦（说话时）
    public void SetFocus(bool isFocused)
    {
        if (isFocused)
        {
            portraitImage.DOColor(Color.white, 0.3f);
            transform.DOScale(1.05f, 0.3f); // 稍微放大
            transform.SetAsLastSibling();   // 移到最上层，遮挡其他人
        }
        else
        {
            portraitImage.DOColor(dimColor, 0.3f);
            transform.DOScale(1.0f, 0.3f);
        }
    }
}