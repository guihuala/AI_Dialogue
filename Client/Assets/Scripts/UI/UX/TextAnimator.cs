using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;
using TMPro;
using Random = UnityEngine.Random;

[RequireComponent(typeof(TMP_Text))]
public class TextAnimator : MonoBehaviour
{
    #region --- 配置参数 ---

    [Header("打字机设置")] [SerializeField] private float defaultTypingSpeed = 0.05f;
    [SerializeField] private bool punctuationPause = true;

    [Header("特效参数")] 
    [SerializeField] private float shakeAmount = 5.0f;
    
    [SerializeField] private float waveSpeed = 4.0f;
    [SerializeField] private float waveHeight = 5.0f;
    
    [SerializeField] private float rainbowSpeed = 1.0f;
    
    [SerializeField] private float pulseSpeed = 5.0f;
    [SerializeField] private float pulseAmount = 0.2f; // 缩放幅度 (1.0 +/- 0.2)

    [SerializeField] private float swingSpeed = 5.0f;
    [SerializeField] private float swingAmount = 10.0f; // 旋转角度

    [SerializeField] private float glitchChance = 0.02f; // 发生故障的概率
    [SerializeField] private float glitchStrength = 10.0f;

    [SerializeField] private float fadeSpeed = 3.0f;
    [SerializeField] private float minAlpha = 0.2f; // 最低透明度

    [Header("音频")] [SerializeField] private AudioSource audioSource;
    [SerializeField] private AudioClip[] typeSounds;

    #endregion

    #region --- 内部变量 ---

    private TMP_Text _tmpText;
    private Coroutine _typingCoroutine;
    private Action _onComplete;
    private bool _isSkipping = false;

    // 特效相关
    private List<EffectRange> _effectRanges = new List<EffectRange>();
    private bool _hasEffects = false;
    private TMP_MeshInfo[] _cachedMeshInfo; // [关键修复] 缓存原始网格信息

    // 标点停顿字典
    private readonly Dictionary<char, float> _punctuationDelays = new Dictionary<char, float>
    {
        { ',', 0.2f }, { '，', 0.2f }, { '.', 0.5f }, { '。', 0.5f },
        { '!', 0.5f }, { '！', 0.5f }, { '?', 0.5f }, { '？', 0.5f }, { '…', 0.5f }
    };

    private struct TextCommand
    {
        public int Index;
        public CommandType Type;
        public float FloatValue;
    }

    private enum CommandType
    {
        Wait,
        Speed
    }

    private struct EffectRange
    {
        public EffectType Type;
        public int StartIndex;
        public int EndIndex;
    }

    private enum EffectType
    {
        Shake,
        Wave,
        Rainbow,
        Wobbly,
        Pulse,
        Swing,
        Glitch,
        Fade
    }

    #endregion

    private void Awake()
    {
        _tmpText = GetComponent<TMP_Text>();
        if (audioSource == null) audioSource = GetComponent<AudioSource>();
    }

    private void OnEnable()
    {
        // 监听 TMP 的内部事件，以防文字被外部意外修改时特效失效
        TMPro_EventManager.TEXT_CHANGED_EVENT.Add(OnTMProChanged);
    }

    private void OnDisable()
    {
        TMPro_EventManager.TEXT_CHANGED_EVENT.Remove(OnTMProChanged);
    }

    private void OnTMProChanged(UnityEngine.Object obj)
    {
        // 只有当受影响的对象是我们自己，且不是因为我们自己在 Update 里刷新的网格时
        if (obj == _tmpText)
        {
            if (_tmpText.textInfo != null)
            {
                _cachedMeshInfo = _tmpText.textInfo.CopyMeshInfoVertexData();
            }
        }
    }

    private void Update()
    {
        if (!DialogueSettings.EnableTextEffects) return;

        // 只有当有特效标签时，才执行网格动画逻辑
        if (_hasEffects && _tmpText.textInfo != null)
        {
            AnimateMesh();
        }
    }

    #region --- 公共接口 ---

