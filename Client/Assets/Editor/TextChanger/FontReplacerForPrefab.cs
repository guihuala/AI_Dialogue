using UnityEditor;
using UnityEngine;
using UnityEngine.UI;

public class FontReplacerForPrefab : EditorWindow
{
    private Font sourceFont;
    private Font targetFont;

    [MenuItem("Tools/GuiTools/替换预制体的所有字体")]
    public static void OpenFontReplacer()
    {
        GetWindow<FontReplacerForPrefab>("替换预制体的所有字体");
    }

    private void OnGUI()
    {
        GUILayout.Label("替换预制体的所有字体", EditorStyles.boldLabel);

        GUILayout.Space(10);

        sourceFont = (Font)EditorGUILayout.ObjectField("被替换字体", sourceFont, typeof(Font), false);
        targetFont = (Font)EditorGUILayout.ObjectField("替换字体", targetFont, typeof(Font), false);

        GUILayout.Space(20);

        if (GUILayout.Button("替换"))
        {
            ReplaceFontsInPrefabs();
        }
    }

    private void ReplaceFontsInPrefabs()
    {
        if (sourceFont == null || targetFont == null)
        {
            Debug.LogError("Please specify both source and target fonts.");
            return;
        }

        string[] prefabPaths = AssetDatabase.FindAssets("t:Prefab");

        foreach (string prefabPath in prefabPaths)
        {
            string path = AssetDatabase.GUIDToAssetPath(prefabPath);
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);

            if (prefab == null) continue;

            bool hasChanges = false;
            
            Text[] textComponents = prefab.GetComponentsInChildren<Text>(true);
            foreach (Text textComponent in textComponents)
            {
                if (textComponent.font == sourceFont)
                {
                    textComponent.font = targetFont;
                    hasChanges = true;
                    Debug.Log($"Updated font in {prefab.name}: {textComponent.name}");
                }
            }

            if (hasChanges)
            {
                PrefabUtility.SavePrefabAsset(prefab);
            }
        }
    }
}