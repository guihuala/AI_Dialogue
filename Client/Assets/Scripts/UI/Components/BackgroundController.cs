using UnityEngine;
using UnityEngine.UI;
using DG.Tweening;

public class BackgroundController : MonoBehaviour
{
    [Header("UI 引用")]
    public Image backgroundImage;   // 显示当前背景的 Image
    public Image fadeOverlay;       // 用于过渡的黑色遮罩 (或者你可以直接对 backgroundImage 做 Alpha 渐变)
    
    [Header("配置")]
    public float fadeDuration = 0.8f; // 渐变时长

    private string currentLoadedScene = "";

    private void Start()
    {
        MsgCenter.RegisterMsg(MsgConst.CHANGE_SCENE, OnSceneChanged);
        
        // 初始确保遮罩是透明的
        if (fadeOverlay) fadeOverlay.color = new Color(0, 0, 0, 0);
    }

    private void OnDestroy()
    {
        MsgCenter.UnregisterMsg(MsgConst.CHANGE_SCENE, OnSceneChanged);
    }

    private void OnSceneChanged(params object[] args)
    {
        string newSceneName = (string)args[0];
        
        if (newSceneName == currentLoadedScene) return;

        // 加载图片 (假定你的图片放在 Resources/Backgrounds/ 文件夹下，且名字与场景名完全一致)
        Sprite newBgSprite = Resources.Load<Sprite>($"Backgrounds/{newSceneName}");
        
        if (newBgSprite == null)
        {
            Debug.LogWarning($"[Background] 找不到场景图片: Resources/Backgrounds/{newSceneName}，尝试使用默认背景。");
            newBgSprite = Resources.Load<Sprite>("Backgrounds/未知");
            if (newBgSprite == null) return;
        }

        currentLoadedScene = newSceneName;
        SwitchBackgroundSmoothly(newBgSprite);
    }

    private void SwitchBackgroundSmoothly(Sprite newSprite)
    {
        if (fadeOverlay == null)
        {
            // 如果没有黑色遮罩，直接硬切
            backgroundImage.sprite = newSprite;
            return;
        }

        // 使用 DOTween 做一个经典的“黑场过渡” (黑屏 -> 换图 -> 亮起)
        Sequence seq = DOTween.Sequence();
        seq.Append(fadeOverlay.DOFade(1f, fadeDuration / 2f)); // 暗场
        seq.AppendCallback(() => 
        {
            backgroundImage.sprite = newSprite; // 在最黑的时候换图
        });
        seq.Append(fadeOverlay.DOFade(0f, fadeDuration / 2f)); // 亮场
    }
}