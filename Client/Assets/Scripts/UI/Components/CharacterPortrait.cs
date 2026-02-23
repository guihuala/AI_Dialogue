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
    
    [Header("Portrait Size")]
    [SerializeField] private Vector2 portraitSize = new Vector2(300, 400); // 添加默认尺寸
    [SerializeField] private bool preserveAspect = true; // 保持宽高比
    
    public string CharacterID { get; private set; }
    
    private CharacterData characterData; // 缓存角色数据
    
    public void Initialize(CharacterData data)
    {
        characterData = data;
        CharacterID = data.id;
    
        // 初始使用默认立绘
        portraitImage.sprite = data.defaultPortrait;
    
        SetPortraitSize();
        canvasGroup.alpha = 0f;
    }
    
    public void ChangeExpression(string mood)
    {
        if (characterData == null) return;
    
        Sprite newSprite = characterData.GetSpriteByMood(mood);
        if (newSprite != null && portraitImage.sprite != newSprite)
        {
            portraitImage.sprite = newSprite;
            transform.DOPunchScale(new Vector3(0.02f, 0.02f, 0), 0.2f, 1);
        }
    }
    
    // 设置立绘尺寸
    private void SetPortraitSize()
    {
        if (preserveAspect)
        {
            // 保持宽高比设置尺寸
            float spriteAspect = portraitImage.sprite.rect.width / portraitImage.sprite.rect.height;
            float targetAspect = portraitSize.x / portraitSize.y;
            
            if (spriteAspect > targetAspect)
            {
                // 图片更宽，以宽度为基准
                float width = portraitSize.x;
                float height = width / spriteAspect;
                rectTransform.sizeDelta = new Vector2(width, height);
            }
            else
            {
                // 图片更高，以高度为基准
                float height = portraitSize.y;
                float width = height * spriteAspect;
                rectTransform.sizeDelta = new Vector2(width, height);
            }
        }
        else
        {
            // 直接拉伸到目标尺寸
            rectTransform.sizeDelta = portraitSize;
        }
    }

    // 可以添加一个方法动态调整尺寸
    public void SetPortraitSize(Vector2 newSize, bool preserveAspect = true)
    {
        this.portraitSize = newSize;
        this.preserveAspect = preserveAspect;
        SetPortraitSize();
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