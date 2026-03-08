using System.Collections.Generic;
using UnityEngine;

[CreateAssetMenu(fileName = "NewDialogueSequence", menuName = "GameConfig/Dialogue Sequence SO")]
public class DialogueSequence : ScriptableObject
{
    [Header("固定对话序列")]
    public List<DialogueTurn> sequence = new List<DialogueTurn>();
}