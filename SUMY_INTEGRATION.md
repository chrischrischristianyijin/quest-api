# Sumy 内容预处理集成文档

## 概述

本项目已成功集成 Sumy 库作为**内容预处理步骤**，为 Quest API 提供基于关键句提取的段落 Top-K 内容筛选功能。Sumy 预处理在内容清洗后、LLM 摘要前执行，确保 LLM 处理的是最相关的关键内容。

## 功能特点

### 🔍 关键句提取
- 支持 **LexRank** 和 **TextRank** 两种算法
- 自动语言检测（中文/英文）
- 可配置关键句数量（默认 8 个）

### 📊 段落 Top-K 算法
- 将关键句映射回原始段落
- 统计每个段落的命中次数
- 按分数排序，选择 Top-K 段落（默认 4 个）

### 🔄 上下文窗口
- 为每个选中段落添加前后上下文
- 可配置窗口大小（默认前后各 1 段）
- 保持文本连贯性

## 安装与设置

### 1. 安装依赖
```bash
# 自动安装（推荐）
python setup_sumy.py

# 手动安装
pip install sumy==0.11.0 nltk==3.8.1
```

### 2. 环境变量配置
```bash
# 启用 Sumy 预处理（默认启用）
export SUMY_PREPROCESSING_ENABLED=1

# 预处理参数配置
export SUMY_MAX_SENTENCES=8          # 最大关键句数量
export SUMY_TOP_K_PARAGRAPHS=4       # Top-K 段落数量
export SUMY_CONTEXT_WINDOW=1         # 上下文窗口大小
export SUMY_ALGORITHM=lexrank        # 算法选择 (lexrank/textrank)

# LLM 摘要配置（处理预处理后的内容）
export SUMMARY_ENABLED=1
export OPENAI_API_KEY=your_key_here
```

## 使用方式

### API 调用
Sumy 摘要已集成到现有的摘要 API 中，无需额外调用：

```python
# 通过 metadata API
POST /api/v1/metadata/extract
{
    "url": "https://example.com/article"
}

# 或通过 insights API
POST /api/v1/insights
{
    "url": "https://example.com/article",
    "thought": "用户想法"
}
```

### 工作流程
1. **内容抓取**：获取网页 HTML 和原始文本
2. **内容清洗**：Curator 清洗 + 文本规范化
3. **Sumy 预处理**：提取关键段落（Top-K + 上下文）
4. **LLM 摘要**：基于预处理后的关键内容生成摘要
5. **结果保存**：保存预处理后的内容和摘要

## 算法详解

### LexRank 算法
- 基于图的排序算法
- 计算句子间的相似度
- 适合处理较长的文档
- **推荐用于新闻文章、学术论文**

### TextRank 算法  
- Google PageRank 的文本版本
- 基于句子的共现关系
- 计算效率更高
- **推荐用于博客、社交媒体内容**

### 段落映射算法
```python
def map_sentences_to_paragraphs(key_sentences, paragraphs):
    """
    1. 精确匹配：句子完全包含在段落中
    2. 模糊匹配：词汇重叠率 > 60%
    3. 分数累计：每个命中 +1 分，模糊命中 +0.5 分
    4. Top-K 选择：按分数排序，选择前 K 个段落
    5. 上下文扩展：添加前后窗口段落
    """
```

## 性能优化

### 缓存机制
- 段落分割结果缓存
- 关键句提取结果缓存
- 避免重复计算

### 内存管理
- 延迟加载 Sumy 库
- 自动清理临时数据
- 支持大文档处理

### 错误处理
- 优雅的依赖缺失处理
- 自动回退机制
- 详细的错误日志

## 配置调优

### 针对不同内容类型

**新闻文章**：
```bash
SUMY_ALGORITHM=lexrank
SUMY_MAX_SENTENCES=10
SUMY_TOP_K_PARAGRAPHS=5
SUMY_CONTEXT_WINDOW=1
```

**技术博客**：
```bash
SUMY_ALGORITHM=textrank
SUMY_MAX_SENTENCES=8
SUMY_TOP_K_PARAGRAPHS=4
SUMY_CONTEXT_WINDOW=2
```

**学术论文**：
```bash
SUMY_ALGORITHM=lexrank
SUMY_MAX_SENTENCES=12
SUMY_TOP_K_PARAGRAPHS=6
SUMY_CONTEXT_WINDOW=1
```

### 性能 vs 质量权衡

| 配置 | 性能 | 质量 | 适用场景 |
|------|------|------|----------|
| 快速模式 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 实时预览 |
| 平衡模式 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 一般使用 |
| 高质量模式 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 重要文档 |

## 测试验证

### 运行测试
```bash
# 完整测试
python test_sumy_integration.py

# 基本功能测试
python setup_sumy.py
```

### 测试内容
- ✅ 依赖安装检查
- ✅ 中文文本摘要
- ✅ 英文文本摘要
- ✅ 集成API测试
- ✅ 错误处理测试

## 监控与日志

### 关键日志
```
INFO - 尝试使用 Sumy 生成摘要
INFO - Sumy 摘要生成成功，方法: sumy, 段落数: 4, 关键句数: 8
WARNING - Sumy 摘要生成失败，回退到 LLM 摘要: [错误信息]
```

### 性能指标
- 摘要生成时间
- 段落命中率
- 回退频率
- 内存使用量

## 故障排除

### 常见问题

**Q: 提示 "Sumy 库不可用"**
```bash
# 重新安装依赖
pip install sumy==0.11.0 nltk==3.8.1
python -c "import nltk; nltk.download('punkt')"
```

**Q: 中文摘要效果不佳**
```bash
# 调整算法和参数
export SUMY_ALGORITHM=textrank
export SUMY_MAX_SENTENCES=12
```

**Q: 摘要过短或过长**
```bash
# 调整段落和上下文参数
export SUMY_TOP_K_PARAGRAPHS=6
export SUMY_CONTEXT_WINDOW=2
```

## 未来改进

### 计划功能
- [ ] 支持更多语言
- [ ] 自定义停用词
- [ ] 摘要质量评分
- [ ] A/B 测试框架

### 性能优化
- [ ] 异步处理
- [ ] 分布式计算
- [ ] 模型压缩
- [ ] 缓存优化

---

## 总结

Sumy 内容预处理集成为 Quest API 提供了：
- 🎯 **更精准的内容筛选**（关键段落提取）
- 💰 **更低的 LLM 成本**（减少输入 token 数量）
- 🚀 **更快的处理速度**（预筛选减少 LLM 处理时间）
- 📊 **更好的摘要质量**（LLM 专注于关键内容）
- 🔧 **灵活的参数调节**（适应不同内容类型）

**新的处理流程**：
```
原始内容 → Curator清洗 → Sumy预处理 → LLM摘要 → 保存结果
   ↓           ↓            ↓          ↓        ↓
 HTML文本   规范化文本    关键段落    高质量摘要  最终存储
```

通过这种设计，确保了 LLM 始终处理最相关的内容，提高了摘要质量的同时降低了成本。
