using System.Collections;
using UnityEngine;
using UnityEngine.UI;

namespace SimpleUITips
{
    /// <summary>
    /// 飘字提示条目（缩放+上移，定时销毁）
    /// </summary>
    public class UITipItem : MonoBehaviour
    {
        public Text ContentText;
        public float MoveUp = 50f;
        public float ScaleInTime = 0.3f;
        public float MoveTime = 0.5f;

        private RectTransform _rt;
        private float _startY;
        private float _deadTime;
        private Coroutine _lifeCoro;

        private void Awake() => _rt = GetComponent<RectTransform>();

        public void Init(Vector3 worldPos, string content, float deadTime)
        {
            if (ContentText) ContentText.text = content;
            _deadTime = Mathf.Max(0f, deadTime);

            transform.localScale = Vector3.zero;

            var sp = Camera.main != null ? Camera.main.WorldToScreenPoint(worldPos) : Vector3.zero;
            _rt.localPosition = UIConvert.ScreenToUIPoint(_rt, sp);
            _startY = _rt.localPosition.y;

            StartCoroutine(ScaleOverTime(Vector3.zero, Vector3.one, ScaleInTime));
            StartCoroutine(MoveYOverTime(_startY + MoveUp, MoveTime));
            if (_lifeCoro != null) StopCoroutine(_lifeCoro);
            _lifeCoro = StartCoroutine(LifeTimer(_deadTime));
        }

        public void ResetTip(Vector3 worldPos, string content)
        {
            if (ContentText) ContentText.text = content;
            StopAllCoroutines();
            transform.localScale = Vector3.zero;

            var sp = Camera.main != null ? Camera.main.WorldToScreenPoint(worldPos) : Vector3.zero;
            _rt.localPosition = UIConvert.ScreenToUIPoint(_rt, sp);
            _startY = _rt.localPosition.y;

            StartCoroutine(ScaleOverTime(Vector3.zero, Vector3.one, ScaleInTime));
            StartCoroutine(MoveYOverTime(_startY + MoveUp, MoveTime));
            if (_lifeCoro != null) StopCoroutine(_lifeCoro);
            _lifeCoro = StartCoroutine(LifeTimer(_deadTime));
        }

        private IEnumerator LifeTimer(float t)
        {
            yield return new WaitForSeconds(t);
            Destroy(gameObject);
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