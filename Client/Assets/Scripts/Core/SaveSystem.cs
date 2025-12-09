using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using System.Collections.Generic;

public class SaveSystem : MonoBehaviour
{
    [Header("Configuration")]
    [SerializeField] private GameDirector gameDirector;
    [SerializeField] private LLMClient llmClient;
    [SerializeField] private string nextSceneName = "GameScene";

    [Header("UI References (Optional - for Main Menu)")]
    [SerializeField] private InputField sessionIdInput;

    public void OnStartGameClicked(string slotId)
    {
        // 1. Set Session ID
        if (string.IsNullOrEmpty(slotId)) slotId = System.Guid.NewGuid().ToString(); // New Game if empty
        
        PlayerPrefs.SetString("CurrentSessionID", slotId);
        PlayerPrefs.Save();

        // 2. Load Scene
        SceneManager.LoadScene(nextSceneName);
    }
    
    // Call this inside GameDirector.Start() to initialize the correct session
    public void InitializeSession()
    {
        string sessionId = PlayerPrefs.GetString("CurrentSessionID", "default");
        llmClient.SetSessionId(sessionId);
        Debug.Log($"Session Initialized: {sessionId}");
    }
}
