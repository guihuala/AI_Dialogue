using UnityEngine;
using UnityEditor;
using System.Collections.Generic;
using System.IO;

public class UIDataEditor : EditorWindow
{
    private UIDatas targetUIDatas;
    private string searchPath = "Assets/";
    private Vector2 scrollPosition;

    [MenuItem("Tools/GuiTools/UI Manager/UIData Configurator")]
    public static void ShowWindow()
    {
        GetWindow<UIDataEditor>("UIData Configurator");
    }

    private void OnGUI()
    {
        EditorGUILayout.Space();
        EditorGUILayout.LabelField("UIData Configuration Tool", EditorStyles.boldLabel);
        EditorGUILayout.Space();

        // 选择目标 UIDatas asset
        targetUIDatas = (UIDatas)EditorGUILayout.ObjectField("Target UIDatas", targetUIDatas, typeof(UIDatas), false);

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

        EditorGUILayout.Space();

        // 操作按钮
        if (targetUIDatas == null)
        {
            EditorGUILayout.HelpBox("Please assign a UIDatas asset first.", MessageType.Warning);
            return;
        }

        if (GUILayout.Button("Scan for BasePanel Prefabs", GUILayout.Height(30)))
        {
            ScanForBasePanelPrefabs();
        }

        EditorGUILayout.Space();

        // 显示当前配置的UI数据
        if (targetUIDatas.uiDataList != null && targetUIDatas.uiDataList.Count > 0)
        {
            EditorGUILayout.LabelField("Current UI Data List:", EditorStyles.boldLabel);
            scrollPosition = EditorGUILayout.BeginScrollView(scrollPosition, GUILayout.Height(200));
            
            for (int i = 0; i < targetUIDatas.uiDataList.Count; i++)
            {
                EditorGUILayout.BeginVertical("box");
                EditorGUILayout.LabelField($"UI Name: {targetUIDatas.uiDataList[i].uiName}");
                EditorGUILayout.LabelField($"Path: {targetUIDatas.uiDataList[i].uiPath}");
                EditorGUILayout.EndVertical();
            }
            
            EditorGUILayout.EndScrollView();

            if (GUILayout.Button("Clear All Data", GUILayout.Height(25)))
            {
                if (EditorUtility.DisplayDialog("Clear All Data", 
                    "Are you sure you want to clear all UI data?", "Yes", "No"))
                {
                    targetUIDatas.uiDataList.Clear();
                    EditorUtility.SetDirty(targetUIDatas);
                    AssetDatabase.SaveAssets();
                }
            }
        }
        else
        {
            EditorGUILayout.HelpBox("No UI data configured. Click 'Scan for BasePanel Prefabs' to populate.", MessageType.Info);
        }
    }

    private void ScanForBasePanelPrefabs()
    {
        if (targetUIDatas == null)
        {
            Debug.LogError("No UIDatas asset assigned!");
            return;
        }

        // 获取所有预制件文件
        string[] prefabFiles = Directory.GetFiles(searchPath, "*.prefab", SearchOption.AllDirectories);
        List<UIData> foundPanels = new List<UIData>();

        int processedCount = 0;
        int validCount = 0;

        foreach (string filePath in prefabFiles)
        {
            string assetPath = filePath.Replace("\\", "/");
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
            
            if (prefab != null)
            {
                processedCount++;
                
                // 检查预制件是否有 BasePanel 组件
                BasePanel basePanel = prefab.GetComponent<BasePanel>();
                if (basePanel != null)
                {
                    // 创建相对路径（相对于 Resources 文件夹）
                    string resourcesRelativePath = GetResourcesRelativePath(assetPath);
                    
                    UIData uiData = new UIData
                    {
                        uiName = prefab.name,
                        uiPath = resourcesRelativePath
                    };
                    
                    foundPanels.Add(uiData);
                    validCount++;
                    
                    Debug.Log($"Found BasePanel: {prefab.name} at path: {resourcesRelativePath}");
                }
            }
        }

        // 更新 UIDatas
        targetUIDatas.uiDataList = foundPanels;
        EditorUtility.SetDirty(targetUIDatas);
        AssetDatabase.SaveAssets();

        Debug.Log($"Scan completed! Processed {processedCount} prefabs, found {validCount} BasePanel prefabs.");
        EditorUtility.DisplayDialog("Scan Complete", 
            $"Processed {processedCount} prefabs\nFound {validCount} BasePanel prefabs", "OK");
    }

    private string GetResourcesRelativePath(string fullPath)
    {
        // 查找 "Resources/" 在路径中的位置
        int resourcesIndex = fullPath.IndexOf("Resources/");
        if (resourcesIndex == -1)
        {
            Debug.LogWarning($"Prefab is not in a Resources folder: {fullPath}");
            return fullPath; // 如果不在Resources文件夹，返回完整路径
        }

        // 获取 Resources 文件夹之后的路径
        string relativePath = fullPath.Substring(resourcesIndex + "Resources/".Length);
        
        // 移除文件扩展名
        relativePath = relativePath.Replace(".prefab", "");
        
        return relativePath;
    }
}