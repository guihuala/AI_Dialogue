using System;
using System.Collections;
using UnityEngine;
using UnityEngine.UI;

namespace SimpleUITips
{

    /// <summary>
    /// 气泡条目
    /// </summary>
    public class UIBubbleItem : MonoBehaviour
    {
        public Text ContentText;
        public Image ContentImage; // 可选
        public Text KeyText;
        public Text ItemNameText;

        private GameObject _creator;
        private GameObject _player;
        private RectTransform _rt;

        private void Awake() => _rt = GetComponent<RectTransform>();

        public void Init(BubbleInfo info, string keys)
        {
            _creator = info.creator;
            _player = info.player;
            if (ContentText) ContentText.text = info.content;
            if (ItemNameText) ItemNameText.text = info.itemName;
            if (KeyText) KeyText.text = keys;

            transform.localScale = Vector3.zero;
            StartCoroutine(ScaleOverTime(Vector3.zero, Vector3.one, 0.2f));
        }

        public void UpdateContent(string content)
        {
            if (ContentText) ContentText.text = content;
        }

        private void LateUpdate()
        {
            if (_creator == null || _rt == null) return;
            var sp = Camera.main != null ? Camera.main.WorldToScreenPoint(_creator.transform.position) : Vector3.zero;
            _rt.localPosition = UIConvert.ScreenToUIPoint(_rt, sp);
        }

        public void DestroyBubble()
        {
            StartCoroutine(ScaleOverTime(Vector3.one, Vector3.zero, 0.2f, () => Destroy(gameObject)));
        }

        private IEnumerator ScaleOverTime(Vector3 from, Vector3 to, float duration, Action onComplete = null)
        {
            float t = 0f;
            while (t < duration)
            {
                transform.localScale = Vector3.Lerp(from, to, t / duration);
                t += Time.unscaledDeltaTime;
                yield return null;
            }
            transform.localScale = to;
            onComplete?.Invoke();
        }
    }
}