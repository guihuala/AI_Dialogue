# Unity Core Framework 使用说明文档

## 1\. 简介

本框架提供了一套轻量级、高性能的游戏核心管理系统，旨在解决游戏开发中常见的生命周期管理、资源复用、事件解耦和场景切换问题。

**主要模块：**

* **ObjectPool**: 高性能对象池（零 GC 复用）。
* **MsgCenter**: 基于 int Key 的消息发布/订阅系统。
* **GameManager**: 游戏流程状态机。
* **SceneLoader**: 带有过渡动画的异步场景加载器。
* **TimeManager**: 时间流速控制。

-----

## 2\. 核心模块详解

### 2.1 ObjectPool (对象池系统) - [已优化]

用于管理高频生成的游戏对象（如子弹、特效、敌人），避免频繁 `Instantiate/Destroy` 带来的 CPU 开销和内存碎片。

**优化特性：**

* **零 GC 运行**：移除了字符串操作，对象名称在生成时一次性处理。
* **层级缓存**：内部缓存父节点 Transform，不再使用 `GameObject.Find`，大幅提升获取速度。
* **自动归位**：回收对象时自动归类到对应的子节点下，保持 Hierarchy 整洁。

#### API 使用方法：

**1. 获取对象 (代替 Instantiate)**

```csharp
// 这里的 prefab 可以是任何 GameObject
GameObject bullet = ObjectPool.Instance.GetObject(bulletPrefab);
bullet.transform.position = muzzle.position;
bullet.transform.rotation = muzzle.rotation;
```

**2. 回收对象 (代替 Destroy)**

```csharp
ObjectPool.Instance.PushObject(bullet);
```

**3. 自动回收脚本 (`PushSelfBase`)**
挂载在需要自动回收的 Prefab 上（如爆炸特效、临时的子弹）。

* **注意**：由于对象是复用的，**必须使用 `OnEnable` 重置状态**，不要使用 `Start`。
* **设置**：在 Inspector 中调整 `Life Time` 即可。

<!-- end list -->

```csharp
// PushSelfBase.cs 使用示例
private void OnEnable() 
{
    // 重置逻辑写在这里，例如：
    timer = 0f;
    isPushed = false;
    rb.velocity = Vector3.zero; // 如果有刚体
}
```

-----

### 2.2 MsgCenter (消息中心)

基于观察者模式的全局事件总线，使用 `int` 代替 `string` 作为事件 Key，性能更佳。

#### 配置：

在 `MsgConst.cs` 中定义常量，避免魔法数字。

```csharp
// MsgConst.cs
public class MsgConst
{
    public const int GameStart = 1001;
    public const int PlayerDead = 1002;
    public const int ScoreChanged = 1003;
}
```

#### API 使用方法：

**1. 发送消息 (Send)**

```csharp
// 无参数
MsgCenter.SendMsgAct(MsgConst.PlayerDead);

// 有参数 (params object[])
MsgCenter.SendMsg(MsgConst.ScoreChanged, 100, "Bonus");
```

**2. 监听消息 (Register)**
建议在 `Awake` 或 `Start` 中注册。

```csharp
void Start()
{
    // 注册无参事件
    MsgCenter.RegisterMsgAct(MsgConst.PlayerDead, OnPlayerDead);
    
    // 注册有参事件
    MsgCenter.RegisterMsg(MsgConst.ScoreChanged, OnScoreChanged);
}

// 对应回调
void OnPlayerDead() { ... }
void OnScoreChanged(params object[] args) 
{
    int score = (int)args[0];
    string type = (string)args[1];
}
```

**3. 移除监听 (Unregister)**
**重要**：务必在 `OnDestroy` 中注销，防止内存泄漏或空引用报错。

```csharp
void OnDestroy()
{
    MsgCenter.UnregisterMsgAct(MsgConst.PlayerDead, OnPlayerDead);
    MsgCenter.UnregisterMsg(MsgConst.ScoreChanged, OnScoreChanged);
}
```

-----

### 2.3 GameManager (游戏总控)

管理游戏的全局状态（运行、暂停、结束）。

* **状态枚举**：`Playing`, `Paused`, `GameOver`
* **功能**：
    * `StartGame()`: 开始游戏流程。
    * `PauseGame()`: 暂停游戏（自动设置 TimeScale 为 0，呼出 UI）。
    * `ResumeGame()`: 恢复游戏。
    * `ReturnToMainMenu()`: 重置状态并加载主菜单场景。

-----

### 2.4 SceneLoader (场景加载器)

提供平滑的场景切换体验，包含淡入淡出动画和进度条。

* **Setup**：确保场景中存在 `SceneLoader` 单例，并且 Inspector 中引用了 Loading UI (CanvasGroup, Image, Text)。
* **API**：

<!-- end list -->

```csharp
// 加载枚举中定义的场景
SceneLoader.Instance.LoadScene(GameScene.Gameplay, () => {
    Debug.Log("加载完成回调");
});

// 重新加载当前关卡
SceneLoader.Instance.ReloadCurrentScene();
```

-----

### 2.5 TimeManager (时间管理)

控制游戏的全局时间流速。

* **IsPaused**: 获取当前是否暂停。
* **TimeFactor**: 获取当前时间倍率。
* **API**：

<!-- end list -->

```csharp
// 开启 "子弹时间" (0.1 倍速)
TimeManager.Instance.SetTimeFactor(0.1f);

// 恢复正常速度
TimeManager.Instance.SetTimeFactor(1f);
```

*(注：请确保 TimeManager 中的 Update 逻辑已修复为 `Time.timeScale = TimeFactor`)*

-----

## 3\. 快速集成指南

1.  **场景搭建**：

    * 创建一个名为 `_App` 或 `Managers` 的初始场景或预制体。
    * 挂载 `GameManager`, `ObjectPool`, `TimeManager`, `MsgCenter`。
    * 挂载 `SceneLoader` 并赋值 UI 组件（进度条 Image、Loading 面板 CanvasGroup）。

2.  **对象池准备**：

    * 制作子弹或特效的 Prefab。
    * 挂载 `PushSelfBase` 脚本。
    * 设置 `Life Time` (例如 3秒)。

3.  **脚本调用**：

    * 在角色攻击脚本中，将 `Instantiate(bullet)` 替换为 `ObjectPool.Instance.GetObject(bullet)`。
    * 在 UI 脚本中，通过 `MsgCenter` 监听 `MsgConst.ScoreChanged` 来更新分数显示。

-----

**文档版本**：1.0
**更新日期**：2025-11-23