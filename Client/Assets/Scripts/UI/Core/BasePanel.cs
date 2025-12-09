using DG.Tweening;
using UnityEngine;

/// <summary>
/// UI面板的基类
/// </summary>
[RequireComponent(typeof(CanvasGroup))]
public class BasePanel : MonoBehaviour
{
    protected bool hasRemoved = false; // 标记面板是否已被移除
    protected string panelName; // 面板名称
    protected CanvasGroup canvasGroup; // 用于管理透明度和交互
    
    [Header("动画设置")]
    [SerializeField] protected float fadeInDuration = 0.5f; // 淡入持续时间
    [SerializeField] protected float fadeOutDuration = 0.5f; // 淡出持续时间
    [SerializeField] protected Ease fadeInEase = Ease.OutQuad; // 淡入缓动类型
    [SerializeField] protected Ease fadeOutEase = Ease.InQuad; // 淡出缓动类型
    [SerializeField] protected bool scaleAnimation = true; // 是否启用缩放动画
    [SerializeField] protected Vector2 scaleFrom = new Vector2(0.8f, 0.8f); // 初始缩放值
    [SerializeField] protected float scaleDuration = 0.3f; // 缩放动画持续时间

    protected virtual void Awake()
    {
        // 获取 CanvasGroup 组件
        canvasGroup = GetComponent<CanvasGroup>();
    }

    /// <summary>
    /// 打开面板
    /// </summary>
    /// <param name="name">面板名称</param>
    public virtual void OpenPanel(string name)
    {
        panelName = name;

        // 激活面板
        gameObject.SetActive(true);

        // 初始化面板的透明度为 0
        canvasGroup.alpha = 0;
        
        // 如果启用缩放动画，设置初始缩放值
        if (scaleAnimation)
        {
            transform.localScale = scaleFrom;
        }

        // 使用 DOTween 播放渐显动画（不受时间缩放影响）
        Sequence s = DOTween.Sequence();
        s.SetUpdate(UpdateType.Normal, true); // 设置为不受时间缩放影响
        
        // 添加淡入动画
        s.Append(canvasGroup.DOFade(1, fadeInDuration)
            .SetEase(fadeInEase)
            .SetUpdate(UpdateType.Normal, true));
            
        // 如果启用缩放动画，添加缩放动画
        if (scaleAnimation)
        {
            s.Join(transform.DOScale(Vector3.one, scaleDuration)
                .SetEase(fadeInEase)
                .SetUpdate(UpdateType.Normal, true));
        }
    }

    /// <summary>
    /// 关闭面板
    /// </summary>
    public virtual void ClosePanel()
    {
        hasRemoved = true;

        // 使用 DOTween 播放渐隐动画，并在动画完成后销毁对象（不受时间缩放影响）
        Sequence s = DOTween.Sequence();
        s.SetUpdate(UpdateType.Normal, true); // 设置为不受时间缩放影响
        
        // 添加淡出动画
        s.Append(canvasGroup.DOFade(0, fadeOutDuration)
            .SetEase(fadeOutEase)
            .SetUpdate(UpdateType.Normal, true));
            
        // 如果启用缩放动画，添加缩放动画
        if (scaleAnimation)
        {
            s.Join(transform.DOScale(scaleFrom, Mathf.Min(fadeOutDuration, scaleDuration))
                .SetEase(fadeOutEase)
                .SetUpdate(UpdateType.Normal, true));
        }
        
        // 动画完成后销毁对象
        s.OnComplete(() =>
        {
            if (gameObject != null)
            {
                Destroy(gameObject);
            }
        });
    }
    
    /// <summary>
    /// 立即关闭面板（无动画）
    /// </summary>
    public virtual void ClosePanelImmediate()
    {
        hasRemoved = true;
        if (gameObject != null)
        {
            Destroy(gameObject);
        }
    }
    
    /// <summary>
    /// 设置面板交互状态
    /// </summary>
    /// <param name="interactable">是否可交互</param>
    public virtual void SetInteractable(bool interactable)
    {
        if (canvasGroup != null)
        {
            canvasGroup.interactable = interactable;
            canvasGroup.blocksRaycasts = interactable;
        }
    }
}