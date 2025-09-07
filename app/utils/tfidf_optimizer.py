"""
TF-IDF 文本预处理优化器

在 Trafilatura 提取之前使用 TF-IDF 向量化进行内容优化：
1. 识别页面中的重要文本块
2. 过滤低质量内容（广告、导航等）
3. 提取核心内容区域
4. 优化 HTML 结构以提高 Trafilatura 提取质量
"""

import os
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from bs4 import BeautifulSoup, Tag
import numpy as np

logger = logging.getLogger(__name__)

# 检查 scikit-learn 可用性
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity, linear_kernel
    SKLEARN_AVAILABLE = True
    logger.info("scikit-learn 库加载成功")
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn 不可用，TF-IDF 优化将被跳过")
    TfidfVectorizer = None
    cosine_similarity = None
    linear_kernel = None

# 检查 jieba 中文分词可用性
try:
    import jieba
    JIEBA_AVAILABLE = True
    logger.info("jieba 中文分词库加载成功")
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba 不可用，中文分词将被跳过")
    jieba = None


def is_tfidf_enabled() -> bool:
    """检查是否启用 TF-IDF 优化"""
    return (
        SKLEARN_AVAILABLE and 
        os.getenv('TFIDF_OPTIMIZER_ENABLED', 'true').lower() in ('1', 'true', 'yes', 'on')
    )


def get_tfidf_config() -> Dict[str, Any]:
    """获取 TF-IDF 优化配置"""
    return {
        'min_text_length': int(os.getenv('TFIDF_MIN_TEXT_LENGTH', '80') or '80'),  # 中文建议 80-120
        'max_features': int(os.getenv('TFIDF_MAX_FEATURES', '10000') or '10000'),  # 增加到 10k
        'min_df': int(os.getenv('TFIDF_MIN_DF', '2') or '2'),  # 改为绝对计数：2
        'max_df': float(os.getenv('TFIDF_MAX_DF', '0.8') or '0.8'),
        'score_floor': float(os.getenv('TFIDF_SCORE_FLOOR', '0.06') or '0.06'),  # 重命名：得分下限
        'content_ratio_threshold': float(os.getenv('TFIDF_CONTENT_RATIO', '0.2') or '0.2'),  # 降低到 20%
        'min_keep_k': int(os.getenv('TFIDF_MIN_KEEP_K', '80') or '80'),  # 新增：最低保留块数
        'percentile_threshold': float(os.getenv('TFIDF_PERCENTILE_THRESHOLD', '0.80') or '0.80'),  # 新增：80分位阈值
        'remove_low_quality': os.getenv('TFIDF_REMOVE_LOW_QUALITY', 'true').lower() in ('1', 'true', 'yes'),
        'enhance_content_blocks': os.getenv('TFIDF_ENHANCE_BLOCKS', 'true').lower() in ('1', 'true', 'yes'),
        'enable_chinese_segmentation': os.getenv('TFIDF_ENABLE_CHINESE_SEG', 'true').lower() in ('1', 'true', 'yes'),
        'max_link_density': float(os.getenv('TFIDF_MAX_LINK_DENSITY', '0.3') or '0.3'),  # 最大链接密度
        'min_alphanumeric_ratio': float(os.getenv('TFIDF_MIN_ALPHANUMERIC_RATIO', '0.5') or '0.5'),  # 最小字母数字比例
    }


