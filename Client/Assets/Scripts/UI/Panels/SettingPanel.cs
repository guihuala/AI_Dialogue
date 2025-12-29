using System.Collections.Generic;
using SimpleUITips;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.SceneManagement;

public class SettingsPanel : BasePanel
{
    [Header("通用组件 - 音频")]
    public Slider bgmVolumeSlider;
    public Slider sfxVolumeSlider;

    [Header("通用组件 - 视频")]
    public Dropdown resolutionDropdown;
    public Toggle fullscreenToggle;

    [Header("通用组件 - 数据")]
    public Button clearDataButton;

    [Header("游戏内按钮 (Game Mode)")]
    public Button resumeButton;   
    public Button mainmenuButton; 

    [Header("主菜单按钮 (Menu Mode)")]
    public Button backButton;     
    public Button resetButton;    

    [Header("容器")]
    public GameObject gameButtonsContainer;
    public GameObject menuButtonsContainer;

    private bool _isGameplayMode;
    private Resolution[] _resolutions; // 缓存系统支持的分辨率列表

    private void Start()
    {
        InitAudioSettings();
        InitVideoSettings(); // 新增：初始化视频设置
        InitButtons();
    }

    public override void OpenPanel(string name)
    {
        RefreshUIState();
        base.OpenPanel(name);
    }

    private void InitAudioSettings()
    {
        bgmVolumeSlider.value = AudioManager.Instance.bgmVolumeFactor;
        sfxVolumeSlider.value = AudioManager.Instance.sfxVolumeFactor;
        
        bgmVolumeSlider.onValueChanged.AddListener(ChangeBgmVolume);
        sfxVolumeSlider.onValueChanged.AddListener(ChangeSfxVolume);
    }

    // 初始化视频设置逻辑
    private void InitVideoSettings()
    {
        // 1. 设置全屏 Toggle 状态
        if (fullscreenToggle != null)
        {
            fullscreenToggle.isOn = Screen.fullScreen;
            fullscreenToggle.onValueChanged.AddListener(SetFullscreen);
        }

        // 2. 设置分辨率 Dropdown
        if (resolutionDropdown != null)
        {
            _resolutions = Screen.resolutions;
            resolutionDropdown.ClearOptions();

            List<string> options = new List<string>();
            int currentResolutionIndex = 0;

            for (int i = 0; i < _resolutions.Length; i++)
            {
                // 构建显示的字符串，例如 "1920 x 1080"
                string option = _resolutions[i].width + " x " + _resolutions[i].height + " @" + _resolutions[i].refreshRate + "Hz";
                options.Add(option);

                // 找到当前屏幕分辨率对应的索引，以便默认选中
                if (_resolutions[i].width == Screen.width &&
                    _resolutions[i].height == Screen.height)
                {
                    currentResolutionIndex = i;
                }
            }

            resolutionDropdown.AddOptions(options);
            resolutionDropdown.value = currentResolutionIndex;
            resolutionDropdown.RefreshShownValue();

            resolutionDropdown.onValueChanged.AddListener(SetResolution);
        }
    }

    private void InitButtons()
    {
        if(resumeButton) resumeButton.onClick.AddListener(OnResumeButtonClick);
        if(mainmenuButton) mainmenuButton.onClick.AddListener(OnMainmenuButtonClick);
        if(backButton) backButton.onClick.AddListener(OnBackButtonClick);
        if(resetButton) resetButton.onClick.AddListener(OnResetButtonClick);
        
        if(clearDataButton) clearDataButton.onClick.AddListener(OnClearDataClick);
    }

    private void RefreshUIState()
    {
        string currentScene = SceneManager.GetActiveScene().name;
        // 假设主菜单场景枚举为 0 或者名字为 MainMenu
        _isGameplayMode = currentScene != GameScene.MainMenu.ToString(); 
        
        if (gameButtonsContainer != null) gameButtonsContainer.SetActive(_isGameplayMode);
        if (menuButtonsContainer != null) menuButtonsContainer.SetActive(!_isGameplayMode);
        
        if (_isGameplayMode)
        {
            GameManager.Instance.PauseGame();
        }
    }

    #region 视频控制

    public void SetResolution(int resolutionIndex)
    {
        if (_resolutions == null || resolutionIndex >= _resolutions.Length) return;
        
        Resolution resolution = _resolutions[resolutionIndex];
        // 设置分辨率，第三个参数为是否全屏
        Screen.SetResolution(resolution.width, resolution.height, Screen.fullScreen);
        
        Debug.Log($"分辨率设置为: {resolution.width} x {resolution.height}");
    }

    public void SetFullscreen(bool isFullscreen)
    {
        Screen.fullScreen = isFullscreen;
        Debug.Log($"全屏状态: {isFullscreen}");
    }

    #endregion

    #region 音量控制

    private void ChangeBgmVolume(float value)
    {
        AudioManager.Instance.ChangeBgmVolume(value);
    }

    private void ChangeSfxVolume(float value)
    {
        AudioManager.Instance.ChangeSfxVolume(value);
    }

    private void SaveSettings()
    {
        PlayerPrefs.SetFloat("MainVolume", AudioManager.Instance.mainVolume);
        PlayerPrefs.SetFloat("BgmVolumeFactor", AudioManager.Instance.bgmVolumeFactor);
        PlayerPrefs.SetFloat("SfxVolumeFactor", AudioManager.Instance.sfxVolumeFactor);
        
        // 注意：分辨率和全屏状态 Unity 会自动保存（在 Windows 注册表中），
        // 但如果需要跨设备同步，你也可以在这里手动保存分辨率 Index。
        
        PlayerPrefs.Save();
        Debug.Log("Settings Saved!");
    }

    #endregion

    #region 按钮回调
    
    private void OnClearDataClick()
    {
        // 1. 清空所有 PlayerPrefs
        PlayerPrefs.DeleteAll(); 
        PlayerPrefs.Save();
        
        Debug.Log("所有存档数据已清空！");

        // 2. 视觉反馈：重置 UI 状态到默认值
        OnResetButtonClick(); 
        
        // 3. 弹出一个飘字提示
        UIHelper.Instance.ShowFixedText(FixedUIPosType.Center, "存档已清空", 1.5f);
    }

    private void OnResumeButtonClick()
    {
        SaveSettings();
        GameManager.Instance.ResumeGame(); 
        UIManager.Instance.ClosePanel(panelName);
    }

    private void OnMainmenuButtonClick()
    {
        SaveSettings();
        GameManager.Instance.ReturnToMainMenu(); 
        UIManager.Instance.ClosePanel(panelName);
    }

    private void OnBackButtonClick()
    {
        SaveSettings();
        UIManager.Instance.ClosePanel(panelName);
    }

    private void OnResetButtonClick()
    {
        // 重置 UI 显示
        bgmVolumeSlider.value = 0.8f;
        sfxVolumeSlider.value = 0.8f;

        // 应用到底层逻辑
        AudioManager.Instance.ChangeMainVolume(1f);
        ChangeBgmVolume(0.8f);
        ChangeSfxVolume(0.8f);
    }

    #endregion
}