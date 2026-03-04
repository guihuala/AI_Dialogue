using UnityEngine;
using UnityEngine.UI;

public class TitleUIController : MonoBehaviour
{
    public Button continueButton;
    public Button startButton;
    public Button settingsButton;
    public Button exitButton;

    private void Start()
    {
        if (continueButton != null)
        {
            // If there's save data, show the continue button, otherwise hide it
            bool hasSave = PlayerPrefs.GetInt("HasSaveData", 0) == 1;
            continueButton.gameObject.SetActive(hasSave);
            continueButton.onClick.AddListener(OnContinueButtonClicked);
        }

        if (startButton != null) startButton.onClick.AddListener(OnStartButtonClicked);
        if (settingsButton != null) settingsButton.onClick.AddListener(OnSettingsButtonClicked);
        if (exitButton != null) exitButton.onClick.AddListener(OnExitButtonClicked);
    }
    
    public void OnStartButtonClicked()
    {
        // New Game -> Clear save flag
        PlayerPrefs.SetInt("HasSaveData", 0);
        PlayerPrefs.Save();
        UIManager.Instance.OpenPanel("CharacterSelectionPanel");
    }

    public void OnContinueButtonClicked()
    {
        // Continue Game -> Set routing flag so GameManager loads progress
        PlayerPrefs.SetInt("IsContinuingGame", 1);
        PlayerPrefs.Save();
        SceneLoader.Instance.LoadScene(GameScene.Gameplay);
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