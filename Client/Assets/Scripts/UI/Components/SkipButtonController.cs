using UnityEngine;
using UnityEngine.UI;

[RequireComponent(typeof(Button))]
public class SkipButtonController : MonoBehaviour
{
    private Button skipButton;

    private void Awake()
    {
        skipButton = GetComponent<Button>();
        
        // 游戏刚启动时，强行把自己隐藏起来，防止在不该出现的时候暴露
        gameObject.SetActive(false);
    }

    private void Start()
    {
        // 注册监听显示/隐藏的广播
        MsgCenter.RegisterMsg(MsgConst.TOGGLE_SKIP_BUTTON, OnToggleSkipButton);

        // 代码自动绑定点击事件，你就不用在 Unity 面板里手动拖拽 GameManager 了！
        skipButton.onClick.AddListener(() => {
            if (GameManager.Instance != null)
            {
                GameManager.Instance.SkipIntro();
            }
        });
    }

    private void OnDestroy()
    {
        // 销毁时注销监听，防止内存泄漏
        MsgCenter.UnregisterMsg(MsgConst.TOGGLE_SKIP_BUTTON, OnToggleSkipButton);
    }

    private void OnToggleSkipButton(params object[] args)
    {
        // 接收 GameManager 传来的 true 或 false
        bool show = (bool)args[0];
        gameObject.SetActive(show);
    }
}