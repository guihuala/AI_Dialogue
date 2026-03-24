## **需要实现的接口：**

## 🔧 **必需的管理后台API接口**

### **1. 认证相关接口**
```
POST /api/admin/login
请求体: { "password": "string" }
响应: { "status": "success", "data": { "token": "string", "expires_at": "string", "ttl_seconds": number } }

GET /api/admin/session
请求头: X-Admin-Token: <token>
响应: { "status": "success", "data": { "token": "string", "expires_at": "string", "ttl_seconds": number } }

POST /api/admin/logout
请求头: X-Admin-Token: <token>
响应: { "status": "success" }
```

### **2. 用户管理接口**
```
GET /api/admin/users
请求头: X-Admin-Token: <token>
查询参数: q=搜索词, page=页码, page_size=每页数量, sort_by=排序字段, sort_order=排序方向
响应: { "status": "success", "data": [用户列表], "pagination": 分页信息 }

GET /api/admin/users/stats
请求头: X-Admin-Token: <token>
响应: { "status": "success", "data": { "total_accounts": 总数, "active_sessions": 活跃会话等 } }
```

### **3. 文件管理接口**
```
GET /api/admin/files
请求头: X-Admin-Token: <token>
响应: { "status": "success", "md": [markdown文件列表], "csv": [csv文件列表] }

GET /api/admin/file
请求头: X-Admin-Token: <token>
查询参数: type=文件类型(md/csv), name=文件名
响应: { "status": "success", "content": "文件内容" }

POST /api/admin/file
请求头: X-Admin-Token: <token>
请求体: { "type": "md/csv", "name": "文件名", "content": "文件内容" }
响应: { "status": "success", "message": "保存成功" }
```

### **4. 预设模组管理**
```
GET /api/admin/preset/mods
请求头: X-Admin-Token: <token>
响应: { "status": "success", "data": [预设模组列表] }

GET /api/admin/preset/files
请求头: X-Admin-Token: <token>
查询参数: target=default/preset, mod_id=模组ID
响应: { "status": "success", "md": [文件列表], "csv": [文件列表] }

GET /api/admin/preset/file
请求头: X-Admin-Token: <token>
查询参数: target=default/preset, mod_id=模组ID, type=文件类型, name=文件名
响应: { "status": "success", "content": "文件内容" }

POST /api/admin/preset/file
请求头: X-Admin-Token: <token>
请求体: { "target": "default/preset", "mod_id": "模组ID", "type": "文件类型", "name": "文件名", "content": "内容" }
响应: { "status": "success", "message": "保存成功" }
```

### **5. 事件骨架管理**
```
POST /api/admin/event_skeletons/validate
请求头: X-Admin-Token: <token>
请求体: { "name": "文件名", "content": "JSON内容", "rules": {验证规则} }
响应: { "status": "success", "data": {验证结果} }

POST /api/admin/event_skeletons/promote
请求头: X-Admin-Token: <token>
请求体: { "source_name": "源文件", "target_name": "目标文件", "content": "内容", "allow_warnings": boolean }
响应: { "status": "success", "data": {发布结果} }

GET /api/admin/event_skeletons/rules
请求头: X-Admin-Token: <token>
查询参数: name=规则文件名
响应: { "status": "success", "data": {规则内容} }

POST /api/admin/event_skeletons/rules
请求头: X-Admin-Token: <token>
请求体: { "name": "规则文件名", "rules": {规则内容} }
响应: { "status": "success", "data": {保存结果} }
```

### **6. 其他管理功能**
```
POST /api/admin/upload_portrait
请求头: X-Admin-Token: <token>
表单数据: file=图片文件
响应: { "status": "success", "url": "图片URL" }

POST /api/admin/generate_skill_prompt
请求头: X-Admin-Token: <token>
请求体: { "concept": "技能概念" }
响应: { "status": "success", "prompt": "生成的提示词" }
```

## 🎯 **管理后台功能需求**

### **核心功能模块：**
1. **用户管理面板**
   - 用户列表查看
   - 用户搜索和筛选
   - 用户统计信息

2. **内容管理面板**
   - 剧情文件编辑
   - 角色配置管理
   - 模组内容管理

3. **系统管理面板**
   - 系统状态监控
   - 数据统计查看
   - 文件上传管理

4. **开发工具面板**
   - 事件骨架验证
   - 技能提示词生成
   - 预设模组管理

### **安全要求：**
1. **强密码认证**：管理员密码验证
2. **会话管理**：Token-based认证
3. **权限控制**：仅管理员可访问
4. **操作日志**：记录管理操作

## 🔍 **当前问题诊断**

### **前端已就绪：**
- ✅ 管理界面组件完整
- ✅ API调用配置就绪
- ✅ 路由导航已配置

### **后端需实现：**
- ❌ 管理认证接口
- ❌ 用户管理接口
- ❌ 文件管理接口
- ❌ 系统管理接口

### **数据存储需求：**
1. **用户数据**：从现有用户系统读取
2. **文件数据**：访问项目文件系统
3. **会话数据**：内存或Redis存储
4. **统计数据**：从现有数据计算

## 🚀 **实施建议**

### **方案A：扩展demo_server.py**
在现有demo_server.py基础上添加管理路由，使用模拟数据或简单文件操作。

### **方案B：启用完整应用**
切换到原始Server应用（需要配置环境变量和依赖）。

### **方案C：最小化实现**
只实现核心认证和基础管理功能，其他返回模拟数据。

### **推荐方案：A+C结合**
1. 先实现认证接口（必须）
2. 添加用户管理（模拟数据）
3. 实现文件管理（简单文件操作）
4. 其他功能返回占位数据

## 📝 **接口优先级**

### **P0（必须实现）：**
1. `POST /api/admin/login` - 管理员登录
2. `GET /api/admin/session` - 会话验证
3. `POST /api/admin/logout` - 退出登录

### **P1（核心功能）：**
4. `GET /api/admin/users` - 用户列表
5. `GET /api/admin/users/stats` - 用户统计
6. `GET /api/admin/files` - 文件列表

### **P2（增强功能）：**
7. `GET /api/admin/file` - 读取文件
8. `POST /api/admin/file` - 保存文件
9. `POST /api/admin/upload_portrait` - 上传图片

### **P3（高级功能）：**
10. 所有预设模组管理接口
11. 事件骨架管理接口
12. 技能提示词生成