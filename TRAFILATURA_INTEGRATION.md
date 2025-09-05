# Trafilatura 正文提取集成

## 🎯 设计理念

Quest API 已经完全集成 **Trafilatura** 作为主要的正文提取器，替代了之前复杂的多步骤处理流程。

### 📊 流程对比

**之前的复杂流程**：
```
URL → BeautifulSoup → Readability → Curator → 手动清理 → Sumy → LLM
```

**新的简化流程**：
```
URL → Trafilatura → Sumy → LLM
```

## 🔧 技术优势

### Trafilatura vs 原方案

| 特性 | 原方案 | Trafilatura |
|------|--------|-------------|
| **正文提取** | BeautifulSoup + 手动规则 | ✅ 专业算法 |
| **多语言支持** | 基础 | ✅ 原生支持 |
| **降噪能力** | 多步骤手动清理 | ✅ 内置强算法 |
| **元数据提取** | 手动实现 | ✅ 自动提取 |
| **维护成本** | 高 | ✅ 低 |
| **复杂页面** | 一般 | ✅ 表现更稳 |

### 简化的好处

1. **减少依赖**：移除了 `readability-lxml`
2. **更高质量**：Trafilatura 专门针对正文提取优化
3. **更快速度**：减少了多个中间步骤
4. **更稳定**：减少了出错点
5. **更智能**：自动处理多种页面结构

## 📋 配置说明

### 环境变量

```bash
# 核心开关
TRAFILATURA_ENABLED=true                    # 启用 Trafilatura 提取

# 提取选项
TRAFILATURA_INCLUDE_COMMENTS=false          # 包含评论内容
TRAFILATURA_INCLUDE_TABLES=true             # 包含表格内容
TRAFILATURA_INCLUDE_FORMATTING=false        # 保留格式标记
TRAFILATURA_DEDUPLICATE=true                # 去重复内容

# 策略选项
TRAFILATURA_FAVOR_PRECISION=true            # 优先精确度（更严格）
TRAFILATURA_FAVOR_RECALL=false              # 优先召回率（更宽松）

# 回退选项
CURATOR_FALLBACK_ENABLED=true               # 启用 Curator 作为回退
CURATOR_PRIMARY=false                       # Curator 不再是主要方案
```

### 推荐配置

**新闻文章**：
```bash
TRAFILATURA_FAVOR_PRECISION=true
TRAFILATURA_INCLUDE_TABLES=true
TRAFILATURA_INCLUDE_COMMENTS=false
```

**博客内容**：
```bash
TRAFILATURA_FAVOR_PRECISION=false
TRAFILATURA_FAVOR_RECALL=true
TRAFILATURA_INCLUDE_COMMENTS=true
```

**学术论文**：
```bash
TRAFILATURA_INCLUDE_TABLES=true
TRAFILATURA_INCLUDE_FORMATTING=true
TRAFILATURA_DEDUPLICATE=false
```

## 🔄 处理流程

### 三级回退机制

1. **Trafilatura 提取**（主要）
   - 专业正文提取算法
   - 自动降噪和清理
   - 多语言支持
   - 元数据提取

2. **Curator 回退**（可选）
   - 仅在 `CURATOR_FALLBACK_ENABLED=true` 时启用
   - 用于 Trafilatura 无法处理的特殊页面

3. **BeautifulSoup 极简回退**（保险）
   - 最后的保险机制
   - 基础的标签清理
   - 主要内容区域识别

### 流程示例

```python
# 1. Trafilatura 专业提取
if trafilatura_available:
    result = extract_content_with_trafilatura(html, url, config)
    if result.text:
        return result.text  # ✅ 成功

# 2. Curator 回退（可选）
if curator_fallback_enabled:
    result = apply_curator(html)
    if result.curated_text:
        return result.curated_text  # ✅ 回退成功

# 3. BeautifulSoup 极简回退
soup = BeautifulSoup(html)
main_content = find_main_content(soup)
return main_content.get_text()  # ✅ 保险成功
```

## 📈 性能提升

### 处理速度

- **减少步骤**：从 5 步减少到 1 步
- **减少 I/O**：不再需要多次 HTML 解析
- **减少内存**：不再保存中间结果

### 提取质量

- **更准确**：Trafilatura 专业算法
- **更干净**：内置降噪处理
- **更完整**：保留重要的表格和列表

### 维护成本

- **更少依赖**：减少外部库依赖
- **更少配置**：大部分参数自动优化
- **更少 Bug**：减少自定义逻辑

## 🧪 测试验证

### 测试不同类型网站

```bash
# 新闻网站
curl "http://localhost:8000/api/v1/insights" \
  -d '{"url": "https://www.cnn.com/2024/01/01/politics/news"}'

# 博客文章
curl "http://localhost:8000/api/v1/insights" \
  -d '{"url": "https://medium.com/@author/article"}'

# 学术论文
curl "http://localhost:8000/api/v1/insights" \
  -d '{"url": "https://arxiv.org/abs/2401.00001"}'
```

### 预期日志输出

```
INFO: 使用 Trafilatura 专业正文提取
INFO: Trafilatura 提取成功: 15000 字符
INFO: Sumy 预处理成功: 15000 → 5000 (压缩率: 67%)
INFO: LLM 摘要生成完成: 800 字符
```

## 🔧 故障排除

### Trafilatura 提取失败

**问题**：`Trafilatura 提取无结果`

**解决方案**：
1. 检查页面是否为反爬虫页面
2. 尝试启用 `CURATOR_FALLBACK_ENABLED=true`
3. 调整 `TRAFILATURA_FAVOR_RECALL=true` 放宽条件

### 提取内容质量差

**问题**：提取的内容包含太多噪音

**解决方案**：
1. 设置 `TRAFILATURA_FAVOR_PRECISION=true`
2. 启用 `TRAFILATURA_DEDUPLICATE=true`
3. 禁用 `TRAFILATURA_INCLUDE_COMMENTS=false`

### 缺少重要内容

**问题**：重要的表格或列表被过滤

**解决方案**：
1. 启用 `TRAFILATURA_INCLUDE_TABLES=true`
2. 设置 `TRAFILATURA_FAVOR_RECALL=true`
3. 禁用 `TRAFILATURA_DEDUPLICATE=false`

## 📚 更多资源

- [Trafilatura 官方文档](https://trafilatura.readthedocs.io/)
- [Trafilatura GitHub](https://github.com/adbar/trafilatura)
- [Quest API Sumy 集成文档](./SUMY_INTEGRATION.md)

---

## 🎉 总结

通过集成 Trafilatura，Quest API 实现了：

- ✅ **更简单**的处理流程
- ✅ **更高质量**的正文提取
- ✅ **更快速度**的处理性能
- ✅ **更低维护**成本
- ✅ **更强兼容性**支持

这是一个重大的架构优化，让整个系统更加专业和高效！🚀
