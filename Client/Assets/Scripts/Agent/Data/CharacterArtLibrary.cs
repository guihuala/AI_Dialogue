using System.Collections.Generic;
using UnityEngine;
using System.Linq;

[CreateAssetMenu(fileName = "CharacterArtLibrary", menuName = "Game/Character Art Library")]
public class CharacterArtLibrary : ScriptableObject
{
    public List<CharacterData> characters;
    
    public CharacterData GetCharacter(string identifier)
    {
        if (string.IsNullOrEmpty(identifier)) return null;
        
        string lowerId = identifier.ToLower();
        
        // 优先匹配ID，如果ID不匹配，再尝试匹配 displayName(中文名)
        return characters.FirstOrDefault(c => 
            c.id.ToLower() == lowerId || 
            c.displayName.ToLower() == lowerId || 
            c.displayName.Contains(identifier)); 
    }
}