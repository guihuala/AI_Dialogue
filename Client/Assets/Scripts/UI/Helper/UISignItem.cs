using System;
using System.Collections;
using UnityEngine;
using UnityEngine.UI;

namespace SimpleUITips
{
    /// <summary>
    /// 图标提示条目（跟随世界坐标）
    /// </summary>
    public class UISignItem : MonoBehaviour
    {
        public Image IconImg;
        public float OffsetY = 150f;

        private RectTransform _rt;
        private GameObject _creator;

        private void Awake() => _rt = GetComponent<RectTransform>();

        public void Init(GameObject creator, string iconPath)
        {
            _creator = creator;
            if (IconImg)
            {
                var sp = string.IsNullOrEmpty(iconPath) ? null : Resources.Load<Sprite>(iconPath);
                if (sp != null) IconImg.sprite = sp;
            }
            RefreshPosition();
        }

        private void LateUpdate() => RefreshPosition();

        private void RefreshPosition()
        {
            if (_rt == null || _creator == null) return;
            var sp = Camera.main != null ? Camera.main.WorldToScreenPoint(_creator.transform.position) : Vector3.zero;
            var lp = UIConvert.ScreenToUIPoint(_rt, sp);
            _rt.localPosition = new Vector2(lp.x, lp.y + OffsetY);
        }
    }
}