    public void ShowText(string content, Action onComplete = null)
    {
        if (_typingCoroutine != null) StopCoroutine(_typingCoroutine);

        _onComplete = onComplete;
        _isSkipping = false;
        _effectRanges.Clear();

        // 1. 解析标签
        string textNoEffects = ParseEffectTags(content);
        string finalCleanText = ParseTypewriterCommands(textNoEffects, out List<TextCommand> commands);

        // 2. 设置给 TMP 并强制刷新一次
        _tmpText.text = finalCleanText;
        _tmpText.ForceMeshUpdate();

        // 3. 立即缓存一份原始的网格数据（位置、颜色、UV等）
        // 这样在 Update 里就可以基于这份“干净”的数据做动画，而不会产生漂移
        _cachedMeshInfo = _tmpText.textInfo.CopyMeshInfoVertexData();

        _hasEffects = _effectRanges.Count > 0;
        _tmpText.maxVisibleCharacters = 0;

        // 4. 开始打字
        _typingCoroutine = StartCoroutine(TypingProcess(finalCleanText, commands));
    }

    public void SkipTypewriter()
    {
        if (_typingCoroutine != null)
        {
            _isSkipping = true;
        }
    }

    #endregion

    #region --- 打字机逻辑 ---

    private IEnumerator TypingProcess(string text, List<TextCommand> commands)
    {
        int totalChars = text.Length;
        int visibleCount = 0;
        // 应用全局速度倍率 (速度越快，间隔越小，所以是 除以 倍率)
        float currentSpeed = defaultTypingSpeed / DialogueSettings.TextSpeedMultiplier;

        // 如果全局禁用了打字机，直接跳过循环
        if (!DialogueSettings.EnableTypewriter)
        {
            _tmpText.maxVisibleCharacters = totalChars;
            _onComplete?.Invoke();
            yield break; 
        }

        while (visibleCount <= totalChars)
        {
            if (_isSkipping)
            {
                _tmpText.maxVisibleCharacters = totalChars;
                break;
            }

            _tmpText.maxVisibleCharacters = visibleCount;

            // 处理指令
            if (commands != null && commands.Count > 0)
            {
                if (commands[0].Index == visibleCount)
                {
                    var cmd = commands[0];
                    commands.RemoveAt(0);
                    
                    if (cmd.Type == CommandType.Wait) yield return new WaitForSeconds(cmd.FloatValue); 
                    else if (cmd.Type == CommandType.Speed) currentSpeed = cmd.FloatValue / DialogueSettings.TextSpeedMultiplier;
                }
            }

            // 标点停顿
            if (punctuationPause && visibleCount > 0 && visibleCount < text.Length)
            {
                char lastChar = text[visibleCount - 1];
                if (_punctuationDelays.ContainsKey(lastChar))
                    yield return new WaitForSeconds(_punctuationDelays[lastChar]);
            }

            // 音效
            if (DialogueSettings.EnableTypingSound && visibleCount < totalChars && visibleCount % 2 == 0) 
            {
                PlayTypeSound();
            }

            yield return new WaitForSeconds(currentSpeed);
            visibleCount++;
        }

        _tmpText.maxVisibleCharacters = totalChars;
        _typingCoroutine = null;
        _onComplete?.Invoke();
    }

    private void PlayTypeSound()
    {
        if (audioSource != null && typeSounds != null && typeSounds.Length > 0)
        {
            audioSource.PlayOneShot(typeSounds[Random.Range(0, typeSounds.Length)]);
        }
    }

    #endregion

    #region --- 特效动画逻辑 (Update) ---

