using UnityEngine;
using UnityEditor;
using System.IO;
using System.Text.RegularExpressions;
using System.Collections.Generic;

[CustomEditor(typeof(DialogueSequence))]
public class DialogueSequenceImporter : Editor
{
    public override void OnInspectorGUI()
    {
        // 绘制原本的面板
        base.OnInspectorGUI();

        DialogueSequence sequenceSO = (DialogueSequence)target;

        GUILayout.Space(15);
        GUI.backgroundColor = Color.green;
        if (GUILayout.Button("一键导入剧本文本 (.txt)", GUILayout.Height(35)))
        {
            ImportFromText(sequenceSO);
        }
        GUI.backgroundColor = Color.white;
    }

    private void ImportFromText(DialogueSequence sequenceSO)
    {
        // 弹出文件选择框，选择纯文本文件
        string path = EditorUtility.OpenFilePanel("选择剧本文件", "", "txt");
        if (string.IsNullOrEmpty(path)) return;

        // 记录撤销操作，防止误覆盖
        Undo.RecordObject(sequenceSO, "Import Dialogue Sequence");

        sequenceSO.sequence.Clear();

        string[] lines = File.ReadAllLines(path);
        
        // 正则匹配：提取方括号内的名字，和方括号后面的台词
        // 匹配类似于: [旁白] 这是一段台词 
        // 匹配类似于: [微信 - 唐梦琪] "你好啊"
        Regex regex = new Regex(@"^\[(.*?)\]\s*(.*)");

        int importedCount = 0;

        foreach (string line in lines)
        {
            if (string.IsNullOrWhiteSpace(line)) continue;

            Match match = regex.Match(line.Trim());
            if (match.Success)
            {
                string speaker = match.Groups[1].Value.Trim();
                string content = match.Groups[2].Value.Trim();

                // 简单的清理：如果策划在台词外围加了双引号，可以选择性去掉
                if (content.StartsWith("\"") && content.EndsWith("\""))
                {
                    content = content.Substring(1, content.Length - 2);
                }

                sequenceSO.sequence.Add(new DialogueTurn
                {
                    speaker = speaker,
                    content = content,
                    mood = "平静" // 默认情绪，可在面板上再手动微调
                });
                
                importedCount++;
            }
            else
            {
                Debug.LogWarning($"[剧本导入警告] 无法解析此行格式，已跳过：\n{line}");
            }
        }

        // 标记该 SO 已修改，确保 Unity 会保存数据
        EditorUtility.SetDirty(sequenceSO);
        AssetDatabase.SaveAssets();

        Debug.Log($"<color=green>[剧本导入成功]</color> 共导入 {importedCount} 条对话到 {sequenceSO.name}！");
    }
}