using UnityEngine;
using UnityEditor;
using System.Collections.Generic;
using System.IO;

public class AudioDataEditor : EditorWindow
{
    private AudioDatas targetAudioDatas;
    private string searchPath = "Assets/";
    private Vector2 scrollPosition;
    private bool includeSubfolders = true;
    private string[] audioExtensions = new string[] { ".wav", ".mp3", ".ogg", ".aiff" };

    [MenuItem("Tools/GuiTools/Audio Manager/AudioData Configurator")]
    public static void ShowWindow()
    {
        GetWindow<AudioDataEditor>("AudioData Configurator");
    }

    private void OnGUI()
    {
        EditorGUILayout.Space();
        EditorGUILayout.LabelField("AudioData Configuration Tool", EditorStyles.boldLabel);
        EditorGUILayout.Space();

        // 选择目标 AudioDatas asset
        targetAudioDatas = (AudioDatas)EditorGUILayout.ObjectField("Target AudioDatas", targetAudioDatas, typeof(AudioDatas), false);

        EditorGUILayout.Space();
        EditorGUILayout.LabelField("Search Settings", EditorStyles.boldLabel);
        
        // 搜索路径设置
        EditorGUILayout.BeginHorizontal();
        searchPath = EditorGUILayout.TextField("Search Path", searchPath);
        if (GUILayout.Button("Browse", GUILayout.Width(60)))
        {
            string newPath = EditorUtility.OpenFolderPanel("Select Folder to Search", searchPath, "");
            if (!string.IsNullOrEmpty(newPath))
            {
                searchPath = "Assets" + newPath.Replace(Application.dataPath, "");
            }
        }
        EditorGUILayout.EndHorizontal();

        includeSubfolders = EditorGUILayout.Toggle("Include Subfolders", includeSubfolders);

        EditorGUILayout.Space();

        // 操作按钮
        if (targetAudioDatas == null)
        {
            EditorGUILayout.HelpBox("Please assign an AudioDatas asset first.", MessageType.Warning);
            return;
        }

        if (GUILayout.Button("Scan for Audio Files", GUILayout.Height(30)))
        {
            ScanForAudioFiles();
        }

        EditorGUILayout.Space();

        // 显示当前配置的音频数据
        if (targetAudioDatas.audioDataList != null && targetAudioDatas.audioDataList.Count > 0)
        {
            EditorGUILayout.LabelField($"Current Audio Data List ({targetAudioDatas.audioDataList.Count} items):", EditorStyles.boldLabel);
            
            // 搜索过滤
            EditorGUILayout.BeginHorizontal();
            EditorGUILayout.LabelField("Filter:", GUILayout.Width(40));
            string searchFilter = EditorGUILayout.TextField("", GUILayout.ExpandWidth(true));
            EditorGUILayout.EndHorizontal();

            scrollPosition = EditorGUILayout.BeginScrollView(scrollPosition, GUILayout.Height(300));
            
            int displayedCount = 0;
            for (int i = 0; i < targetAudioDatas.audioDataList.Count; i++)
            {
                var audioData = targetAudioDatas.audioDataList[i];
                
                // 应用搜索过滤
                if (!string.IsNullOrEmpty(searchFilter) && 
                    !audioData.audioName.ToLower().Contains(searchFilter.ToLower()) &&
                    !audioData.audioPath.ToLower().Contains(searchFilter.ToLower()))
                {
                    continue;
                }

                displayedCount++;
                
                EditorGUILayout.BeginVertical("box");
                
                EditorGUILayout.BeginHorizontal();
                EditorGUILayout.LabelField("Name:", GUILayout.Width(40));
                audioData.audioName = EditorGUILayout.TextField(audioData.audioName);
                EditorGUILayout.EndHorizontal();

                EditorGUILayout.BeginHorizontal();
                EditorGUILayout.LabelField("Path:", GUILayout.Width(40));
                EditorGUILayout.SelectableLabel(audioData.audioPath, EditorStyles.textField, GUILayout.Height(EditorGUIUtility.singleLineHeight));
                EditorGUILayout.EndHorizontal();

                // 预览按钮
                EditorGUILayout.BeginHorizontal();
                if (GUILayout.Button("Play Preview", GUILayout.Width(100)))
                {
                    PlayAudioPreview(audioData.audioPath);
                }
                
                if (GUILayout.Button("Remove", GUILayout.Width(60)))
                {
                    if (EditorUtility.DisplayDialog("Remove Audio Data", 
                        $"Are you sure you want to remove '{audioData.audioName}'?", "Yes", "No"))
                    {
                        targetAudioDatas.audioDataList.RemoveAt(i);
                        EditorUtility.SetDirty(targetAudioDatas);
                        AssetDatabase.SaveAssets();
                        break;
                    }
                }
                EditorGUILayout.EndHorizontal();

                EditorGUILayout.EndVertical();
            }

            if (displayedCount == 0 && !string.IsNullOrEmpty(searchFilter))
            {
                EditorGUILayout.HelpBox("No items match your search filter.", MessageType.Info);
            }
            
            EditorGUILayout.EndScrollView();

            EditorGUILayout.Space();

            if (GUILayout.Button("Clear All Data", GUILayout.Height(25)))
            {
                if (EditorUtility.DisplayDialog("Clear All Data", 
                    "Are you sure you want to clear all audio data?", "Yes", "No"))
                {
                    targetAudioDatas.audioDataList.Clear();
                    EditorUtility.SetDirty(targetAudioDatas);
                    AssetDatabase.SaveAssets();
                }
            }

            if (GUILayout.Button("Save Changes", GUILayout.Height(25)))
            {
                EditorUtility.SetDirty(targetAudioDatas);
                AssetDatabase.SaveAssets();
                EditorUtility.DisplayDialog("Save Complete", "Audio data saved successfully!", "OK");
            }
        }
        else
        {
            EditorGUILayout.HelpBox("No audio data configured. Click 'Scan for Audio Files' to populate.", MessageType.Info);
        }
    }