    private void AnimateMesh()
    {
        // 防空检查：如果没有缓存，或者缓存和当前的网格数量对不上（说明文本刚变，缓存还没来得及更新），就先不执行特效
        if (_tmpText.textInfo == null || _cachedMeshInfo == null) return;
        if (_cachedMeshInfo.Length != _tmpText.textInfo.meshInfo.Length) return;

        var textInfo = _tmpText.textInfo;
        bool meshChanged = false;

        // 1. 每一帧，先从 Cache 恢复原始顶点位置
        for (int i = 0; i < textInfo.characterCount; i++)
        {
            TMP_CharacterInfo charInfo = textInfo.characterInfo[i];
            if (!charInfo.isVisible) continue;

            int matIndex = charInfo.materialReferenceIndex;
            int vertIndex = charInfo.vertexIndex;

            // 再次确保索引安全，防止数组越界崩溃
            if (matIndex >= _cachedMeshInfo.Length || matIndex >= textInfo.meshInfo.Length) continue;

            // 从缓存中获取原始顶点和颜色
            Vector3[] sourceVerts = _cachedMeshInfo[matIndex].vertices;
            Color32[] sourceColors = _cachedMeshInfo[matIndex].colors32;

            // 目标网格
            Vector3[] destVerts = textInfo.meshInfo[matIndex].vertices;
            Color32[] destColors = textInfo.meshInfo[matIndex].colors32;

            // 安全检查：如果顶点数组长度不对（比如缓存是旧的），跳过
            if (vertIndex + 4 > sourceVerts.Length || vertIndex + 4 > destVerts.Length) continue;

            Array.Copy(sourceVerts, vertIndex, destVerts, vertIndex, 4);
            Array.Copy(sourceColors, vertIndex, destColors, vertIndex, 4);

            meshChanged = true;
        }

        // 2. 应用特效偏移 (这部分逻辑保持不变)
        foreach (var range in _effectRanges)
        {
            for (int i = range.StartIndex; i < range.EndIndex; i++)
            {
                if (i >= textInfo.characterCount) continue;
                var charInfo = textInfo.characterInfo[i];
                if (!charInfo.isVisible) continue;

                int matIndex = charInfo.materialReferenceIndex;
                int vertIndex = charInfo.vertexIndex;

                if (matIndex >= textInfo.meshInfo.Length) continue; // 安全检查

                Vector3[] verts = textInfo.meshInfo[matIndex].vertices;
                Color32[] colors = textInfo.meshInfo[matIndex].colors32;

                // 安全检查
                if (vertIndex + 4 > verts.Length) continue;

                Vector3 offset = Vector3.zero;
                
                // 1. 先计算字符中心点 (用于缩放和旋转)
                // TMP 的顶点顺序通常是: 0:左下, 1:左上, 2:右上, 3:右下
                // 中心点 = (左下 + 右上) / 2
                Vector3 center = (verts[vertIndex + 0] + verts[vertIndex + 2]) / 2;
                Matrix4x4 matrix = Matrix4x4.identity;

                switch (range.Type)
                {
                    case EffectType.Shake:
                        // 原有的 Shake
                        offset = new Vector3(Random.Range(-shakeAmount, shakeAmount),
                            Random.Range(-shakeAmount, shakeAmount), 0);
                        break;
                    case EffectType.Wave:
                        // 原有的 Wave
                        offset = new Vector3(0, Mathf.Sin(Time.time * waveSpeed + i * 0.5f) * waveHeight, 0);
                        break;
                    case EffectType.Wobbly:
                         // 原有的 Wobbly
                        offset = new Vector3(Mathf.Sin(Time.time * 3f + i), Mathf.Cos(Time.time * 2f + i), 0) * 1.5f;
                        break;
                    case EffectType.Rainbow:
                         // 原有的 Rainbow
                        float hue = Mathf.Repeat(Time.time * rainbowSpeed + i * 0.05f, 1f);
                        Color32 rainbowColor = Color.HSVToRGB(hue, 1f, 1f);
                        // 注意：这里需要保留原有的 Alpha 值，否则可能会覆盖掉 Fade 特效
                        byte originalAlpha = colors[vertIndex + 0].a; 
                        rainbowColor.a = originalAlpha;
                        
                        colors[vertIndex + 0] = rainbowColor;
                        colors[vertIndex + 1] = rainbowColor;
                        colors[vertIndex + 2] = rainbowColor;
                        colors[vertIndex + 3] = rainbowColor;
                        break;
                    
                    case EffectType.Pulse:
                        // 缩放逻辑
                        float scaleParams = 1 + Mathf.Sin(Time.time * pulseSpeed + i * 0.5f) * pulseAmount;
                        // 创建缩放矩阵：以中心点为原点进行缩放
                        matrix = Matrix4x4.TRS(center, Quaternion.identity, Vector3.one * scaleParams) 
                                 * Matrix4x4.TRS(-center, Quaternion.identity, Vector3.one);
                        break;

                    case EffectType.Swing:
                        // 旋转逻辑 (钟摆)
                        float angle = Mathf.Sin(Time.time * swingSpeed + i * 0.2f) * swingAmount;
                        Quaternion rot = Quaternion.Euler(0, 0, angle);
                        // 创建旋转矩阵：以中心点为轴心
                        matrix = Matrix4x4.TRS(center, rot, Vector3.one) 
                                 * Matrix4x4.TRS(-center, Quaternion.identity, Vector3.one);
                        break;

                    case EffectType.Glitch:
                        // 故障逻辑：极低概率发生大幅度位移，制造闪烁错位感
                        if (Random.value < glitchChance)
                        {
                            offset = new Vector3(
                                Random.Range(-glitchStrength, glitchStrength),
                                Random.Range(-glitchStrength * 0.5f, glitchStrength * 0.5f), 
                                0);
                        }
                        break;
                        
                    case EffectType.Fade:
                        // 透明度逻辑
                        float alphaRaw = (Mathf.Sin(Time.time * fadeSpeed + i * 0.5f) + 1) / 2f; // 0~1
                        // 映射到 minAlpha ~ 1.0
                        float alphaVal = Mathf.Lerp(minAlpha, 1.0f, alphaRaw);
                        byte alphaByte = (byte)(alphaVal * 255);
                        
                        colors[vertIndex + 0].a = alphaByte;
                        colors[vertIndex + 1].a = alphaByte;
                        colors[vertIndex + 2].a = alphaByte;
                        colors[vertIndex + 3].a = alphaByte;
                        break;
                }

                // 统一应用位置偏移
                if (offset != Vector3.zero)
                {
                    verts[vertIndex + 0] += offset;
                    verts[vertIndex + 1] += offset;
                    verts[vertIndex + 2] += offset;
                    verts[vertIndex + 3] += offset;
                }

                // 统一应用矩阵变换 (缩放/旋转)
                // 只有当矩阵不是单位矩阵时才计算，节省性能
                if (matrix != Matrix4x4.identity)
                {
                    verts[vertIndex + 0] = matrix.MultiplyPoint3x4(verts[vertIndex + 0]);
                    verts[vertIndex + 1] = matrix.MultiplyPoint3x4(verts[vertIndex + 1]);
                    verts[vertIndex + 2] = matrix.MultiplyPoint3x4(verts[vertIndex + 2]);
                    verts[vertIndex + 3] = matrix.MultiplyPoint3x4(verts[vertIndex + 3]);
                }

                if (range.Type != EffectType.Rainbow)
                {
                    verts[vertIndex + 0] += offset;
                    verts[vertIndex + 1] += offset;
                    verts[vertIndex + 2] += offset;
                    verts[vertIndex + 3] += offset;
                }
            }
        }

        // 3. 上传修改后的网格
        if (meshChanged)
        {
            _tmpText.UpdateVertexData(TMP_VertexDataUpdateFlags.Vertices | TMP_VertexDataUpdateFlags.Colors32);
        }
    }

