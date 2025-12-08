using UnityEngine;
using UnityEngine.UI;

public class CharacterPresenter : MonoBehaviour
{
    [Header("UI Components")]
    [SerializeField] private Image characterImage;
    [SerializeField] private GameObject bubbleRoot;
    [SerializeField] private Text nameText;
    [SerializeField] private Text contentText;

    [Header("Settings")]
    public string characterId; // e.g., "tang_mengqi"

    public void Show(string text, string displayName = "")
    {
        gameObject.SetActive(true);
        if (bubbleRoot != null) bubbleRoot.SetActive(true);
        
        if (contentText != null) contentText.text = text;
        
        // If displayName is provided, update it. Otherwise keep prefab default or ignore.
        if (nameText != null && !string.IsNullOrEmpty(displayName))
        {
            nameText.text = displayName;
        }
    }

    public void Hide()
    {
        gameObject.SetActive(false);
    }

    public void UpdateText(string text)
    {
        if (contentText != null) contentText.text = text;
    }
}
