using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using DG.Tweening;

public enum AnimationType
{
    Scale,          // 缩放
    Position,       // 位置移动
    Rotation,       // 旋转
    Color,          // 颜色变化
    Combined        // 组合动画
}

public class ButtonHoverAnimation : MonoBehaviour, IPointerEnterHandler, IPointerExitHandler, IPointerDownHandler, IPointerUpHandler
{
    [Header("基本设置")]
    [Tooltip("动画类型")]
    public AnimationType animationType = AnimationType.Scale;
    
    [Tooltip("启用点击动画")]
    public bool enableClickAnimation = true;
    
    [Tooltip("动画时长")]
    public float animationDuration = 0.2f;
    
    [Tooltip("缓动函数类型")]
    public Ease easeType = Ease.OutBack;

    [Header("缩放动画设置")]
    [Tooltip("悬停时缩放倍数")]
    public float hoverScale = 1.1f;
    [Tooltip("点击时缩放倍数")]
    public float clickScale = 0.95f;

    [Header("移动动画设置")]
    [Tooltip("悬停时移动偏移")]
    public Vector2 hoverMoveOffset = new Vector2(0, 10f);
    [Tooltip("点击时移动偏移")]
    public Vector2 clickMoveOffset = new Vector2(0, -5f);

    [Header("旋转动画设置")]
    [Tooltip("悬停时旋转角度")]
    public float hoverRotation = 5f;
    [Tooltip("点击时旋转角度")]
    public float clickRotation = -3f;

    [Header("颜色动画设置")]
    [Tooltip("悬停时颜色")]
    public Color hoverColor = new Color(1.2f, 1.2f, 1.2f, 1f);
    [Tooltip("点击时颜色")]
    public Color clickColor = new Color(0.9f, 0.9f, 0.9f, 1f);
    
    [Header("高级设置")]
    [Tooltip("启用震动效果")]
    public bool enableShake = true;
    [Tooltip("震动强度")]
    public float shakeStrength = 10f;
    [Tooltip("震动持续时间")]
    public float shakeDuration = 0.5f;
    [Tooltip("震动频率")]
    public int shakeVibrato = 10;

    private Vector3 originalScale;
    private Vector3 originalPosition;
    private Quaternion originalRotation;
    private Color originalColor;
    
    private Image buttonImage;
    private Sequence hoverSequence;
    private Sequence clickSequence;

    private void Start()
    {
        // 保存原始状态
        originalScale = transform.localScale;
        originalPosition = transform.localPosition;
        originalRotation = transform.rotation;
        
        // 获取UI组件
        buttonImage = GetComponent<Image>();
        
        if (buttonImage != null)
        {
            originalColor = buttonImage.color;
        }
    }

    public void OnPointerEnter(PointerEventData eventData)
    {
        KillAllTweens();
        
        switch (animationType)
        {
            case AnimationType.Scale:
                PlayScaleAnimation(hoverScale);
                break;
                
            case AnimationType.Position:
                PlayMoveAnimation(hoverMoveOffset);
                break;
                
            case AnimationType.Rotation:
                PlayRotationAnimation(hoverRotation);
                break;
                
            case AnimationType.Color:
                PlayColorAnimation(hoverColor);
                break;
                
            case AnimationType.Combined:
                PlayCombinedHoverAnimation();
                break;
        }
        
        // 添加震动效果
        if (enableShake)
        {
            transform.DOShakePosition(shakeDuration, shakeStrength, shakeVibrato, 90, false, true)
                     .SetEase(Ease.OutQuad);
        }
    }

    public void OnPointerExit(PointerEventData eventData)
    {
        KillAllTweens();
        PlayResetAnimation();
    }

    public void OnPointerDown(PointerEventData eventData)
    {
        if (!enableClickAnimation) return;
        
        KillAllTweens();
        
        switch (animationType)
        {
            case AnimationType.Scale:
                PlayScaleAnimation(clickScale);
                break;
                
            case AnimationType.Position:
                PlayMoveAnimation(clickMoveOffset);
                break;
                
            case AnimationType.Rotation:
                PlayRotationAnimation(clickRotation);
                break;
                
            case AnimationType.Color:
                PlayColorAnimation(clickColor);
                break;
                
            case AnimationType.Combined:
                PlayCombinedClickAnimation();
                break;
        }
    }

    public void OnPointerUp(PointerEventData eventData)
    {
        if (!enableClickAnimation) return;
        PlayResetAnimation();
    }

    #region 动画方法
    private void PlayScaleAnimation(float targetScale)
    {
        transform.DOScale(originalScale * targetScale, animationDuration)
                 .SetEase(easeType);
    }

    private void PlayMoveAnimation(Vector2 offset)
    {
        Vector3 targetPosition = originalPosition + (Vector3)offset;
        transform.DOLocalMove(targetPosition, animationDuration)
                 .SetEase(easeType);
    }

    private void PlayRotationAnimation(float angle)
    {
        transform.DORotate(new Vector3(0, 0, angle), animationDuration)
                 .SetEase(easeType);
    }

    private void PlayColorAnimation(Color targetColor)
    {
        if (buttonImage != null)
        {
            buttonImage.DOColor(targetColor, animationDuration)
                       .SetEase(easeType);
        }
    }

    private void PlayCombinedHoverAnimation()
    {
        hoverSequence = DOTween.Sequence();
        
        hoverSequence.Join(transform.DOScale(originalScale * hoverScale, animationDuration));
        hoverSequence.Join(transform.DOLocalMove(originalPosition + (Vector3)hoverMoveOffset, animationDuration));
        hoverSequence.Join(transform.DORotate(new Vector3(0, 0, hoverRotation), animationDuration));
        
        if (buttonImage != null)
        {
            hoverSequence.Join(buttonImage.DOColor(hoverColor, animationDuration));
        }
        
        hoverSequence.SetEase(easeType);
    }

    private void PlayCombinedClickAnimation()
    {
        clickSequence = DOTween.Sequence();
        
        clickSequence.Join(transform.DOScale(originalScale * clickScale, animationDuration));
        clickSequence.Join(transform.DOLocalMove(originalPosition + (Vector3)clickMoveOffset, animationDuration));
        clickSequence.Join(transform.DORotate(new Vector3(0, 0, clickRotation), animationDuration));
        
        if (buttonImage != null)
        {
            clickSequence.Join(buttonImage.DOColor(clickColor, animationDuration));
        }
        
        clickSequence.SetEase(easeType);
    }

    private void PlayResetAnimation()
    {
        transform.DOScale(originalScale, animationDuration)
                 .SetEase(easeType);
        
        transform.DOLocalMove(originalPosition, animationDuration)
                 .SetEase(easeType);
        
        transform.DORotate(originalRotation.eulerAngles, animationDuration)
                 .SetEase(easeType);
        
        if (buttonImage != null)
        {
            buttonImage.DOColor(originalColor, animationDuration)
                       .SetEase(easeType);
        }
    }
    #endregion

    private void KillAllTweens()
    {
        transform.DOKill();
        
        if (buttonImage != null) buttonImage.DOKill();
        
        if (hoverSequence != null) hoverSequence.Kill();
        if (clickSequence != null) clickSequence.Kill();
    }

    private void OnDestroy()
    {
        KillAllTweens();
    }

    private void OnDisable()
    {
        // 当按钮被禁用时重置状态
        transform.localScale = originalScale;
        transform.localPosition = originalPosition;
        transform.rotation = originalRotation;
        
        if (buttonImage != null) buttonImage.color = originalColor;
    }
}