class TfidfTextOptimizer:
    """TF-IDF 文本优化器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_tfidf_config()
        self.vectorizer = None
        self.content_vectors = None
        
    def _extract_text_blocks(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """提取页面中的文本块"""
        text_blocks = []
        
        # 定义内容标签
        content_tags = ['p', 'div', 'article', 'section', 'main', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        
        # 定义需要排除的标签
        exclude_tags = ['script', 'style', 'nav', 'header', 'footer', 'aside', 'menu', 'noscript']
        
        # 移除排除标签
        for tag_name in exclude_tags:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        # 提取文本块
        for tag in soup.find_all(content_tags):
            if not isinstance(tag, Tag):
                continue
                
            # 获取直接文本内容
            text = tag.get_text(separator=' ', strip=True)
            
            if len(text) >= self.config['min_text_length']:
                # 计算一些特征
                word_count = len(text.split())
                char_count = len(text)
                
                # 计算链接密度：链接文字长度 / 块文本长度
                links = tag.find_all('a')
                link_text_len = sum(len(a.get_text(strip=True)) for a in links)
                link_density = link_text_len / max(len(text), 1)
                
                # 检查标签类型权重
                tag_weight = self._get_tag_weight(tag.name)
                
                # 检查 class 和 id 属性
                class_score = self._get_class_score(tag.get('class', []))
                id_score = self._get_id_score(tag.get('id', ''))
                
                text_blocks.append({
                    'tag': tag,
                    'text': text,
                    'word_count': word_count,
                    'char_count': char_count,
                    'link_density': link_density,  # 更新为 link_density
                    'tag_weight': tag_weight,
                    'class_score': class_score,
                    'id_score': id_score,
                    'total_score': 0.0  # 将通过 TF-IDF 计算
                })
        
        return text_blocks
    
    def _get_tag_weight(self, tag_name: str) -> float:
        """获取标签权重"""
        weights = {
            'article': 1.0,
            'main': 1.0,
            'section': 0.9,
            'div': 0.7,
            'p': 0.8,
            'h1': 0.9,
            'h2': 0.8,
            'h3': 0.7,
            'h4': 0.6,
            'h5': 0.5,
            'h6': 0.5,
        }
        return weights.get(tag_name, 0.5)
    
    def _get_class_score(self, classes: List[str]) -> float:
        """根据 class 名称计算内容相关性得分"""
        if not classes:
            return 0.5
        
        # 内容相关的 class 关键词
        content_keywords = [
            'content', 'article', 'post', 'story', 'text', 'body', 'main',
            'entry', 'description', 'summary', 'abstract', 'excerpt'
        ]
        
        # 非内容相关的 class 关键词
        noise_keywords = [
            'ad', 'advertisement', 'banner', 'sidebar', 'nav', 'navigation',
            'menu', 'footer', 'header', 'comment', 'social', 'share',
            'related', 'recommend', 'popup', 'modal', 'widget'
        ]
        
        score = 0.5
        for class_name in classes:
            class_lower = class_name.lower()
            
            # 检查内容关键词
            for keyword in content_keywords:
                if keyword in class_lower:
                    score += 0.2
                    break
            
            # 检查噪声关键词
            for keyword in noise_keywords:
                if keyword in class_lower:
                    score -= 0.3
                    break
        
        return max(0.0, min(1.0, score))
    
    def _get_id_score(self, element_id: str) -> float:
        """根据 id 名称计算内容相关性得分"""
        if not element_id:
            return 0.5
        
        id_lower = element_id.lower()
        
        # 内容相关的 id 关键词
        content_keywords = [
            'content', 'article', 'post', 'story', 'text', 'body', 'main'
        ]
        
        # 非内容相关的 id 关键词
        noise_keywords = [
            'ad', 'advertisement', 'sidebar', 'nav', 'navigation',
            'menu', 'footer', 'header', 'comment', 'social'
        ]
        
        score = 0.5
        
        for keyword in content_keywords:
            if keyword in id_lower:
                return 0.8
        
        for keyword in noise_keywords:
            if keyword in id_lower:
                return 0.2
        
        return score
    
    def _pretokenize(self, text: str) -> str:
        """混合语言预分词：中文 jieba + 英文正规化"""
        if not text:
            return ""
        
        text = text.strip()
        tokens = []
        
        # 检查是否包含中文字符
        if re.search(r'[\u4e00-\u9fff]', text):
            # 中文分词
            if JIEBA_AVAILABLE and self.config.get('enable_chinese_segmentation', True):
                try:
                    # jieba 分词
                    words = jieba.cut(text)
                    tokens.extend([w.strip() for w in words if w.strip()])
                except Exception as e:
                    logger.warning(f"jieba 分词失败: {e}")
                    # jieba 失败，用汉字 bigram 兜底
                    tokens.extend(self._chinese_bigram_fallback(text))
            else:
                # jieba 不可用，用汉字 bigram 兜底
                tokens.extend(self._chinese_bigram_fallback(text))
        else:
            # 英文正规化 + 单词切分
            tokens.extend(self._english_tokenize(text))
        
        # 去停用词
        tokens = self._remove_stopwords(tokens)
        
        # 用空格连接
        return " ".join(tokens)
    
    def _chinese_bigram_fallback(self, text: str) -> List[str]:
        """中文 bigram 兜底分词"""
        # 提取汉字
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        tokens = []
        
        # 单字
        tokens.extend(chinese_chars)
        
        # bigram
        for i in range(len(chinese_chars) - 1):
            tokens.append(chinese_chars[i] + chinese_chars[i + 1])
        
        return tokens
    
    def _english_tokenize(self, text: str) -> List[str]:
        """英文正规化 + 单词切分"""
        # 正规化：转小写，去标点
        normalized = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # 单词切分
        words = normalized.split()
        
        # 过滤单字符词（可选）
        words = [w for w in words if len(w) > 1]
        
        return words
    
    def _remove_stopwords(self, tokens: List[str]) -> List[str]:
        """统一去停用词（中英两套）"""
        # 中文停用词
        chinese_stopwords = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'
        }
        
        # 英文停用词
        english_stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'
        }
        
        # 过滤停用词
        filtered_tokens = []
        for token in tokens:
            token_lower = token.lower()
            if token_lower not in chinese_stopwords and token_lower not in english_stopwords:
                filtered_tokens.append(token)
        
        return filtered_tokens

    def _calculate_tfidf_scores(self, text_blocks: List[Dict[str, Any]], query_text: str = "") -> List[Dict[str, Any]]:
        """使用 TF-IDF 余弦相似度计算文本块得分"""
        if not text_blocks:
            return text_blocks
        
        # 准备文本数据并预处理
        texts = [self._pretokenize(block['text']) for block in text_blocks]
        
        # 生成查询文本（标题 + 用户查询）
        if not query_text:
            # 如果没有查询，使用第一个文本块的前80字符作为查询
            query_text = texts[0][:80] if texts else ""
        query_text = self._pretokenize(query_text)
        
        try:
            # 动态调整 min_df 和 max_df 以适应文档数量
            n_docs = len(texts)
            min_df = min(self.config['min_df'], max(1, n_docs - 1))  # 最多 n_docs-1
            max_df = max(self.config['max_df'], min(1.0, max(0.1, n_docs / 2)))  # 至少50%的文档
            
            # 如果文档太少，使用更宽松的设置
            if n_docs < 3:
                min_df = 1
                max_df = 1.0
            
            # 创建 TF-IDF 向量化器
            self.vectorizer = TfidfVectorizer(
                max_features=self.config['max_features'],
                min_df=min_df,
                max_df=max_df,
                stop_words=None,  # 在预分词阶段统一去停用词
                token_pattern=r'(?u)\b\w+\b',  # 保留单字（中文/英文都不丢）
                ngram_range=(1, 1),    # 只用 1-gram，预分词已处理 ngram
                lowercase=False,  # 预分词已处理大小写
                strip_accents=None,  # 预分词已处理
                norm='l2'  # 保持 L2 归一化，便于余弦相似度计算
            )
            
            # 计算 TF-IDF 向量
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            query_vector = self.vectorizer.transform([query_text])
            
            # 计算余弦相似度
            similarities = linear_kernel(query_vector, tfidf_matrix).ravel()
            
            # 计算每个文本块的得分
            for i, block in enumerate(text_blocks):
                # TF-IDF 余弦相似度得分
                tfidf_score = float(similarities[i])
                
                # 综合得分：TF-IDF + 结构化特征
                total_score = (
                    tfidf_score * 0.6 +  # TF-IDF 相似度权重最高
                    block['tag_weight'] * 0.15 +
                    block['class_score'] * 0.15 +
                    block['id_score'] * 0.05 +
                    (1.0 - block.get('link_density', block.get('link_ratio', 0))) * 0.05
                )
                
                block['tfidf_score'] = tfidf_score
                block['total_score'] = total_score
            
            # 按得分排序
            text_blocks.sort(key=lambda x: x['total_score'], reverse=True)
            
            logger.debug(f"TF-IDF 余弦相似度分析完成，处理了 {len(text_blocks)} 个文本块")
            logger.debug(f"查询文本: {query_text[:100]}...")
            
        except Exception as e:
            logger.warning(f"TF-IDF 计算失败: {e}")
            # 如果 TF-IDF 失败，使用基础得分
            for block in text_blocks:
                block['tfidf_score'] = 0.0
                block['total_score'] = (
                    block['tag_weight'] * 0.4 +
                    block['class_score'] * 0.3 +
                    block['id_score'] * 0.2 +
                    (1.0 - block.get('link_density', block.get('link_ratio', 0))) * 0.1
                )
            text_blocks.sort(key=lambda x: x['total_score'], reverse=True)
        
        return text_blocks
    
    def _apply_quality_rules(self, text_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """应用质量规则过滤"""
        if not text_blocks:
            return text_blocks
        
        filtered_blocks = []
        discard_reasons = {'too_short': 0, 'link_density': 0, 'blacklist': 0, 'alphanumeric': 0}
        
        # 黑名单短语
        blacklist_phrases = [
            'cookie', 'subscribe', '免责', '相关阅读', '扫码', '©', '责任编辑',
            '广告', '推广', '赞助', '点击', '更多', '阅读全文', '展开全文'
        ]
        
        for block in text_blocks:
            text = block['text']
            
            # 规则1: 最小长度
            if len(text) < self.config['min_text_length']:
                discard_reasons['too_short'] += 1
                continue
            
            # 规则2: 链接密度过高
            if block.get('link_density', 0) > self.config.get('max_link_density', 0.3):
                discard_reasons['link_density'] += 1
                continue
            
            # 规则3: 非字母数字比例过高
            alphanumeric_count = sum(1 for c in text if c.isalnum())
            alphanumeric_ratio = alphanumeric_count / max(len(text), 1)
            if alphanumeric_ratio < self.config.get('min_alphanumeric_ratio', 0.5):
                discard_reasons['alphanumeric'] += 1
                continue
            
            # 规则4: 黑名单短语且长度较短
            text_lower = text.lower()
            if any(phrase in text_lower for phrase in blacklist_phrases) and len(text) < 120:
                discard_reasons['blacklist'] += 1
                continue
            
            filtered_blocks.append(block)
        
        logger.debug(f"质量规则过滤：{len(text_blocks)} -> {len(filtered_blocks)} 个文本块")
        logger.debug(f"丢弃原因：{discard_reasons}")
        
        return filtered_blocks
    
    def _filter_low_quality_blocks(self, text_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤低质量文本块 - 自适应阈值 + Top-K 兜底"""
        if not self.config['remove_low_quality']:
            return text_blocks
        
        if not text_blocks:
            return text_blocks
        
        n = len(text_blocks)
        scores = [block['total_score'] for block in text_blocks]
        
        # 计算阈值
        p80 = float(np.percentile(scores, self.config['percentile_threshold'] * 100))
        floor = float(self.config.get('score_floor', self.config.get('similarity_threshold', 0.06)))
        
        # Top-K 兜底
        K = max(int(np.ceil(self.config['content_ratio_threshold'] * n)), self.config['min_keep_k'])
        
        # 两种保留策略
        by_rank = set(range(min(K, n)))  # text_blocks 已按分数降序
        by_thresh = {i for i, s in enumerate(scores) if s >= max(p80, floor)}
        
        # 合并保留的索引
        kept_idx = sorted(by_rank | by_thresh)
        filtered_blocks = [text_blocks[i] for i in kept_idx]
        
        logger.debug(f"自适应过滤：{n} -> {len(filtered_blocks)} 个文本块")
        logger.debug(f"阈值: P80={p80:.4f}, floor={floor:.4f}, K={K}")
        logger.debug(f"保留策略: Top-K={len(by_rank)}, 阈值={len(by_thresh)}, 合并={len(kept_idx)}")
        
        return filtered_blocks
    
    def _enhance_content_structure(self, soup: BeautifulSoup, high_quality_blocks: List[Dict[str, Any]]) -> BeautifulSoup:
        """增强内容结构，优化 HTML 以提高 Trafilatura 提取质量"""
        if not self.config['enhance_content_blocks']:
            return soup
        
        try:
            # 创建新的 HTML 结构
            new_soup = BeautifulSoup('<html><head></head><body></body></html>', 'html.parser')
            body = new_soup.body
            
            # 保留原始的 head 部分（包含元数据）
            if soup.head:
                new_soup.head.replace_with(soup.head)
            
            # 添加高质量内容块
            for i, block in enumerate(high_quality_blocks[:10]):  # 只保留前10个最高质量的块
                # 创建包装器
                wrapper = new_soup.new_tag('div', **{'class': 'tfidf-content-block', 'data-score': f"{block['total_score']:.3f}"})
                
                # 克隆原始标签
                cloned_tag = new_soup.new_tag(block['tag'].name)
                cloned_tag.string = block['text']
                
                # 保留重要属性
                if block['tag'].get('id'):
                    cloned_tag['id'] = block['tag']['id']
                if block['tag'].get('class'):
                    cloned_tag['class'] = block['tag']['class']
                
                wrapper.append(cloned_tag)
                body.append(wrapper)
            
            logger.debug(f"HTML 结构优化完成，保留了 {len(high_quality_blocks[:10])} 个高质量内容块")
            return new_soup
            
        except Exception as e:
            logger.warning(f"HTML 结构优化失败: {e}")
            return soup
    
    def optimize_html(self, html: str, url: Optional[str] = None, title: str = "", user_query: str = "") -> Tuple[str, Dict[str, Any]]:
        """
        使用 TF-IDF 优化 HTML 内容
        
        Args:
            html: 原始 HTML 内容
            url: 页面 URL（可选）
            title: 页面标题（用于查询）
            user_query: 用户查询（用于查询）
        
        Returns:
            优化后的 HTML 和分析报告
        """
        if not SKLEARN_AVAILABLE or not is_tfidf_enabled():
            return html, {'optimization': 'disabled'}
        
        try:
            logger.debug(f"开始 TF-IDF HTML 优化: {url or 'unknown'}")
            
            # 解析 HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取文本块
            text_blocks = self._extract_text_blocks(soup)
            
            if not text_blocks:
                logger.warning("未找到有效文本块")
                return html, {'optimization': 'no_content_blocks'}
            
            # 生成查询文本
            query_text = (title + " " + user_query).strip()
            
            # 计算 TF-IDF 得分
            text_blocks = self._calculate_tfidf_scores(text_blocks, query_text)
            
            # 应用质量规则过滤
            text_blocks = self._apply_quality_rules(text_blocks)
            
            # 过滤低质量内容
            high_quality_blocks = self._filter_low_quality_blocks(text_blocks)
            
            # 增强内容结构
            optimized_soup = self._enhance_content_structure(soup, high_quality_blocks)
            
            # 生成分析报告
            report = {
                'optimization': 'success',
                'original_blocks': len(text_blocks),
                'filtered_blocks': len(high_quality_blocks),
                'top_scores': [
                    {
                        'score': block['total_score'],
                        'tfidf_score': block['tfidf_score'],
                        'tag': block['tag'].name,
                        'text_preview': block['text'][:100] + '...' if len(block['text']) > 100 else block['text']
                    }
                    for block in high_quality_blocks[:3]
                ],
                'config': self.config
            }
            
            logger.info(f"TF-IDF 优化完成: {len(text_blocks)} -> {len(high_quality_blocks)} 个内容块")
            
            return str(optimized_soup), report
            
        except Exception as e:
            logger.error(f"TF-IDF 优化失败: {e}")
            return html, {'optimization': 'failed', 'error': str(e)}


