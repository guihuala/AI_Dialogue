# 模组系统说明

本文档说明当前项目中“默认模组 / 私有模组 / 公共模组 / 下载副本 / 派生作品”的实现状态、规则。

## 系统设计

### 默认模组

- 系统内置内容
- 只读
- 不可删除
- 不可直接覆盖保存
- 想修改时，必须先另存为私有模组

### 私有模组

- 存在于个人库中
- 仅当前玩家可编辑、删除、使用
- 可以在开局时选择
- 可以首次公开到工坊

### 公共模组

- 对所有玩家可见
- 本质上仍归原作者所有
- 只有原作者能更新公共版本
- 其他玩家只能下载为自己的私有副本

### 下载副本

- 从工坊下载到个人库的私有副本
- 后续改动只影响自己
- 不会反向覆盖原作者公共模组
- 如果再次公开，应作为派生作品处理

### 派生作品

- 基于下载副本再次公开形成的新作品
- 不覆盖原作者作品
- 会记录来源作品 id

## 当前规则

### 开局选择规则

- 模组只在“开始新游戏”时真正生效
- 局外不能直接热切换模组
- 模组中心中的“模组”是资产，不是即时运行态

### 编辑规则

- 编辑器只编辑当前选中的“编辑目标”
- 编辑目标由 `editor_mod_id / editor_source` 记录
- 开局实际使用的模组由 `active_mod_id / active_source` 记录
- 这两组状态已经拆开，避免“正在编辑哪个模组”和“这局游戏加载哪个模组”混淆

### 发布规则

- `publish_create`
  用于私有原创模组的首次公开
- `publish_update`
  用于原作者更新自己已经公开的模组
- `publish_fork`
  用于下载副本再次公开为新的派生作品

### 所有权规则

- 默认模组：任何人都不能直接写
- 私有模组：只有拥有者能编辑和删除
- 公共模组：所有人可见，但只有原作者能更新
- 下载副本：只属于下载者自己
- 派生作品：属于派生作者，不属于原作者

## 前端

### 模组中心

位置：

- `WebClient/src/components/ModManager.tsx`

当前已支持：

- 我的库 / 创意工坊切换
- 搜索
- 筛选
  - 我的库：全部、原创、下载副本、已公开
  - 工坊：全部、原创、派生、我的作品
- 排序
  - 我的库：最近更新、名称
  - 工坊：最近更新、下载量、名称
- 默认模组只读卡片
- 工坊详情弹窗
- 模组概要
- 自动类型标签
  - 偏角色向
  - 偏剧情向
  - 偏系统向

### 编辑器

位置：

- `WebClient/src/components/PromptEditor.tsx`
- `WebClient/src/components/editor/EditorModals.tsx`

当前已支持：

- 默认模组只读
- 私有模组可编辑
- 发布弹窗根据当前模组状态自动识别：
  - 首次公开
  - 更新公开版本
  - 发布为派生作品

## 后端

主要接口位于：

- `Server/src/routers/content_router.py`
- `Server/src/routers/admin_router.py`

当前关键接口：

- `POST /api/library/save_current`
- `GET /api/library/list`
- `POST /api/library/edit/{item_id}`
- `DELETE /api/library/{item_id}`
- `POST /api/editor/default`
- `POST /api/workshop/download/{item_id}`
- `GET /api/workshop/list`
- `POST /api/workshop/publish_create`
- `POST /api/workshop/publish_update`
- `POST /api/workshop/publish_fork`

兼容保留：

- `POST /api/workshop/publish_current`

## 相关文件

前端：

- `WebClient/src/components/ModManager.tsx`
- `WebClient/src/components/PromptEditor.tsx`
- `WebClient/src/components/editor/EditorModals.tsx`
- `WebClient/src/api/gameApi.ts`

后端：

- `Server/src/routers/content_router.py`
- `Server/src/routers/admin_router.py`
- `Server/src/services/state_service.py`
