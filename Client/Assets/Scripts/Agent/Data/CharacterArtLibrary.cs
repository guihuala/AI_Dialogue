using System.Collections.Generic;
using UnityEngine;
using System.Linq;

[CreateAssetMenu(fileName = "CharacterArtLibrary", menuName = "Game/Character Art Library")]
public class CharacterArtLibrary : ScriptableObject
{
    public List<CharacterData> characters;
    
    public CharacterData GetCharacter(string id)
    {
        if (string.IsNullOrEmpty(id)) return null;
        
        // 在列表中查找 ID 匹配的数据
        return characters.FirstOrDefault(c => c.id.ToLower() == id.ToLower());
    }
}