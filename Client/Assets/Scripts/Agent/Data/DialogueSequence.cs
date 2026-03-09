using System.Collections.Generic;
using UnityEngine;

[CreateAssetMenu(fileName = "NewDialogueSequence", menuName = "Game/Dialogue Sequence")]
public class DialogueSequence : ScriptableObject
{
    [Header("固定对话序列")]
    public List<DialogueTurn> sequence = new List<DialogueTurn>();
}