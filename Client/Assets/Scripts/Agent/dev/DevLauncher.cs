using UnityEngine;
using System.Diagnostics;
using System.IO;

public class DevLauncher : MonoBehaviour
{
    [Header("Path Configuration (Mac Only)")]
    // 填入你的 Server 文件夹的绝对路径 (不带末尾的 /)
    // 例如: /Users/xuzi/Downloads/AI_Dialogue/Server
    [SerializeField] private string serverRootPath = "/Users/xuzi/Downloads/AI_Dialogue/Server"; 
    
    // 填入你的虚拟环境 Python 可执行文件路径
    // 例如: /Users/xuzi/Downloads/AI_Dialogue/.venv/bin/python
    [SerializeField] private string pythonPath = "/Users/xuzi/Downloads/AI_Dialogue/.venv/bin/python";

    void Start()
    {
        // 仅在编辑器模式下运行，打包后不执行
#if UNITY_EDITOR && UNITY_STANDALONE_OSX
        LaunchBackendOnMac();
#endif
    }

    private void LaunchBackendOnMac()
    {
        string scriptPath = Path.Combine(serverRootPath, "src/app.py");
        
        // 检查文件是否存在
        if (!File.Exists(scriptPath))
        {
            UnityEngine.Debug.LogError($"找不到后端脚本: {scriptPath}");
            return;
        }

        ProcessStartInfo startInfo = new ProcessStartInfo();
        startInfo.FileName = "osascript"; // 调用 AppleScript
        
        // 组合命令：
        // 1. tell application "Terminal" -> 呼叫终端
        // 2. do script "..." -> 执行命令
        // 3. cd 到目录 && 运行 python
        string cmd = $"cd '{serverRootPath}' && '{pythonPath}' '{scriptPath}'";
        string appleScript = $"tell application \"Terminal\" to do script \"{cmd}\"";
        
        startInfo.Arguments = $"-e \"{appleScript}\"";
        startInfo.UseShellExecute = false;
        startInfo.CreateNoWindow = true;

        try 
        {
            Process.Start(startInfo);
            UnityEngine.Debug.Log("已发送指令启动 Python 后端终端...");
        }
        catch (System.Exception e)
        {
            UnityEngine.Debug.LogError($"启动失败: {e.Message}");
        }
    }
}