    #endregion

    #region --- 标签解析 ---

    private string ParseEffectTags(string text)
    {
        StringBuilder sb = new StringBuilder();
        string pattern = @"<(shake|wave|rainbow|wobbly|pulse|swing|glitch|fade)>(.*?)</\1>";
        int lastIndex = 0;
        int cleanIndex = 0;

        foreach (Match m in Regex.Matches(text, pattern))
        {
            sb.Append(text.Substring(lastIndex, m.Index - lastIndex));
            cleanIndex += (m.Index - lastIndex);

            string typeStr = m.Groups[1].Value;
            string content = m.Groups[2].Value;
            
            EffectType type = EffectType.Shake;
            if (typeStr == "wave") type = EffectType.Wave;
            else if (typeStr == "rainbow") type = EffectType.Rainbow;
            else if (typeStr == "wobbly") type = EffectType.Wobbly;
            else if (typeStr == "pulse") type = EffectType.Pulse;
            else if (typeStr == "swing") type = EffectType.Swing;
            else if (typeStr == "glitch") type = EffectType.Glitch;
            else if (typeStr == "fade") type = EffectType.Fade;
            
            _effectRanges.Add(new EffectRange
            {
                Type = type,
                StartIndex = cleanIndex,
                EndIndex = cleanIndex + content.Length
            });

            sb.Append(content);
            cleanIndex += content.Length;
            lastIndex = m.Index + m.Length;
        }

        sb.Append(text.Substring(lastIndex));
        return sb.ToString();
    }

    private string ParseTypewriterCommands(string text, out List<TextCommand> commands)
    {
        commands = new List<TextCommand>();
        StringBuilder sb = new StringBuilder();
        string pattern = @"\[(wait|speed)=([0-9.]+)\]";
        int lastIndex = 0;
        int cleanIndex = 0;

        foreach (Match m in Regex.Matches(text, pattern))
        {
            sb.Append(text.Substring(lastIndex, m.Index - lastIndex));
            cleanIndex += (m.Index - lastIndex);

            string typeStr = m.Groups[1].Value;
            if (float.TryParse(m.Groups[2].Value, out float val))
            {
                commands.Add(new TextCommand
                {
                    Index = cleanIndex,
                    Type = typeStr == "wait" ? CommandType.Wait : CommandType.Speed,
                    FloatValue = val
                });
            }

            lastIndex = m.Index + m.Length;
        }

        sb.Append(text.Substring(lastIndex));
        return sb.ToString();
    }

    #endregion
}