using System;
using UnityEngine;
using UnityEngine.UI;

namespace SimpleUITips
{
    /// <summary>
    /// 通用圆形进度条条目（UGUI Image.fillAmount）
    /// </summary>
    public class UICommonProgressItem : MonoBehaviour
    {
        public Image ProgressBarImage;

        private RectTransform _rt;
        private GameObject _creator;
        public float OffsetX = 30f;
        public float OffsetY = 30f;

        private float _curProgress;
        private float _maxProgress;

        private string _key;
        private CircleProgressType _type;
        private Action _onComplete;

        private void Awake() => _rt = GetComponent<RectTransform>();

        public void Init(string key, CircleProgressType type, GameObject creator, float duration, Action onComplete)
        {
            _key = key;
            _type = type;
            _creator = creator;
            _maxProgress = Mathf.Max(0.0001f, duration);
            _curProgress = 0f;
            _onComplete = onComplete;

            if (ProgressBarImage) ProgressBarImage.fillAmount = 0f;
            RefreshPosition();
        }

        private void Update()
        {
            if (_type == CircleProgressType.Auto)
            {
                _curProgress += Time.deltaTime;
                if (ProgressBarImage)
                    ProgressBarImage.fillAmount = Mathf.Clamp01(_curProgress / _maxProgress);
                if (_curProgress >= _maxProgress)
                {
                    _onComplete?.Invoke();
                    Destroy(gameObject);
                    return;
                }
            }
            RefreshPosition();
        }

        private void RefreshPosition()
        {
            if (_rt == null || _creator == null) return;
            var sp = Camera.main != null ? Camera.main.WorldToScreenPoint(_creator.transform.position) : Vector3.zero;
            var lp = UIConvert.ScreenToUIPoint(_rt, sp);
            _rt.localPosition = new Vector2(lp.x + OffsetX, lp.y + OffsetY);
        }

        public void SetManualProgress01(float value01)
        {
            _type = CircleProgressType.Manual;
            if (ProgressBarImage) ProgressBarImage.fillAmount = Mathf.Clamp01(value01);
        }
    }
}