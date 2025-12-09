using UnityEngine;
using System.Collections.Generic;
using DG.Tweening;

public class ParallaxTilt : MonoBehaviour
{
    [System.Serializable]
    public class Layer
    {
        public RectTransform rect;
        [Tooltip("视差强度（像素）：背景小、前景大，例如 5~40")]
        public float parallax = 15f;
        [Tooltip("限制该图层的最大位移（像素）")]
        public float maxOffset = 40f;

        // 内部：缓存
        [HideInInspector] public Vector2 initialPos;
        [HideInInspector] public Tweener posTweener;
    }

    [Header("Targets")]
    public RectTransform root;
    public List<Layer> layers = new List<Layer>();

    [Header("Tilt (Rotation)")]
    [Tooltip("绕 X 轴最大旋转角（上下点头）")]
    public float maxTiltX = 6f;
    [Tooltip("绕 Y 轴最大旋转角（左右点头）")]
    public float maxTiltY = 8f;
    [Tooltip("旋转 Tweener 的“速度”（秒越小越跟手）")]
    public float rotFollowTime = 0.18f;
    public Ease rotEase = Ease.OutQuad;

    [Header("Root Move (Position)")]
    [Tooltip("根节点随鼠标移动的最大位移（像素）")]
    public Vector2 rootMoveRange = new Vector2(18f, 12f);
    [Tooltip("平移 Tweener 的“速度”")]
    public float moveFollowTime = 0.14f;
    public Ease moveEase = Ease.OutQuad;

    [Header("Parallax (Layers)")]
    [Tooltip("视差 Tweener 的“速度”")]
    public float parallaxFollowTime = 0.16f;
    public Ease parallaxEase = Ease.OutQuad;
    [Tooltip("视差方向与鼠标同向（关=反向）")]
    public bool parallaxSameDirection = false;

    [Header("Scale (Optional)")]
    [Tooltip("是否启用微缩放")]
    public bool enableScale = false;
    [Tooltip("最大缩放偏移，例如 0.02 表示 1%~2%")]
    public float maxScaleDelta = 0.015f;
    [Tooltip("缩放 Tweener 的“速度”")]
    public float scaleFollowTime = 0.2f;
    public Ease scaleEase = Ease.OutQuad;

    [Header("Behavior")]
    [Tooltip("鼠标到屏幕边缘时是否达到最大倾斜/位移")]
    public bool edgeIsMax = true;

    // 缓存
    private Quaternion _initialRot;
    private Vector2 _initialAnchoredPos;
    private Vector3 _initialScale;

    private Tweener _rotTweener;
    private Tweener _moveTweener;
    private Tweener _scaleTweener;

    void Awake()
    {
        if (root == null) root = (RectTransform)transform;

        _initialRot = root.localRotation;
        _initialAnchoredPos = root.anchoredPosition;
        _initialScale = root.localScale;

        // 预创建根节点旋转/平移/缩放的 Tweener
        _rotTweener = root.DOLocalRotateQuaternion(_initialRot, rotFollowTime)
            .SetEase(rotEase).SetAutoKill(false).Pause();
        _moveTweener = root.DOAnchorPos(_initialAnchoredPos, moveFollowTime)
            .SetEase(moveEase).SetAutoKill(false).Pause();
        if (enableScale)
        {
            _scaleTweener = root.DOScale(_initialScale, scaleFollowTime)
                .SetEase(scaleEase).SetAutoKill(false).Pause();
        }

        // 记录各图层初始位置并创建 Tweener
        foreach (var L in layers)
        {
            if (L.rect == null) continue;
            L.initialPos = L.rect.anchoredPosition;
            L.posTweener = L.rect.DOAnchorPos(L.initialPos, parallaxFollowTime)
                .SetEase(parallaxEase).SetAutoKill(false).Pause();
        }
    }

