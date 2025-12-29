using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using System.Collections;
using System;

public enum GameScene
{
    MainMenu = 0,   // 主菜单
    Gameplay = 1,   // 游戏场景
}

public class SceneLoader : SingletonPersistent<SceneLoader>
{
    [Header("加载界面设置")]
    [SerializeField] private CanvasGroup loadingCanvas;
    [SerializeField] private Image progressBar;
    [SerializeField] private Text progressText;
    [SerializeField] private float fadeDuration = 0.5f;
    [SerializeField] private float minLoadingTime = 1.5f;

    private AsyncOperation loadingOperation;
    private bool isLoading = false;

    protected override void Awake()
    {
        base.Awake();
        DontDestroyOnLoad(gameObject);
        
        // 初始化加载界面
        if (loadingCanvas != null)
        {
            loadingCanvas.alpha = 0f;
            loadingCanvas.gameObject.SetActive(false);
        }
    }

    /// <summary>
    /// 加载指定枚举场景
    /// </summary>
    public void LoadScene(GameScene scene, Action onComplete = null)
    {
        if (isLoading) return;
        
        string sceneName = scene.ToString();
        StartCoroutine(LoadSceneRoutine(sceneName, onComplete));
    }

    /// <summary>
    /// 重新加载当前场景
    /// </summary>
    public void ReloadCurrentScene(Action onComplete = null)
    {
        if (isLoading) return;
        
        string currentScene = SceneManager.GetActiveScene().name;
        StartCoroutine(LoadSceneRoutine(currentScene, onComplete));
    }

    private IEnumerator LoadSceneRoutine(string sceneName, Action onComplete)
    {
        isLoading = true;
        float startTime = Time.time;

        // 淡入加载界面
        yield return StartCoroutine(FadeLoadingScreen(0f, 1f));

        // 开始异步加载场景
        loadingOperation = SceneManager.LoadSceneAsync(sceneName);
        loadingOperation.allowSceneActivation = false;

        // 更新加载进度
        while (!loadingOperation.isDone)
        {
            float progress = Mathf.Clamp01(loadingOperation.progress / 0.9f);
            UpdateProgressUI(progress);

            // 确保最小加载时间，然后激活场景
            if (loadingOperation.progress >= 0.9f && 
                Time.time - startTime >= minLoadingTime)
            {
                loadingOperation.allowSceneActivation = true;
            }

            yield return null;
        }

        // 等待一帧确保场景完全加载
        yield return null;

        // 淡出加载界面
        yield return StartCoroutine(FadeLoadingScreen(1f, 0f));

        isLoading = false;
        onComplete?.Invoke();
    }

    private IEnumerator FadeLoadingScreen(float startAlpha, float targetAlpha)
    {
        if (loadingCanvas == null) yield break;

        loadingCanvas.gameObject.SetActive(true);
        float elapsedTime = 0f;

        while (elapsedTime < fadeDuration)
        {
            elapsedTime += Time.deltaTime;
            loadingCanvas.alpha = Mathf.Lerp(startAlpha, targetAlpha, elapsedTime / fadeDuration);
            yield return null;
        }

        loadingCanvas.alpha = targetAlpha;

        // 如果完全淡出，则禁用游戏对象
        if (targetAlpha == 0f)
        {
            loadingCanvas.gameObject.SetActive(false);
        }
    }

    private void UpdateProgressUI(float progress)
    {
        if (progressBar != null)
            progressBar.fillAmount = progress;
        
        if (progressText != null)
            progressText.text = $"{(progress * 100):0}%";
    }

    /// <summary>
    /// 检查是否正在加载
    /// </summary>
    public bool IsLoading() => isLoading;
}