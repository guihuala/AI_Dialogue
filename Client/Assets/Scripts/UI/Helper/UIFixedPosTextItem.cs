using System;
using System.Collections;
using UnityEngine;
using UnityEngine.UI;

namespace SimpleUITips
{
    /// <summary>
    /// 固定位置文本条目（可用于分数、状态）
    /// </summary>
    public class UIFixedPosTextItem : MonoBehaviour
    {
        public Text ContentText;

        private RectTransform _rt;
        private float _startY;

        private void Awake() => _rt = GetComponent<RectTransform>();

        public void Init(FixedUIPosType posType, string content)
        {
            if (ContentText) ContentText.text = content;
            transform.localScale = Vector3.zero;

            if (_rt != null)
            {
                var parent = _rt.parent as RectTransform;
                Vector2 target = Vector2.zero;
                if (parent != null)
                {
                    var half = parent.rect.size / 2f;
                    switch (posType)
                    {
                        case FixedUIPosType.Left:   target = new Vector2(-half.x + 120f, 0f); break;
                        case FixedUIPosType.Right:  target = new Vector2( half.x - 120f, 0f); break;
                        case FixedUIPosType.Top:    target = new Vector2(0f,  half.y - 80f); break;
                        case FixedUIPosType.Bottom: target = new Vector2(0f, -half.y + 80f); break;
                        case FixedUIPosType.Center: target = Vector2.zero; break;
                    }
                }
                _rt.localPosition = target;
                _startY = _rt.localPosition.y;
            }

            StartCoroutine(ScaleOverTime(Vector3.zero, Vector3.one, 0.3f));
            StartCoroutine(MoveYOverTime(_startY + 50f, 0.5f));
        }

        private IEnumerator ScaleOverTime(Vector3 from, Vector3 to, float duration)
        {
            float t = 0f;
            while (t < duration)
            {
                transform.localScale = Vector3.Lerp(from, to, t / duration);
                t += Time.unscaledDeltaTime;
                yield return null;
            }
            transform.localScale = to;
        }

        private IEnumerator MoveYOverTime(float targetY, float duration)
        {
            float t = 0f;
            Vector3 start = _rt.localPosition;
            while (t < duration)
            {
                _rt.localPosition = new Vector3(start.x, Mathf.Lerp(start.y, targetY, t / duration), start.z);
                t += Time.unscaledDeltaTime;
                yield return null;
            }
            _rt.localPosition = new Vector3(start.x, targetY, start.z);
        }
    }
}