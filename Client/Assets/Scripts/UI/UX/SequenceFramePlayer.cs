using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

#if UNITY_EDITOR
using UnityEditor;
#endif

[AddComponentMenu("Sequence/Sequence Frame Player")]
public class SequenceFramePlayer : MonoBehaviour
{
    public enum TargetType { Auto, SpriteRenderer, UIImage, RawImage }
    public enum PlaybackMode { Once, Loop, PingPong }
    public enum TimeMode { ScaledTime, UnscaledTime }

    [Header("Target")]
    [Tooltip("自动：优先找 SpriteRenderer，其次 Image，再次 RawImage")]
    public TargetType targetType = TargetType.Auto;

    [Tooltip("目标 SpriteRenderer（可空，自动查找）")]
    public SpriteRenderer spriteRenderer;

    [Tooltip("目标 UI Image（可空，自动查找）")]
    public Image uiImage;

    [Tooltip("目标 RawImage（可空，自动查找）")]
    public RawImage rawImage;

    [Header("Frames")]
    [Tooltip("播放帧（Sprite 模式）")]
    public List<Sprite> spriteFrames = new List<Sprite>();

    [Tooltip("播放帧（Texture 模式，供 RawImage 使用）")]
    public List<Texture> textureFrames = new List<Texture>();

    [Tooltip("按名字排序帧（适合 0001,0002...）")]
    public bool sortByName = true;

    [Header("Playback")]
    [Min(1)]
    public int fps = 12;

    public PlaybackMode playbackMode = PlaybackMode.Loop;

    public TimeMode timeMode = TimeMode.ScaledTime;

    [Tooltip("Awake 时自动播放")]
    public bool playOnAwake = true;

    [Tooltip("在同一帧只更新一次贴图（避免抖动）")]
    public bool skipRedundantApply = true;

    [Tooltip("初始从第几帧开始（0 基）")]
    public int startFrame = 0;

    [Header("Events")]
    public UnityEvent onLoop;
    public UnityEvent onCompleted; // Once 模式播完触发
    public UnityEvent<int> onFrameChanged; // 参数：当前帧索引

    [Header("Debug")]
    [SerializeField] private int currentIndex = 0;
    [SerializeField] private bool isPlaying = false;
    [SerializeField] private int direction = 1; // 用于 PingPong

    private float _accumulator;
    private float _frameDuration => 1f / Mathf.Max(1, fps);
    private TargetType _resolvedTarget;

    // --- Public API ---

    public bool IsPlaying => isPlaying;
    public int FrameCount => UsingSprites ? spriteFrames.Count : textureFrames.Count;
    public int CurrentIndex => currentIndex;
    public float NormalizedTime
    {
        get => FrameCount <= 1 ? 0 : (float)currentIndex / (FrameCount - 1);
        set => SetIndex(Mathf.RoundToInt(Mathf.Clamp01(value) * Mathf.Max(0, FrameCount - 1)), true);
    }

    public void Play()
    {
        if (FrameCount == 0) return;
        isPlaying = true;
    }

    public void Pause() => isPlaying = false;

    public void Stop(bool rewind = true)
    {
        isPlaying = false;
        if (rewind) SetIndex(startFrame, true);
    }

    public void NextFrame() => Step(1);
    public void PrevFrame() => Step(-1);
    
    /// <summary>
    /// 设置到具体帧索引
    /// </summary>
    public void SetIndex(int index, bool forceApply = false)
    {
        index = Mathf.Clamp(index, 0, Mathf.Max(0, FrameCount - 1));
        if (currentIndex == index && !forceApply && skipRedundantApply) return;
        currentIndex = index;
        ApplyIndex(currentIndex, forceApply);
        onFrameChanged?.Invoke(currentIndex);
    }

    // --- Lifecycle ---

    private void Reset()
    {
        AutoResolveTargets();
        playOnAwake = true;
        fps = 12;
        playbackMode = PlaybackMode.Loop;
        timeMode = TimeMode.ScaledTime;
    }

    private void Awake()
    {
        AutoResolveTargets();
        if (sortByName)
        {
            if (spriteFrames.Count > 1)
                spriteFrames.Sort((a, b) => string.Compare(a?.name, b?.name, StringComparison.Ordinal));
            if (textureFrames.Count > 1)
                textureFrames.Sort((a, b) => string.Compare(a?.name, b?.name, StringComparison.Ordinal));
        }
        currentIndex = Mathf.Clamp(startFrame, 0, Mathf.Max(0, FrameCount - 1));
        ApplyIndex(currentIndex, true);
        if (playOnAwake && FrameCount > 0) Play();
    }

