# 前端说明

## 1. 技术栈

前端位于 `WebClient/`，核心技术如下：

- React 18
- TypeScript
- Vite
- Zustand
- Axios
- Lucide React
- Tailwind CSS v4 风格工具类

入口依赖定义见 `WebClient/package.json`。

## 2. 入口与页面组织

前端入口很简单：

- `src/main.tsx`：挂载 React 应用
- `src/App.tsx`：管理全局布局、标签页、顶部栏、侧边栏、手机浮层、加载动画等

项目当前没有使用 `react-router` 做完整声明式路由，而是通过：

- `locationToTab`
- `tabToPath`
- `activeTab`

来完成 URL 与页面标签之间的同步。当前主标签主要有：

- `game`：游戏主界面
- `mods` / `workshop`：模组中心
- `editor`：编辑器
- `settings`：系统设置
- `admin`：后台管理页

## 3. 前端模块划分

### 游戏界面

核心文件：

- `src/components/GameView.tsx`
- `src/components/GameSetup.tsx`
- `src/components/SaveSelection.tsx`
- `src/components/game/*`

这一部分负责：

- 标题菜单与开局流程
- 存档选择
- 文字展示与打字机效果
- 角色立绘切换
- 场景切换
- 历史记录显示
- 选项按钮与回合推进
- 手机界面浮层与消息提醒

其中 `GameView.tsx` 是游戏交互主容器，会把 Zustand 中的状态映射到界面上。

### 模组中心

核心文件：

- `src/components/ModManager.tsx`

负责两个概念页：

- `library`：个人模组库
- `workshop`：工坊资源列表

主要能力包括：

- 保存当前活动配置为模组
- 查看默认模组、私有模组、下载副本
- 切换当前编辑目标
- 从工坊下载模组
- 查看工坊详情弹窗
- 查看模组概要、类型标签、来源与版本
- 对个人库和工坊列表进行筛选与排序
- 回滚快照
- 查看用户状态与安全数据

当前前端语义已经调整为：

- 模组不能在局外直接应用
- 模组只会在新游戏开始时生效
- 默认模组只读，不可删除
- 公共模组详情通过弹窗查看，而不是直接在列表中展开全部信息

### Prompt/内容编辑器

核心文件：

- `src/components/PromptEditor.tsx`
- `src/components/editor/*`

这是项目很有特色的一部分，前端不只是“玩游戏”，还承担了“内容创作工具”的职责。编辑器支持：

- 世界设定编辑
- 角色管理
- 人物关系编辑
- 剧情/事件编排
- Skill 文本编辑
- 底层文件直接编辑

它通过后台接口获取和保存 `.md`、`.json`、`.csv` 文件，属于一个面向模组作者的可视化控制台。

#### “事件”与“骨架”的关系（重点）

为了避免混淆，可以按“双轨”理解：

- 事件编辑（CSV）：
  - 负责剧情素材与演出文本本身（场景、对话、传统事件池内容）。
- 骨架编辑（event_skeletons）：
  - 负责系统规则（触发条件、优先级、选项态度、状态变化、不可逆标记、关系链推进）。

执行顺序是：

- 先由骨架层决定“这回合触发什么、结算什么状态变化”；
- 再由事件/文本层把这一回合写成玩家看到的内容。

因此：

- 想改“剧情写法与具体内容”，优先改 CSV；
- 想改“什么时候触发暧昧/冲突、选项后状态怎么变”，优先改骨架。

当前编辑器还承担模组发布入口，已支持根据当前模组状态自动区分：

- 首次公开
- 更新公开版本
- 发布为派生作品

也就是说，前端已经不再把“公开”混成单一动作，而是会根据当前编辑模组的来源与公开状态自动选择合适的发布路径。

### 后台管理页

核心文件：

- `src/components/AdminDashboard.tsx`

主要用于：

- 管理员工坊资源
- 管理员登录与登出
- 查看用户状态、配额与审计日志
- 执行存储清理

管理员 token 会保存在浏览器 `localStorage` 中，并通过请求拦截器附加到 `X-Admin-Token`。

## 4. 状态管理

全局游戏状态由 `src/store/gameStore.ts` 管理，使用 Zustand 创建单一状态容器。

状态内容大致分为四类：

- 对局状态：`isPlaying`、`chapter`、`turn`、`current_evt_id`
- 主角属性：`san`、`money`、`gpa`、`hygiene`、`reputation`
- 叙事数据：`displayText`、`nextOptions`、`history`、`narrativeState`
- 设备/UI 状态：`isPhoneOpen`、`typewriterSpeed`、`audioVolume`、`uiTransparency`

同时它也封装了关键异步动作：

- `startGame`
- `performTurn`
- `saveGame`
- `loadSave`
- `prefetch`
- `resetGame`

也就是说，这个 store 不只是“存状态”，还承担了前端主要业务编排层的角色。

## 5. API 调用方式

API 封装主要在：

- `src/api/gameApi.ts`
- `src/api/settingsApi.ts`

### `gameApi.ts`

统一面向 `http://127.0.0.1:8000/api`，涵盖：

- 游戏开始、推进、预取、存档、读档
- 管理员登录与文件编辑
- 模组库与工坊操作
- 用户状态、配额、审计、快照
- 记忆管理

### `settingsApi.ts`

单独面向 `/api/system/settings`，处理模型配置读取和更新。

## 6. 数据流特点

这个项目前端有两个比较重要的特点：

#### 不是纯展示层

前端并不是只接收后端渲染结果，部分事件脚本会在本地直接解析和推进。`gameStore.ts` 中有一段“本地剧本命中后直接解析下一回合”的逻辑，用来减少延迟、提升交互流畅度。

#### 强依赖本地存储

前端会在 `localStorage` 中持久化至少两类标识：

- `visitor_id`
- `admin_token`

前者对应用户数据隔离，后者对应管理员会话。

## 7. 重要文件

建议优先阅读：

1. `WebClient/src/App.tsx`
2. `WebClient/src/store/gameStore.ts`
3. `WebClient/src/api/gameApi.ts`
4. `WebClient/src/components/GameView.tsx`
5. `WebClient/src/components/PromptEditor.tsx`
6. `WebClient/src/components/ModManager.tsx`

## 8. 开发注意点

- 前端 API 地址目前写死为本地 `127.0.0.1:8000`，部署前建议提取成环境变量。
- 页面切换是自定义标签路由，不是标准路由系统；新增页面时要同时更新标签映射。
- 编辑器、模组中心、后台管理共享大量后端资源接口，改动时要注意权限边界。
- `gameStore` 业务较重，后续如果功能继续增长，适合拆分为多个 domain store
