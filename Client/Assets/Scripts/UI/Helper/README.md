# SimpleUITips 使用说明文档

## 1\. 简介

**SimpleUITips** 是一个轻量级的 Unity UI 反馈系统。它集成了常见的游戏 UI 提示功能，包括世界坐标飘字、交互气泡、头顶图标、屏幕固定位置提示以及圆形进度条。

**核心特点：**

* **统一管理**：通过 `UIHelper` 单例统一调用，无需在各个脚本中引用具体的 UI 对象。
* **坐标转换**：内置世界坐标转 UI 坐标逻辑，支持屏幕跟随。
* **智能排序**：交互气泡支持根据与 Player 的距离自动排序显示。
* **防刷屏机制**：飘字提示包含“快速替换”逻辑，防止短时间内大量飘字遮挡视线。

-----

## 2\. 环境搭建

1.  **场景设置**：

   * 确保场景中有一个 `Canvas`。
   * 创建一个空物体（例如命名为 `UIMgr`），挂载 `UIHelper` 脚本。
   * 确保 `UIHelper` 的 `Awake` 能够正常运行（代码中使用了 `Singleton<UIHelper>`，请确保项目中已有单例基类）。

2.  **资源赋值**：

   * 在 `UIHelper` Inspector 面板中，需要分别赋值对应的 **Prefab**：
      * `BubblePrefab` (气泡)
      * `TipPrefab` (飘字)
      * `SignPrefab` (图标)
      * `FixedPosTextPrefab` (固定位置文本)
      * `CircleProgressPrefab` (圆形进度条)

-----

## 3\. 功能模块与 API 参考

### 3.1 飘字提示 (Tip)

用于显示伤害数值、获得物品提示等。具有向上飘动并缩放消失的动画。

* **特性**：如果短时间内（`QuickReplaceThreshold`）连续并在同一位置触发，会直接重置当前飘字内容，而不是生成新的，避免重叠混乱。
* **调用方式**：
  ```csharp
  // 参数：显示内容, 世界坐标, (可选)停留时间
  var tipInfo = new TipInfo("获得金币 +100", transform.position, 1.0f);
  UIHelper.Instance.ShowTip(tipInfo);
  ```

### 3.2 交互气泡 (Bubble)

用于 NPC 对话、物品交互提示（如 "按 F 拾取"）。

* **特性**：
   * 支持多气泡管理，但界面上同一时间通常只显示一个（最近的一个）。
   * 自动根据 `BubbleInfo` 中定义的 `creator` 和 `player` 的距离进行排序，优先显示距离 Player 最近的气泡。
* **调用方式**：
  ```csharp
  // 1. 添加气泡
  List<string> keys = new List<string> { "F" };
  // 参数：按键列表, 气泡拥有者, 玩家对象, 描述内容, 物品名称
  var info = new BubbleInfo(keys, this.gameObject, playerGameObject, "拾取", "生锈的铁剑");
  UIHelper.Instance.AddBubble(info);

  // 2. 更新气泡内容 (例如状态改变)
  UIHelper.Instance.UpdateBubbleContent(this.gameObject, "无法拾取");

  // 3. 移除气泡 (通常在 OnTriggerExit 或物体销毁时)
  UIHelper.Instance.RemoveBubble(this.gameObject);
  ```

### 3.3 头顶图标 (Sign)

用于显示任务标记、状态图标（如感叹号、问号）。

* **特性**：跟随目标物体移动，到达时间后自动销毁。
* **调用方式**：
  ```csharp
  // 参数：图标路径(Resources下), 跟随的目标物体, 显示时长
  var signInfo = new SignInfo("Icons/QuestMark", npcGameObject, 5.0f);
  UIHelper.Instance.ShowSign(signInfo);
  ```

### 3.4 固定位置文本 (FixedPos)

用于显示屏幕中央的公告、任务完成提示、或者屏幕角落的状态更新。

* **支持位置**：`Left`, `Right`, `Top`, `Bottom`, `Center`。
* **调用方式**：
  ```csharp
  // 参数：位置枚举, 文本内容, 显示时长
  UIHelper.Instance.ShowFixedText(FixedUIPosType.Center, "任务完成！", 2.0f);
  ```

### 3.5 圆形进度条 (Progress)

用于显示读条动作（如开启宝箱、采集）。

* **模式**：
   * `Auto`：自动根据时长走完进度，结束后自动销毁。
   * `Manual`：需要代码手动更新进度值。
* **调用方式**：
  ```csharp
  // 1. 自动模式：显示一个跟随玩家的读条，3秒后完成
  UIHelper.Instance.ShowCircleProgress("OpeningChest", CircleProgressType.Auto, playerGo, 3.0f);

  // 2. 手动模式：
  UIHelper.Instance.ShowCircleProgress("Charging", CircleProgressType.Manual, playerGo);
  // 在 Update 中更新
  UIHelper.Instance.SetCircleProgress01("Charging", currentVal / maxVal);

  // 3. 销毁 (手动模式或提前打断时使用)
  UIHelper.Instance.DestroyCircleProgress("OpeningChest");
  ```

-----

## 4\. Prefab 制作规范

为了让脚本正常工作，请按照以下结构制作 Prefab：

| Prefab 类型 | 挂载脚本 | 必须组件/子节点 | 说明 |
| :--- | :--- | :--- | :--- |
| **Tip (飘字)** | `UITipItem` | `ContentText` (Text) | 根节点建议设置为不可见或缩放为0，脚本会接管动画。 |
| **Bubble (气泡)** | `UIBubbleItem` | `ContentText` (Text)<br>`KeyText` (Text)<br>`ItemNameText` (Text) | `KeyText` 用于显示 "E", "Space" 等按键提示。 |
| **Sign (图标)** | `UISignItem` | `IconImg` (Image) | `OffsetY` 参数可在 Inspector 中调整图标的垂直偏移量。 |
| **FixedPos (固定文本)** | `UIFixedPosTextItem` | `ContentText` (Text) | 根节点的锚点建议设为中心，脚本会根据 Type 修改位置。 |
| **Progress (进度条)** | `UICommonProgressItem` | `ProgressBarImage` (Image) | **重要**：Image Type 必须设置为 `Filled` (Radial 360)，以便脚本控制 `fillAmount`。 |

-----

## 5\. 扩展与维护建议

1.  **UIConvert 相机适配**：

   * 目前的 `UIConvert.GetUICamera` 逻辑兼容了 ScreenSpace-Camera 和 WorldSpace 模式。如果你的 Canvas 是 Overlay 模式，请确保该方法返回 `null` 或者根据项目实际情况调整，否则坐标转换可能会有偏差。

2.  **对象池 (Optimization)**：

   * 目前的实现大多使用 `Instantiate` 和 `Destroy`。如果游戏中有高频的战斗飘字（Tip），建议接入对象池（Object Pool）系统，修改 `UIHelper.ShowTip` 中的实例化逻辑，以减少 GC 压力。

3.  **Sorting 优化**：

   * `UIHelper.SortBubbleByDistance` 目前需要外部手动调用（或者在 Add 时自动调用）。如果 Player 移动较快，建议在 `UIHelper` 的 `Update` 中低频（如每0.5秒）检测一次排序，以实时刷新最近的气泡。

-----

**文档版本**：1.0
**最后更新**：2025-11-23