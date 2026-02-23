using System.Collections.Generic;
using UnityEngine;

[CreateAssetMenu(fileName = "NewFixedDialogue", menuName = "Game/Fixed Dialogue")]
public class FixedDialogueData : ScriptableObject
{
    [Header("固定剧情序列")]
    public List<DialogueTurn> sequence;
}