using UnityEngine;
using UnityEngine.UI;

public class SettingsApp : MonoBehaviour
{
    [Header("Tab Buttons")]
    public Button tabGeneralBtn;
    public Button tabLLMBtn;
    public Button tabDeveloperBtn;

    [Header("Tab Panels")]
    public GameObject panelGeneral;
    public GameObject panelLLM;
    public GameObject panelDeveloper;

    [Header("1. General Settings")]
    public Slider textSpeedSlider;
    public Slider bgmVolumeSlider;
    public Slider sfxVolumeSlider;
    public Toggle fullscreenToggle;

    [Header("2. LLM Config")]
    public InputField apiKeyInput;
    public InputField baseUrlInput;
    public InputField modelNameInput;
    public Slider temperatureSlider;

    [Header("3. Developer Tools")]
    public Button rebuildKnowledgeBtn;
    public Text developerLogText;

    [Header("Global Controls")]
    public Button saveApplyBtn;
    public Button resetBtn;

    private void Start()
    {
        // --- 绑定页签切换 ---
        if (tabGeneralBtn) tabGeneralBtn.onClick.AddListener(() => SwitchTab(0));
        if (tabLLMBtn) tabLLMBtn.onClick.AddListener(() => SwitchTab(1));
        if (tabDeveloperBtn) tabDeveloperBtn.onClick.AddListener(() => SwitchTab(2));

        // --- 初始化基础设置 ---
        if (textSpeedSlider) textSpeedSlider.onValueChanged.AddListener(v => DialogueSettings.TextSpeedMultiplier = v);
        if (bgmVolumeSlider) bgmVolumeSlider.onValueChanged.AddListener(v => { if (AudioManager.Instance != null) AudioManager.Instance.ChangeBgmVolume(v); });
        if (sfxVolumeSlider) sfxVolumeSlider.onValueChanged.AddListener(v => { if (AudioManager.Instance != null) AudioManager.Instance.ChangeSfxVolume(v); });
        if (fullscreenToggle) fullscreenToggle.onValueChanged.AddListener(v => Screen.fullScreen = v);

        // --- 绑定全局按钮 ---
        if (saveApplyBtn) saveApplyBtn.onClick.AddListener(SaveAllSettings);
        if (resetBtn) resetBtn.onClick.AddListener(ResetDefaultSettings);
        
        // --- 绑定开发者按钮 ---
        if (rebuildKnowledgeBtn) rebuildKnowledgeBtn.onClick.AddListener(TriggerRebuildKnowledge);

        // 默认打开第一个页签，并加载本地存储
        SwitchTab(0);
        LoadLocalSettings();
    }

    private void SwitchTab(int index)
    {
        if (panelGeneral) panelGeneral.SetActive(index == 0);
        if (panelLLM) panelLLM.SetActive(index == 1);
        if (panelDeveloper) panelDeveloper.SetActive(index == 2);
    }

    private void LoadLocalSettings()
    {
        // 加载大模型配置缓存
        if (apiKeyInput) apiKeyInput.text = PlayerPrefs.GetString("LLM_APIKey", "");
        if (baseUrlInput) baseUrlInput.text = PlayerPrefs.GetString("LLM_BaseUrl", "https://api.deepseek.com/v1");
        if (modelNameInput) modelNameInput.text = PlayerPrefs.GetString("LLM_Model", "deepseek-chat");
        if (temperatureSlider) temperatureSlider.value = PlayerPrefs.GetFloat("LLM_Temp", 0.7f);
        
        // 加载基础设置缓存
        if (textSpeedSlider) textSpeedSlider.value = DialogueSettings.TextSpeedMultiplier;
        if (bgmVolumeSlider && AudioManager.Instance != null) bgmVolumeSlider.value = AudioManager.Instance.bgmVolumeFactor;
        if (fullscreenToggle) fullscreenToggle.isOn = Screen.fullScreen;
    }

    private void SaveAllSettings()
    {
        // 1. 保存到本地 PlayerPrefs
        PlayerPrefs.SetString("LLM_APIKey", apiKeyInput.text);
        PlayerPrefs.SetString("LLM_BaseUrl", baseUrlInput.text);
        PlayerPrefs.SetString("LLM_Model", modelNameInput.text);
        PlayerPrefs.GetFloat("LLM_Temp", temperatureSlider.value);
        if (AudioManager.Instance != null)
        {
            PlayerPrefs.SetFloat("BgmVolumeFactor", AudioManager.Instance.bgmVolumeFactor);
            PlayerPrefs.SetFloat("SfxVolumeFactor", AudioManager.Instance.sfxVolumeFactor);
        }
        PlayerPrefs.Save();

        // 2. 发送请求给后端更新大模型状态
        SettingsRequest req = new SettingsRequest {
            api_key = apiKeyInput.text,
            base_url = baseUrlInput.text,
            model_name = modelNameInput.text,
            temperature = temperatureSlider.value
        };

        // 呼叫 NetworkService 发送配置
        if (NetworkService.Instance != null)
        {
            StartCoroutine(NetworkService.Instance.UpdateSettingsCoroutine(
                req.temperature, 
                800, // 默认最大 token
                req.api_key, 
                req.base_url, 
                req.model_name,
                (res) => Debug.Log("Backend LLM Config Updated!"), 
                (err) => Debug.LogError("Failed to update backend: " + err)
            ));
        }

        Debug.Log("[SettingsApp] All Settings Saved!");
        MsgCenter.SendMsg(MsgConst.SHOW_IMMEDIATE_MESSAGE, "系统", "设置已保存并同步至服务器", Color.green);
    }

    private void TriggerRebuildKnowledge()
    {
        if (developerLogText) developerLogText.text = "正在通知服务器重载语料与剧本...";
        
        if (NetworkService.Instance != null)
        {
            StartCoroutine(NetworkService.Instance.RebuildKnowledgeCoroutine(
                (msg) => { if (developerLogText) developerLogText.text = msg; },
                (err) => { if (developerLogText) developerLogText.text = $"<color=red>重载失败: {err}</color>"; }
            ));
        }
    }

    private void ResetDefaultSettings()
    {
        DialogueSettings.ResetToDefaults();
        if (textSpeedSlider != null) textSpeedSlider.value = DialogueSettings.TextSpeedMultiplier;

        if (bgmVolumeSlider != null) bgmVolumeSlider.value = 0.8f;
        if (sfxVolumeSlider != null) sfxVolumeSlider.value = 0.8f;
        // ChangeBgmVolume(0.8f);
        // ChangeSfxVolume(0.8f);
    }
}