    private void ScanForAudioFiles()
    {
        if (targetAudioDatas == null)
        {
            Debug.LogError("No AudioDatas asset assigned!");
            return;
        }

        SearchOption searchOption = includeSubfolders ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
        List<AudioData> foundAudioFiles = new List<AudioData>();

        int processedCount = 0;
        int validCount = 0;

        // 搜索所有支持的音频文件
        foreach (string extension in audioExtensions)
        {
            string[] audioFiles = Directory.GetFiles(searchPath, "*" + extension, searchOption);
            
            foreach (string filePath in audioFiles)
            {
                string assetPath = filePath.Replace("\\", "/");
                
                // 跳过meta文件
                if (assetPath.EndsWith(".meta")) continue;

                processedCount++;
                
                // 获取相对Resources路径
                string resourcesRelativePath = GetResourcesRelativePath(assetPath);
                
                // 获取文件名（不含扩展名）
                string fileName = Path.GetFileNameWithoutExtension(assetPath);
                
                AudioData audioData = new AudioData
                {
                    audioName = fileName,
                    audioPath = resourcesRelativePath
                };
                
                foundAudioFiles.Add(audioData);
                validCount++;
                
                Debug.Log($"Found Audio: {fileName} at path: {resourcesRelativePath}");
            }
        }

        // 更新 AudioDatas
        targetAudioDatas.audioDataList = foundAudioFiles;
        EditorUtility.SetDirty(targetAudioDatas);
        AssetDatabase.SaveAssets();

        Debug.Log($"Scan completed! Processed {processedCount} files, found {validCount} audio files.");
        EditorUtility.DisplayDialog("Scan Complete", 
            $"Processed {processedCount} files\nFound {validCount} audio files", "OK");
    }

    private string GetResourcesRelativePath(string fullPath)
    {
        // 查找 "Resources/" 在路径中的位置
        int resourcesIndex = fullPath.IndexOf("Resources/");
        if (resourcesIndex == -1)
        {
            Debug.LogWarning($"Audio file is not in a Resources folder: {fullPath}");
            
            // 如果不在Resources文件夹，返回相对于Assets的路径（去掉Assets/前缀）
            if (fullPath.StartsWith("Assets/"))
            {
                return fullPath.Substring("Assets/".Length).Replace(".meta", "");
            }
            return fullPath.Replace(".meta", "");
        }

        // 获取 Resources 文件夹之后的路径
        string relativePath = fullPath.Substring(resourcesIndex + "Resources/".Length);
        
        // 移除文件扩展名
        relativePath = relativePath.Replace(".wav", "")
                                  .Replace(".mp3", "")
                                  .Replace(".ogg", "")
                                  .Replace(".aiff", "")
                                  .Replace(".meta", "");
        
        return relativePath;
    }

    private void PlayAudioPreview(string audioPath)
    {
        // 尝试加载音频剪辑
        AudioClip clip = Resources.Load<AudioClip>(audioPath);
        
        if (clip == null)
        {
            Debug.LogWarning($"无法加载音频剪辑: {audioPath}");
            EditorUtility.DisplayDialog("Preview Error", $"无法加载音频剪辑: {audioPath}", "OK");
            return;
        }
    }

    // 添加右键菜单项
    [MenuItem("Assets/Create/Audio Data from Selection", false, 100)]
    public static void CreateAudioDataFromSelection()
    {
        AudioDatas audioDatas = Selection.activeObject as AudioDatas;
        if (audioDatas == null)
        {
            Debug.LogWarning("请先选择一个AudioDatas asset");
            return;
        }

        GetWindow<AudioDataEditor>().targetAudioDatas = audioDatas;
        GetWindow<AudioDataEditor>().ScanForAudioFiles();
    }

    [MenuItem("Assets/Create/Audio Data from Selection", true)]
    public static bool ValidateCreateAudioDataFromSelection()
    {
        return Selection.activeObject is AudioDatas;
    }
}