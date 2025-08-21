# 🏷️ Quest API 默认标签系统

## 📖 概述

Quest API 为用户提供了一套精简而实用的默认英文标签系统，包含16个核心标签，帮助用户快速开始使用标签功能来组织和管理他们的insights。

## 🎯 默认标签分类

### 1. 技术相关 (Technology)
- **Technology** - 技术和创新
- **Programming** - 编程和编码
- **AI** - 人工智能
- **Web Development** - Web开发和设计

### 2. 学习相关 (Learning)
- **Learning** - 学习和教育
- **Tutorial** - 教程和指南

### 3. 内容类型 (Content Types)
- **Article** - 文章和博客
- **Video** - 视频和教程

### 4. 主题分类 (Topics)
- **Business** - 商业和创业
- **Productivity** - 生产力和效率
- **Design** - 设计和创意

### 5. 工具和资源 (Tools & Resources)
- **Tool** - 工具和实用程序
- **Resource** - 资源和参考资料

### 6. 项目相关 (Projects)
- **Project** - 项目和工作
- **Ideas** - 想法和灵感

## 🚀 自动添加功能

### 新用户注册时自动添加
当新用户注册时，系统会自动为他们添加所有16个核心标签：

```python
# 在 app/services/auth_service.py 中
async def register_user(self, user: UserCreate) -> dict:
    # ... 用户注册逻辑 ...
    
    # 为新用户添加默认标签
    await self.add_default_tags_for_user(user_id)
    
    # ... 返回结果 ...
```

### 手动添加标签脚本
使用 `add_default_tags.py` 脚本可以为现有用户添加默认标签：

```bash
# 运行脚本
python add_default_tags.py
```

## 📱 使用方法

### 1. 查看用户的默认标签
```javascript
// 获取用户标签列表
const response = await fetch('/api/v1/user-tags', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});

const tags = await response.json();
console.log('用户标签:', tags.data);
```

### 2. 使用默认标签创建insight
```javascript
// 创建insight时使用默认标签
const insightResponse = await fetch('/api/v1/insights', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({
    title: 'AI技术发展趋势',
    description: '关于人工智能的最新发展...',
    url: 'https://example.com/ai-trends',
    tags: ['AI', 'Technology', 'Article'] // 使用默认标签
  })
});
```

### 3. 从URL自动创建insight
```javascript
// 使用metadata API自动创建insight
const metadataResponse = await fetch('/api/v1/metadata/create-insight', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`
  },
  body: new FormData({
    url: 'https://example.com/article',
    user_id: userId,
    custom_tags: ['Technology', 'Article'], // 使用默认标签
    custom_description: '这是一篇关于技术的文章'
  })
});
```

## 🎨 标签颜色系统

每个默认标签都有预定义的颜色，确保UI的一致性和美观性：

- **蓝色系**: Technology (#3B82F6), Resource (#1E40AF)
- **绿色系**: Programming (#10B981), Learning (#84CC16), Productivity (#047857)
- **紫色系**: AI (#8B5CF6), Project (#7C3AED)
- **红色系**: Web Development (#EF4444), Video (#DC2626)
- **橙色系**: Tutorial (#F97316), Ideas (#F59E0B)
- **其他**: Business (#1F2937), Design (#BE185D), Tool (#7C2D12), Article (#059669)

## 🔧 自定义标签

用户可以在默认标签基础上创建自己的自定义标签：

```javascript
// 创建自定义标签
const customTagResponse = await fetch('/api/v1/user-tags', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({
    name: 'My Custom Tag',
    color: '#FF6B6B'
  })
});
```

## 📊 标签统计

查看标签使用情况：

```javascript
// 获取标签统计
const statsResponse = await fetch('/api/v1/user-tags/stats/overview', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});

const stats = await statsResponse.json();
console.log('标签统计:', stats.data);
```

## 🌟 最佳实践

### 1. 标签命名规范
- 使用英文标签保持一致性
- 标签名首字母大写
- 避免特殊字符和空格

### 2. 标签组合使用
- 技术标签 + 内容类型标签 (如: AI + Article)
- 主题标签 + 工具标签 (如: Business + Tool)
- 项目标签 + 学习标签 (如: Project + Learning)

### 3. 标签管理
- 定期清理未使用的标签
- 合并相似的标签
- 保持标签数量在合理范围内

## 🔄 更新默认标签

如果需要更新默认标签列表，可以修改 `app/services/auth_service.py` 中的 `DEFAULT_TAGS` 数组：

```python
DEFAULT_TAGS = [
    # 添加新的默认标签
    {"name": "New Tag", "color": "#FF0000"},
    # ... 其他标签
]
```

## 📝 注意事项

1. **权限要求**: 添加默认标签需要 `SUPABASE_SERVICE_ROLE_KEY`
2. **重复检查**: 系统会自动检查并跳过已存在的标签
3. **性能考虑**: 批量添加标签时会有适当的日志记录
4. **错误处理**: 如果某个标签添加失败，不会影响其他标签的添加

## 🎉 总结

简化后的默认标签系统为用户提供了：
- **16个核心英文标签**，覆盖主要使用场景
- **自动添加功能**，新用户无需手动设置
- **清晰的分类体系**，便于快速理解和使用
- **一致的颜色方案**，提升用户体验
- **灵活的扩展性**，支持自定义标签

这个精简的系统让用户可以立即开始使用标签功能，同时不会因为标签过多而感到困惑！🚀
