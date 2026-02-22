using UnityEngine;
using UnityEngine.UI;

public class TitleUIController : MonoBehaviour
{
    public Button startButton;
    public Button settingsButton;
    public Button exitButton;

    private void Awake()
    {
        startButton.onClick.AddListener(OnStartButtonClicked);
        settingsButton.onClick.AddListener(OnSettingsButtonClicked);
        exitButton.onClick.AddListener(OnExitButtonClicked);
    }
    
    public void OnStartButtonClicked()
    {
        UIManager.Instance.OpenPanel("CharacterSelectionPanel");
    }

    public void OnSettingsButtonClicked()
    {
        UIManager.Instance.OpenPanel("SettingPanel");
    }

    public void OnExitButtonClicked()
    {
#if UNITY_EDITOR
        UnityEditor.EditorApplication.isPlaying = false;
#else
        Application.Quit();
#endif
    }
}