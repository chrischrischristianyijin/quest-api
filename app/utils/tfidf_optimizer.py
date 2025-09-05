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
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
    logger.info("scikit-learn 库加载成功")
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn 不可用，TF-IDF 优化将被跳过")
    TfidfVectorizer = None
    cosine_similarity = None


def is_tfidf_enabled() -> bool:
    """检查是否启用 TF-IDF 优化"""
    return (
        SKLEARN_AVAILABLE and 
        os.getenv('TFIDF_OPTIMIZER_ENABLED', 'true').lower() in ('1', 'true', 'yes', 'on')
    )


def get_tfidf_config() -> Dict[str, Any]:
    """获取 TF-IDF 优化配置"""
    return {
        'min_text_length': int(os.getenv('TFIDF_MIN_TEXT_LENGTH', '50') or '50'),
        'max_features': int(os.getenv('TFIDF_MAX_FEATURES', '1000') or '1000'),
        'min_df': float(os.getenv('TFIDF_MIN_DF', '0.1') or '0.1'),
        'max_df': float(os.getenv('TFIDF_MAX_DF', '0.8') or '0.8'),
        'similarity_threshold': float(os.getenv('TFIDF_SIMILARITY_THRESHOLD', '0.3') or '0.3'),
        'content_ratio_threshold': float(os.getenv('TFIDF_CONTENT_RATIO', '0.6') or '0.6'),
        'remove_low_quality': os.getenv('TFIDF_REMOVE_LOW_QUALITY', 'true').lower() in ('1', 'true', 'yes'),
        'enhance_content_blocks': os.getenv('TFIDF_ENHANCE_BLOCKS', 'true').lower() in ('1', 'true', 'yes'),
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
                
                # 检查是否包含链接
                links = tag.find_all('a')
                link_ratio = len(links) / max(word_count, 1)
                
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
                    'link_ratio': link_ratio,
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
    
    def _calculate_tfidf_scores(self, text_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用 TF-IDF 计算文本块得分"""
        if not text_blocks:
            return text_blocks
        
        # 准备文本数据
        texts = [block['text'] for block in text_blocks]
        
        try:
            # 创建 TF-IDF 向量化器
            self.vectorizer = TfidfVectorizer(
                max_features=self.config['max_features'],
                min_df=self.config['min_df'],
                max_df=self.config['max_df'],
                stop_words='english',  # 可以根据需要调整
                ngram_range=(1, 2),    # 包含 1-gram 和 2-gram
                lowercase=True,
                strip_accents='unicode'
            )
            
            # 计算 TF-IDF 向量
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            self.content_vectors = tfidf_matrix
            
            # 计算每个文本块的 TF-IDF 得分
            for i, block in enumerate(text_blocks):
                # 获取该文本块的向量
                vector = tfidf_matrix[i]
                
                # 计算向量的 L2 范数作为内容重要性得分
                tfidf_score = np.linalg.norm(vector.toarray())
                
                # 综合得分：TF-IDF + 结构化特征
                total_score = (
                    tfidf_score * 0.4 +
                    block['tag_weight'] * 0.2 +
                    block['class_score'] * 0.2 +
                    block['id_score'] * 0.1 +
                    (1.0 - block['link_ratio']) * 0.1  # 链接少的内容得分更高
                )
                
                block['tfidf_score'] = tfidf_score
                block['total_score'] = total_score
            
            # 按得分排序
            text_blocks.sort(key=lambda x: x['total_score'], reverse=True)
            
            logger.debug(f"TF-IDF 分析完成，处理了 {len(text_blocks)} 个文本块")
            
        except Exception as e:
            logger.warning(f"TF-IDF 计算失败: {e}")
            # 如果 TF-IDF 失败，使用基础得分
            for block in text_blocks:
                block['tfidf_score'] = 0.0
                block['total_score'] = (
                    block['tag_weight'] * 0.4 +
                    block['class_score'] * 0.3 +
                    block['id_score'] * 0.2 +
                    (1.0 - block['link_ratio']) * 0.1
                )
            text_blocks.sort(key=lambda x: x['total_score'], reverse=True)
        
        return text_blocks
    
    def _filter_low_quality_blocks(self, text_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤低质量文本块"""
        if not self.config['remove_low_quality']:
            return text_blocks
        
        if not text_blocks:
            return text_blocks
        
        # 计算得分阈值
        scores = [block['total_score'] for block in text_blocks]
        if not scores:
            return text_blocks
        
        mean_score = np.mean(scores)
        threshold = mean_score * self.config['content_ratio_threshold']
        
        # 过滤低质量块
        filtered_blocks = [
            block for block in text_blocks 
            if block['total_score'] >= threshold
        ]
        
        logger.debug(f"过滤低质量内容：{len(text_blocks)} -> {len(filtered_blocks)} 个文本块")
        
        return filtered_blocks if filtered_blocks else text_blocks[:5]  # 至少保留前5个
    
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
    
    def optimize_html(self, html: str, url: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        使用 TF-IDF 优化 HTML 内容
        
        Args:
            html: 原始 HTML 内容
            url: 页面 URL（可选）
        
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
            
            # 计算 TF-IDF 得分
            text_blocks = self._calculate_tfidf_scores(text_blocks)
            
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


def optimize_html_with_tfidf(html: str, url: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    """
    便捷函数：使用 TF-IDF 优化 HTML
    
    Args:
        html: 原始 HTML 内容
        url: 页面 URL（可选）
    
    Returns:
        优化后的 HTML 和分析报告
    """
    optimizer = TfidfTextOptimizer()
    return optimizer.optimize_html(html, url)


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
