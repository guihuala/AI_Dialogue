using UnityEngine;

[CreateAssetMenu(fileName = "NewCharacter", menuName = "Game/Character Data")]
public class CharacterData : ScriptableObject
{
    public string id;
    public string displayName;
    public Sprite portrait;
    [TextArea] public string description;
}