def optimize_html_with_tfidf(html: str, url: Optional[str] = None, title: str = "", user_query: str = "") -> Tuple[str, Dict[str, Any]]:
    """
    便捷函数：使用 TF-IDF 优化 HTML
    
    Args:
        html: 原始 HTML 内容
        url: 页面 URL（可选）
        title: 页面标题（用于查询）
        user_query: 用户查询（用于查询）
    
    Returns:
        优化后的 HTML 和分析报告
    """
    optimizer = TfidfTextOptimizer()
    return optimizer.optimize_html(html, url, title, user_query)


# 配置说明
TFIDF_CONFIG_HELP = """
TF-IDF 文本优化器配置选项:

核心开关:
- TFIDF_OPTIMIZER_ENABLED=true               # 启用 TF-IDF 优化

文本处理:
- TFIDF_MIN_TEXT_LENGTH=50                   # 最小文本长度
- TFIDF_MAX_FEATURES=1000                    # TF-IDF 最大特征数
- TFIDF_MIN_DF=0.1                           # 最小文档频率
- TFIDF_MAX_DF=0.8                           # 最大文档频率

质量控制:
- TFIDF_SIMILARITY_THRESHOLD=0.3             # 相似度阈值
- TFIDF_CONTENT_RATIO=0.6                    # 内容质量比例阈值
- TFIDF_REMOVE_LOW_QUALITY=true              # 移除低质量内容
- TFIDF_ENHANCE_BLOCKS=true                  # 增强内容块结构

优势:
✅ 使用 TF-IDF 识别页面核心内容
✅ 过滤广告、导航等噪声内容
✅ 优化 HTML 结构提高 Trafilatura 提取质量
✅ 基于机器学习的智能内容分析
✅ CPU 高效的稀疏矩阵计算
"""
