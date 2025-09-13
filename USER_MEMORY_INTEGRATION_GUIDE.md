# 🧠 用户记忆整合功能指南

## 📋 概述

Quest API 现在支持将用户的聊天记忆自动整合到用户profile中，实现智能的记忆管理和个性化体验。

## 🎯 功能特性

### ✅ 核心功能
- **自动记忆整合**: 聊天完成后自动整合记忆到用户profile
- **智能分类**: 按类型（偏好、事实、上下文、洞察）整理记忆
- **用户控制**: 用户可以手动触发整合或调整设置
- **记忆摘要**: 提供记忆统计和摘要信息
- **设置管理**: 可配置整合策略和参数

### 🔄 整合策略
- **相似性整合**: 合并相似的记忆内容
- **重要性排序**: 基于重要性分数排序记忆
- **时间整合**: 按时间顺序整理记忆
- **自动去重**: 自动检测和合并重复记忆

## 🔗 API端点

### 1. 手动整合记忆

**端点**: `POST /api/v1/user/memory/consolidate`

**功能**: 手动触发用户记忆整合

**请求体**:
```json
{
  "memory_types": ["user_preference", "fact"],  // 可选，指定要整合的类型
  "force_consolidate": false,  // 是否强制整合
  "consolidation_strategy": "similarity"  // 整合策略
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "记忆整合成功",
  "memory_profile": {
    "preferences": {
      "memory_1": {
        "content": "用户喜欢在早上工作",
        "importance": 0.8,
        "created_at": "2024-01-15T10:30:00Z",
        "metadata": {"source": "conversation"}
      }
    },
    "facts": {},
    "context": {},
    "insights": {},
    "last_consolidated": "2024-01-15T10:30:00Z",
    "consolidation_settings": {
      "auto_consolidate": true,
      "consolidation_threshold": 0.8,
      "max_memories_per_type": 50
    }
  }
}
```

### 2. 获取记忆档案

**端点**: `GET /api/v1/user/memory/profile`

**功能**: 获取用户的完整记忆档案

**响应示例**:
```json
{
  "success": true,
  "memory_profile": {
    "preferences": {
      "memory_1": {
        "content": "用户喜欢在早上工作",
        "importance": 0.8,
        "created_at": "2024-01-15T10:30:00Z",
        "metadata": {"source": "conversation"}
      }
    },
    "facts": {
      "memory_1": {
        "content": "用户是软件工程师",
        "importance": 0.9,
        "created_at": "2024-01-15T11:00:00Z",
        "metadata": {"source": "conversation"}
      }
    },
    "context": {},
    "insights": {},
    "last_consolidated": "2024-01-15T11:00:00Z",
    "consolidation_settings": {
      "auto_consolidate": true,
      "consolidation_threshold": 0.8,
      "max_memories_per_type": 50
    }
  }
}
```

### 3. 获取记忆摘要

**端点**: `GET /api/v1/user/memory/summary`

**功能**: 获取用户记忆的统计摘要

**响应示例**:
```json
{
  "success": true,
  "summary": {
    "total_memories": 2,
    "by_type": {
      "preferences": 1,
      "facts": 1,
      "context": 0,
      "insights": 0
    },
    "last_consolidated": "2024-01-15T11:00:00Z",
    "consolidation_settings": {
      "auto_consolidate": true,
      "consolidation_threshold": 0.8,
      "max_memories_per_type": 50
    }
  }
}
```

### 4. 更新记忆设置

**端点**: `PUT /api/v1/user/memory/settings`

**功能**: 更新记忆整合设置

**请求体**:
```json
{
  "auto_consolidate": true,
  "consolidation_threshold": 0.9,
  "max_memories_per_type": 100,
  "consolidation_strategy": "importance"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "记忆档案设置更新成功"
}
```

### 5. 自动整合记忆

**端点**: `POST /api/v1/user/memory/auto-consolidate`

**功能**: 触发自动记忆整合（通常在聊天完成后自动调用）

**查询参数**:
- `session_id` (可选): 特定会话ID

**响应示例**:
```json
{
  "success": true,
  "message": "记忆自动整合完成",
  "memory_profile": {
    // ... 整合后的记忆档案
  }
}
```

## 🔄 自动整合机制

### 触发条件
1. **聊天完成**: 每次聊天会话完成后自动检查
2. **记忆数量**: 当会话中有5条以上记忆时触发
3. **时间间隔**: 距离上次整合超过1小时
4. **用户设置**: 用户启用自动整合功能

### 整合流程
```
聊天完成 → 检查整合条件 → 收集相关记忆 → 智能整合 → 保存到profile → 更新统计
```

### 整合策略
- **相似性整合**: 使用AI检测相似记忆并合并
- **重要性排序**: 按重要性分数排序，保留重要记忆
- **时间整合**: 按时间顺序整理，保留最新信息
- **数量限制**: 每种类型最多保留指定数量的记忆

## 🛠️ 使用方法

### 1. 前端集成

