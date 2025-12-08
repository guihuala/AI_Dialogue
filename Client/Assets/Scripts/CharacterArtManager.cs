using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class CharacterArtManager : MonoBehaviour
{
    [System.Serializable]
    public class CharacterArt
    {
        public string characterId; // Matches the ID in candidates.json (e.g., "tang_mengqi")
        public Sprite defaultSprite;
        // Add more expressions here if needed, e.g., public Sprite happySprite;
    }

    [SerializeField] private List<CharacterArt> characterArts;
    [SerializeField] private Image characterDisplayImage; // The UI Image component to show the sprite

    public void SetCharacter(string characterId)
    {
        if (characterDisplayImage == null) return;

        var art = characterArts.Find(x => x.characterId == characterId);
        if (art != null && art.defaultSprite != null)
        {
            characterDisplayImage.sprite = art.defaultSprite;
            characterDisplayImage.gameObject.SetActive(true);
            
            // Optional: Set native size or preserve aspect ratio
            // characterDisplayImage.SetNativeSize(); 
        }
        else
        {
            // Hide if no sprite found (or if it's the player/narrator)
            characterDisplayImage.gameObject.SetActive(false);
        }
    }

    public void HideCharacter()
    {
        if (characterDisplayImage != null)
            characterDisplayImage.gameObject.SetActive(false);
    }
}
