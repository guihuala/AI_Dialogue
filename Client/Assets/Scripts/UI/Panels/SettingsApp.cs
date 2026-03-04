using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class SettingsApp : MonoBehaviour
{
    [Header("UI Sliders / Toggles")]
    public Slider textSpeedSlider;
    public Slider bgmVolumeSlider;
    public Slider sfxVolumeSlider;
    public Toggle fullscreenToggle;

    [Header("API Controls")]
    public InputField apiKeyInput;
    public Button saveButton;
    public Button resetButton;

    private void Start()
    {
        // 1. Text Speed (from DialogueSettings)
        if (textSpeedSlider != null) 
        {
            textSpeedSlider.value = DialogueSettings.TextSpeedMultiplier;
            textSpeedSlider.onValueChanged.AddListener(OnTextSpeedChanged);
        }

        // 2. Audio (From AudioManager / PlayerPrefs)
        if (bgmVolumeSlider != null) 
        {
            bgmVolumeSlider.value = AudioManager.Instance != null ? AudioManager.Instance.bgmVolumeFactor : 0.8f;
            bgmVolumeSlider.onValueChanged.AddListener(ChangeBgmVolume);
        }

        if (sfxVolumeSlider != null)
        {
            sfxVolumeSlider.value = AudioManager.Instance != null ? AudioManager.Instance.sfxVolumeFactor : 0.8f;
            sfxVolumeSlider.onValueChanged.AddListener(ChangeSfxVolume);
        }

        // 3. Display
        if (fullscreenToggle != null)
        {
            fullscreenToggle.isOn = Screen.fullScreen;
            fullscreenToggle.onValueChanged.AddListener(SetFullscreen);
        }

        // 4. API
        if (apiKeyInput != null)
        {
            apiKeyInput.text = PlayerPrefs.GetString("APIKey", "");
        }

        if (saveButton != null) saveButton.onClick.AddListener(SaveSettings);
        if (resetButton != null) resetButton.onClick.AddListener(ResetDefaultSettings);
    }

    private void OnTextSpeedChanged(float val)
    {
        DialogueSettings.TextSpeedMultiplier = val;
    }

    private void ChangeBgmVolume(float val)
    {
        if (AudioManager.Instance != null) AudioManager.Instance.ChangeBgmVolume(val);
    }

    private void ChangeSfxVolume(float val)
    {
        if (AudioManager.Instance != null) AudioManager.Instance.ChangeSfxVolume(val);
    }

    private void SetFullscreen(bool isFullscreen)
    {
        Screen.fullScreen = isFullscreen;
    }

    private void SaveSettings()
    {
        if (apiKeyInput != null)
        {
            PlayerPrefs.SetString("APIKey", apiKeyInput.text);
        }

        if (AudioManager.Instance != null)
        {
            PlayerPrefs.SetFloat("BgmVolumeFactor", AudioManager.Instance.bgmVolumeFactor);
            PlayerPrefs.SetFloat("SfxVolumeFactor", AudioManager.Instance.sfxVolumeFactor);
        }

        PlayerPrefs.Save();
        Debug.Log("[SettingsApp] Saved to PlayerPrefs!");
        
        if (PhoneManager.Instance != null) PhoneManager.Instance.GoToHome();
    }

    private void ResetDefaultSettings()
    {
        DialogueSettings.ResetToDefaults();
        if (textSpeedSlider != null) textSpeedSlider.value = DialogueSettings.TextSpeedMultiplier;

        if (bgmVolumeSlider != null) bgmVolumeSlider.value = 0.8f;
        if (sfxVolumeSlider != null) sfxVolumeSlider.value = 0.8f;
        ChangeBgmVolume(0.8f);
        ChangeSfxVolume(0.8f);
    }
}