    void Update()
    {
        // 1) 计算鼠标归一化坐标（中心为 0,0）
        Vector2 mouse = Input.mousePosition;
        float nx, ny;
        if (edgeIsMax)
        {
            nx = Mathf.Clamp((mouse.x / Screen.width) * 2f - 1f, -1f, 1f);
            ny = Mathf.Clamp((mouse.y / Screen.height) * 2f - 1f, -1f, 1f);
        }
        else
        {
            nx = Mathf.Clamp((mouse.x - Screen.width * 0.5f) / (Screen.width * 0.5f), -1f, 1f);
            ny = Mathf.Clamp((mouse.y - Screen.height * 0.5f) / (Screen.height * 0.5f), -1f, 1f);
        }

        // 2) 根节点目标旋转（微透视）
        float tx = -ny * maxTiltX; // 鼠标上 -> 抬头（绕X负）
        float ty = -nx * maxTiltY; // 鼠标右 -> 向右压（绕Y负）
        Quaternion targetRot = Quaternion.Euler(tx, ty, 0f);

        // 用 ChangeEndValue 刷新目标，不反复分配 Tweener
        _rotTweener.ChangeEndValue(targetRot, true).Play();

        // 3) 根节点目标平移（整体轻微跟随）
        Vector2 targetRootPos = _initialAnchoredPos + new Vector2(nx * rootMoveRange.x, ny * rootMoveRange.y);
        _moveTweener.ChangeEndValue(targetRootPos, true).Play();

        // 4) 视差（各图层位移）
        float dir = parallaxSameDirection ? 1f : -1f;
        Vector2 mouseVec = new Vector2(nx, ny) * dir;

        for (int i = 0; i < layers.Count; i++)
        {
            var L = layers[i];
            if (L.rect == null) continue;

            Vector2 offset = mouseVec * L.parallax;
            offset.x = Mathf.Clamp(offset.x, -L.maxOffset, L.maxOffset);
            offset.y = Mathf.Clamp(offset.y, -L.maxOffset, L.maxOffset);

            Vector2 targetPos = L.initialPos + offset;
            L.posTweener.ChangeEndValue(targetPos, true).Play();
        }

        // 5) 可选：缩放微动（靠边缘略缩放/放大）
        if (enableScale && _scaleTweener != null)
        {
            // 这里用离中心的“强度”计算缩放，越靠边缘缩放越明显
            float strength = Mathf.Clamp01(new Vector2(nx, ny).magnitude);
            float scaleDelta = maxScaleDelta * strength;
            Vector3 targetScale = _initialScale * (1f + scaleDelta);
            _scaleTweener.ChangeEndValue(targetScale, true).Play();
        }

#if UNITY_EDITOR
        bool focus = UnityEditor.EditorWindow.focusedWindow != null;
#else
        bool focus = Application.isFocused;
#endif
        if (!focus)
        {
            BackToInitial(0.25f);
        }
    }

    /// <summary>手动回正（也可给按钮或失焦时调用）</summary>
    public void BackToInitial(float extraEaseTime = 0.25f)
    {
        _rotTweener.ChangeEndValue(_initialRot, true).SetEase(Ease.OutQuad).Play();
        _moveTweener.ChangeEndValue(_initialAnchoredPos, true).SetEase(Ease.OutQuad).Play();

        if (enableScale && _scaleTweener != null)
            _scaleTweener.ChangeEndValue(_initialScale, true).SetEase(Ease.OutQuad).Play();

        foreach (var L in layers)
        {
            if (L.rect == null || L.posTweener == null) continue;
            L.posTweener.ChangeEndValue(L.initialPos, true).SetEase(Ease.OutQuad).Play();
        }
    }

    void OnDisable()
    {
        // 释放中间态，避免停用后残留
        if (_rotTweener != null) _rotTweener.Kill(false);
        if (_moveTweener != null) _moveTweener.Kill(false);
        if (_scaleTweener != null) _scaleTweener.Kill(false);
        foreach (var L in layers)
            if (L.posTweener != null) L.posTweener.Kill(false);
    }
}