    private void Update()
    {
        if (!isPlaying || FrameCount <= 1) return;
        float dt = timeMode == TimeMode.UnscaledTime ? Time.unscaledDeltaTime : Time.deltaTime;
        _accumulator += dt;

        while (_accumulator >= _frameDuration)
        {
            _accumulator -= _frameDuration;
            Advance();
        }
    }

    // --- Internal ---

    private bool UsingSprites => spriteFrames.Count > 0 || (targetType == TargetType.SpriteRenderer || targetType == TargetType.UIImage || targetType == TargetType.Auto);
    private bool UsingTextures => textureFrames.Count > 0 || targetType == TargetType.RawImage;

    private void AutoResolveTargets()
    {
        if (targetType == TargetType.Auto)
        {
            spriteRenderer = spriteRenderer ?? GetComponent<SpriteRenderer>();
            uiImage = uiImage ?? GetComponent<Image>();
            rawImage = rawImage ?? GetComponent<RawImage>();

            if (spriteRenderer) _resolvedTarget = TargetType.SpriteRenderer;
            else if (uiImage) _resolvedTarget = TargetType.UIImage;
            else if (rawImage) _resolvedTarget = TargetType.RawImage;
            else _resolvedTarget = TargetType.SpriteRenderer; // default
        }
        else
        {
            _resolvedTarget = targetType;
        }
    }

    private void Advance()
    {
        int count = FrameCount;
        if (count == 0) return;

        int next = currentIndex + direction;

        switch (playbackMode)
        {
            case PlaybackMode.Once:
                if (next >= count)
                {
                    next = count - 1;
                    SetIndex(next);
                    isPlaying = false;
                    onCompleted?.Invoke();
                    return;
                }
                break;

            case PlaybackMode.Loop:
                if (next >= count)
                {
                    next = 0;
                    onLoop?.Invoke();
                }
                break;

            case PlaybackMode.PingPong:
                if (next >= count)
                {
                    direction = -1;
                    next = Mathf.Clamp(count - 2, 0, count - 1);
                    onLoop?.Invoke();
                }
                else if (next < 0)
                {
                    direction = 1;
                    next = Mathf.Clamp(1, 0, count - 1);
                    onLoop?.Invoke();
                }
                break;
        }

        SetIndex(next);
    }

    private void Step(int delta)
    {
        int count = FrameCount;
        if (count == 0) return;
        int idx = currentIndex + delta;
        if (playbackMode == PlaybackMode.Loop)
        {
            idx = (idx % count + count) % count;
        }
        else
        {
            idx = Mathf.Clamp(idx, 0, count - 1);
        }
        SetIndex(idx);
    }

    private void ApplyIndex(int index, bool force = false)
    {
        AutoResolveTargets();

        if (_resolvedTarget == TargetType.SpriteRenderer || _resolvedTarget == TargetType.UIImage || _resolvedTarget == TargetType.Auto)
        {
            if (spriteFrames.Count == 0) return;
            var sp = spriteFrames[Mathf.Clamp(index, 0, spriteFrames.Count - 1)];
            if (spriteRenderer)
            {
                if (!skipRedundantApply || force || spriteRenderer.sprite != sp)
                    spriteRenderer.sprite = sp;
            }
            if (uiImage)
            {
                if (!skipRedundantApply || force || uiImage.sprite != sp)
                    uiImage.sprite = sp;
                // 让 Image 以原图显示
                if (uiImage.type != Image.Type.Simple) uiImage.type = Image.Type.Simple;
                uiImage.SetNativeSize();
            }
        }
        else if (_resolvedTarget == TargetType.RawImage)
        {
            if (rawImage == null || textureFrames.Count == 0) return;
            var tex = textureFrames[Mathf.Clamp(index, 0, textureFrames.Count - 1)];
            if (!skipRedundantApply || force || rawImage.texture != tex)
                rawImage.texture = tex;

            // 让 RawImage 以原图尺寸显示
            var rt = rawImage.rectTransform;
            if (rt && tex)
                rt.SetSizeWithCurrentAnchors(RectTransform.Axis.Horizontal, tex.width);
        }
    }
}