```javascript
// 获取用户记忆档案
async function getUserMemoryProfile() {
  const response = await fetch('/api/v1/user/memory/profile', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return await response.json();
}

// 手动整合记忆
async function consolidateMemories() {
  const response = await fetch('/api/v1/user/memory/consolidate', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      consolidation_strategy: 'similarity'
    })
  });
  return await response.json();
}

// 更新记忆设置
async function updateMemorySettings(settings) {
  const response = await fetch('/api/v1/user/memory/settings', {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(settings)
  });
  return await response.json();
}
```

### 2. 后端集成

```python
from app.services.user_service import UserService

# 初始化服务
user_service = UserService()

# 手动整合用户记忆
result = await user_service.consolidate_user_memories(
    user_id="user-uuid",
    request=UserMemoryConsolidationRequest(
        memory_types=["user_preference", "fact"],
        consolidation_strategy="similarity"
    )
)

# 获取记忆档案
memory_profile = await user_service.get_user_memory_profile("user-uuid")

# 更新设置
await user_service.update_memory_profile_settings(
    user_id="user-uuid",
    settings={
        "auto_consolidate": True,
        "consolidation_threshold": 0.8
    }
)
```

## 📊 数据库结构

### profiles表新增字段
```sql
ALTER TABLE profiles ADD COLUMN memory_profile JSONB DEFAULT '{}';
```

### memory_profile字段结构
```json
{
  "preferences": {
    "memory_1": {
      "content": "记忆内容",
      "importance": 0.8,
      "created_at": "2024-01-15T10:30:00Z",
      "metadata": {"source": "conversation"}
    }
  },
  "facts": {},
  "context": {},
  "insights": {},
  "last_consolidated": "2024-01-15T10:30:00Z",
  "consolidation_settings": {
    "auto_consolidate": true,
    "consolidation_threshold": 0.8,
    "max_memories_per_type": 50
  }
}
```

## 🎨 用户体验设计

### 1. 记忆可视化
- **记忆地图**: 显示用户记忆的分布和关系
- **类型统计**: 按类型显示记忆数量
- **时间线**: 显示记忆的时间发展
- **重要性热图**: 显示记忆的重要性分布

### 2. 用户控制
- **手动整合**: 用户可以手动触发记忆整合
- **设置调整**: 用户可以调整整合参数
- **记忆编辑**: 用户可以编辑或删除特定记忆
- **导出功能**: 用户可以导出自己的记忆档案

### 3. 个性化体验
- **智能推荐**: 基于记忆档案提供个性化推荐
- **上下文感知**: 根据用户记忆调整响应
- **记忆提醒**: 在合适的时候提醒用户相关记忆
- **学习进度**: 显示用户的学习和成长轨迹

## 🔧 配置选项

### 默认设置
```json
{
  "auto_consolidate": true,
  "consolidation_threshold": 0.8,
  "max_memories_per_type": 50,
  "consolidation_strategy": "similarity"
}
```

### 可调参数
- **auto_consolidate**: 是否启用自动整合
- **consolidation_threshold**: 相似性阈值（0.0-1.0）
- **max_memories_per_type**: 每种类型最大记忆数量
- **consolidation_strategy**: 整合策略（similarity/importance/time）

## 🚀 部署步骤

### 1. 数据库迁移
```bash
# 运行数据库迁移脚本
psql -d your_database -f database/migrations/add_memory_profile_to_users.sql
```

### 2. 环境变量
确保以下环境变量已配置：
```bash
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
CHAT_MODEL=gpt-4o-mini
```

### 3. 重启服务
```bash
# 重启API服务以加载新功能
systemctl restart quest-api
```

## 📈 监控指标

### 关键指标
- **整合成功率**: 记忆整合的成功率
- **整合频率**: 自动整合的触发频率
- **记忆数量**: 用户记忆档案的大小
- **用户满意度**: 用户对记忆整合功能的反馈

### 性能指标
- **整合耗时**: 记忆整合的平均耗时
- **API响应时间**: 记忆相关API的响应时间
- **存储使用**: 记忆档案的存储空间使用

## 🎯 最佳实践

### 1. 整合策略选择
- **新用户**: 使用相似性整合，快速建立记忆档案
- **活跃用户**: 使用重要性整合，保留重要记忆
- **长期用户**: 使用时间整合，保持记忆的时效性

### 2. 设置优化
- **阈值调整**: 根据用户反馈调整相似性阈值
- **数量限制**: 根据存储容量调整记忆数量限制
- **自动整合**: 根据用户行为调整自动整合频率

### 3. 用户体验
- **渐进式整合**: 避免一次性整合大量记忆
- **用户通知**: 及时通知用户整合结果
- **个性化设置**: 允许用户自定义整合偏好

## 🔮 未来规划

### 短期目标
- [ ] 记忆可视化界面
- [ ] 记忆导出功能
- [ ] 记忆搜索功能
- [ ] 记忆分享功能

### 长期目标
- [ ] 跨会话记忆关联
- [ ] 记忆质量评估
- [ ] 个性化整合策略
- [ ] 记忆预测和推荐

## 📞 技术支持

如有问题或建议，请联系开发团队或查看相关文档：
- API文档: `/docs`
- 错误日志: 查看应用日志
- 性能监控: 查看监控面板
