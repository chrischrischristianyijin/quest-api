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

### 💾 保存模式 🆕
- **strict**: 严格模式，仅保存 Top-K 段落（最小化内容）
- **balanced**: 平衡模式，Top-K + 上下文窗口（默认）
- **preserve**: 保存模式，标记重要句子但保留更多原文（推荐用于保存更多内容）
- 可配置保留比例（0.1-1.0，默认 0.8）

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

# 保存模式配置 🆕
export SUMY_PRESERVE_MODE=preserve   # 保存模式 (strict/balanced/preserve)
export SUMY_PRESERVE_RATIO=0.5       # 保存模式下的保留比例 (0.1-1.0)

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
5. **结果保存**：保存预处理后的内容和摘要（预处理信息仅记录日志，不存储到数据库）

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

## 保存模式详解 🆕

### 三种保存模式对比

| 模式 | 内容保留 | 质量 | 性能 | 适用场景 |
|------|----------|------|------|----------|
| **strict** | 20-40% | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 成本敏感，需要高度精炼 |
| **balanced** | 40-60% | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 平衡质量和成本（默认） |
| **preserve** | 30-70% | ⭐⭐⭐⭐ | ⭐⭐⭐ | 保留关键信息，可调节保留比例 |

### Preserve 模式工作原理

1. **关键句识别**：使用 LexRank/TextRank 找出重要句子
2. **段落评分**：统计每个段落包含的关键句数量
3. **智能保留**：
   - 优先保留包含关键句的段落
   - 按保留比例补充其他段落
   - 保持原文顺序和连贯性
4. **重要性标记**：在结果中标记哪些段落包含关键句

### 保留比例说明

```bash
# 保守策略 - 保留更多内容，适合重要文档
SUMY_PRESERVE_RATIO=0.7

# 平衡策略 - 保留核心内容（推荐）
SUMY_PRESERVE_RATIO=0.5

# 激进策略 - 保留关键内容，节省成本
SUMY_PRESERVE_RATIO=0.3
```

## 配置调优

### 针对不同内容类型

**新闻文章（平衡模式）**：
```bash
SUMY_ALGORITHM=lexrank
SUMY_PRESERVE_MODE=preserve
SUMY_PRESERVE_RATIO=0.5
SUMY_MAX_SENTENCES=8
```

**技术博客（平衡模式）**：
```bash
SUMY_ALGORITHM=textrank
SUMY_PRESERVE_MODE=balanced
SUMY_TOP_K_PARAGRAPHS=4
SUMY_CONTEXT_WINDOW=2
```

**学术论文（重要内容保留）**：
```bash
SUMY_ALGORITHM=lexrank
SUMY_PRESERVE_MODE=preserve
SUMY_PRESERVE_RATIO=0.6
SUMY_MAX_SENTENCES=10
```

**社交媒体/短文（严格模式）**：
```bash
SUMY_ALGORITHM=textrank
SUMY_PRESERVE_MODE=strict
SUMY_TOP_K_PARAGRAPHS=3
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

## 数据存储说明

### 存储策略
- **`text` 字段**：存储 Sumy 预处理后的关键内容（不是原始文本）
- **`summary` 字段**：存储基于预处理内容的 LLM 摘要
- **预处理信息**：仅记录在日志中，不存储到数据库，减少存储开销

### 数据库字段
```sql
-- insight_contents 表结构（简化）
CREATE TABLE insight_contents (
    insight_id UUID,
    text TEXT,        -- Sumy 预处理后的关键内容
    summary TEXT,     -- LLM 生成的摘要
    -- 其他字段...
    -- 注意：没有 sumy_processing 字段
);
```

## 监控与日志

### 关键日志
```
INFO - 开始 Sumy 内容预处理，原文本长度: 15000
INFO - Sumy 预处理成功: 15000 → 12000 (压缩率: 80%, 模式: preserve)
INFO - Sumy 预处理已应用 - 方法: sumy_preserve, 算法: lexrank, 压缩率: 80%, 段落数: 8
INFO - 即将写入 insight_contents - summary 长度: 245, text 长度: 12000
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

## 💡 推荐配置

### 实用的保留比例设置

```bash
# 🔥 推荐配置 - 平衡质量和成本
SUMY_PRESERVE_MODE=preserve
SUMY_PRESERVE_RATIO=0.5       # 保留 50% 内容，节省 50% 成本

# 💰 成本优化配置 - 最大化节省
SUMY_PRESERVE_RATIO=0.3       # 保留 30% 内容，节省 70% 成本

# 📚 重要文档配置 - 保留更多信息
SUMY_PRESERVE_RATIO=0.7       # 保留 70% 内容，节省 30% 成本
```

### 📊 成本效果对比

| 保留比例 | 成本节省 | 信息保留 | 适用场景 |
|----------|----------|----------|----------|
| 30% | 💰💰💰 70% | ⭐⭐⭐ | 批量处理，成本敏感 |
| 50% | 💰💰 50% | ⭐⭐⭐⭐ | **日常使用（推荐）** |
| 70% | 💰 30% | ⭐⭐⭐⭐⭐ | 重要文档，质量优先 |

通过这种设计，确保了 LLM 始终处理最相关的内容，既保留了关键信息又显著降低了成本。现在推荐使用 **50% 保留比例** 作为日常配置！🚀
