using UnityEngine;
using UnityEngine.UI;

namespace SimpleUITips
{
    /// <summary>
    /// 全局加载遮罩条目（旋转动画与文字提示）
    /// </summary>
    public class UILoadingItem : MonoBehaviour
    {
        public Text MessageText;
        public RectTransform Spinner; // 旋转的菊花图或沙漏图
        public float RotationSpeed = 300f;

        public void UpdateMessage(string message)
        {
            if (MessageText != null)
            {
                MessageText.text = message;
            }
        }

        private void Update()
        {
            if (Spinner != null)
            {
                // 保持匀速旋转
                Spinner.Rotate(Vector3.forward, -RotationSpeed * Time.unscaledDeltaTime);
            }
        }
    }
}