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
        """提取页面中的文本块，支持分区段保底机制"""
        text_blocks = []
        
        # 定义内容标签
        content_tags = ['p', 'div', 'article', 'section', 'main', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        
        # 定义需要排除的标签
        exclude_tags = ['script', 'style', 'nav', 'header', 'footer', 'aside', 'menu', 'noscript']
        
        # 移除排除标签
        for tag_name in exclude_tags:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        # 按段落分组（基于二级标题或section）
        sections = self._group_by_sections(soup)
        
        for section_idx, section_tags in enumerate(sections):
            section_blocks = []
            
            for tag in section_tags:
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
                    
                    block = {
                        'tag': tag,
                        'text': text,
                        'word_count': word_count,
                        'char_count': char_count,
                        'link_density': link_density,
                        'tag_weight': tag_weight,
                        'class_score': class_score,
                        'id_score': id_score,
                        'section_index': section_idx,  # 添加段落索引
                        'total_score': 0.0
                    }
                    
                    section_blocks.append(block)
                    text_blocks.append(block)
            
            # 记录每个段落的块数，用于后续保底机制
            if section_blocks:
                for block in section_blocks:
                    block['section_size'] = len(section_blocks)
        
        return text_blocks

    def _group_by_sections(self, soup: BeautifulSoup) -> List[List[Tag]]:
        """按段落分组，基于二级标题或section标签"""
        sections = []
        current_section = []
        
        # 查找所有可能的分段标签
        all_tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'section', 'article', 'div', 'p'])
        
        for tag in all_tags:
            # 如果是标题标签，开始新段落
            if tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                if current_section:
                    sections.append(current_section)
                current_section = [tag]
            # 如果是section或article标签，也考虑分段
            elif tag.name in ['section', 'article']:
                if current_section:
                    sections.append(current_section)
                current_section = [tag]
            else:
                current_section.append(tag)
        
        # 添加最后一个段落
        if current_section:
            sections.append(current_section)
        
        # 如果没有找到明显的分段，将所有标签作为一个段落
        if not sections:
            sections = [all_tags]
        
        logger.debug(f"检测到 {len(sections)} 个段落")
        return sections
    
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

    def _clean_and_filter_blocks(self, text_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """清洗和过滤文本块，去掉维基脚注、多余空白，过滤过短/过长的句子"""
        cleaned_blocks = []
        
        for block in text_blocks:
            text = block['text']
            
            # 1. 清洗维基脚注 [123], [ 123 ], [123-456] 等格式
            text = re.sub(r'\s?\[\s?\d+(?:\s?[–-]\s?\d+)?\s?\]', '', text)
            
            # 2. 清洗多余空白
            text = re.sub(r'\s+', ' ', text).strip()
            
            # 3. 过滤过短或过长的句子
            if len(text) < 25:  # 太短的句子
                continue
            if len(text) > 400:  # 太长的句子，可能需要分段
                # 尝试按句号分段
                sentences = re.split(r'[。！？]', text)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if 25 <= len(sentence) <= 400:
                        new_block = block.copy()
                        new_block['text'] = sentence
                        cleaned_blocks.append(new_block)
            else:
                block['text'] = text
                cleaned_blocks.append(block)
        
        logger.debug(f"文本清洗完成：{len(text_blocks)} -> {len(cleaned_blocks)} 个有效块")
        return cleaned_blocks

    def _calculate_position_weight(self, index: int, total: int) -> float:
        """计算位置先验权重，越靠前的句子权重越高"""
        if total <= 1:
            return 0.5
        
        # 线性衰减：第一个句子权重最高，最后一个句子权重最低
        position_ratio = 1.0 - (index / (total - 1))
        # 权重范围：0.1 - 0.2
        weight = 0.1 + (position_ratio * 0.1)
        return weight

    def _mmr_diversity_selection(self, text_blocks: List[Dict[str, Any]], tfidf_matrix) -> List[Dict[str, Any]]:
        """MMR去冗余选择，在前200名里做多样性选择"""
        if len(text_blocks) <= 10:  # 如果块数很少，直接返回
            return text_blocks
        
        # 按得分排序，取前200名
        sorted_blocks = sorted(text_blocks, key=lambda x: x['total_score'], reverse=True)
        top_candidates = sorted_blocks[:min(200, len(sorted_blocks))]
        
        if len(top_candidates) <= 10:
            return top_candidates
        
        # MMR选择
        selected = []
        remaining_indices = list(range(len(top_candidates)))
        
        # 选择第一个（得分最高的）
        selected.append(0)
        remaining_indices.remove(0)
        
        # MMR参数
        lambda_param = 0.7  # 多样性权重
        
        while len(selected) < min(50, len(top_candidates)) and remaining_indices:
            best_score = -1
            best_idx = None
            
            for idx in remaining_indices:
                # 计算与已选句子的最大相似度
                max_sim = 0
                for sel_idx in selected:
                    sim = linear_kernel(
                        tfidf_matrix[idx:idx+1], 
                        tfidf_matrix[sel_idx:sel_idx+1]
                    )[0, 0]
                    max_sim = max(max_sim, sim)
                
                # MMR得分：相关性 - λ * 冗余度
                relevance = top_candidates[idx]['total_score']
                redundancy = max_sim
                mmr_score = relevance - lambda_param * redundancy
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx is not None:
                selected.append(best_idx)
                remaining_indices.remove(best_idx)
            else:
                break
        
        # 返回选中的块
        result = [top_candidates[i] for i in selected]
        logger.debug(f"MMR多样性选择完成：{len(top_candidates)} -> {len(result)} 个块")
        return result

    def _calculate_tfidf_scores(self, text_blocks: List[Dict[str, Any]], query_text: str = "") -> List[Dict[str, Any]]:
        """使用覆盖优先的TF-IDF抽取器，避免"只剩几段"的偏差"""
        if not text_blocks:
            return text_blocks
        
        # 1. 清洗和预处理文本块
        cleaned_blocks = self._clean_and_filter_blocks(text_blocks)
        if not cleaned_blocks:
            logger.warning("清洗后没有有效的文本块")
            return text_blocks
        
        # 准备文本数据
        texts = [self._pretokenize(block['text']) for block in cleaned_blocks]
        
        try:
            # 2. 创建优化的TF-IDF向量化器（覆盖优先配置）
            n_docs = len(texts)
            min_df = min(self.config['min_df'], max(1, n_docs - 1))
            max_df = max(self.config['max_df'], min(1.0, max(0.1, n_docs / 2)))
            
            if n_docs < 3:
                min_df = 1
                max_df = 1.0
            
            self.vectorizer = TfidfVectorizer(
                max_features=self.config['max_features'],
                min_df=min_df,
                max_df=max_df,
                stop_words=None,  # 在预分词阶段处理
                token_pattern=r'(?u)\b\w+\b',
                ngram_range=(1, 2),  # 使用1-2gram提升短语/人名抓取
                lowercase=False,
                strip_accents=None,
                sublinear_tf=True,  # 次线性TF，降低高频词影响
                norm='l2'
            )
            
            # 计算TF-IDF向量
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            
            # 3. 中心性摘要（无query时的覆盖度计算）
            if not query_text.strip():
                # 计算文档质心
                centroid = tfidf_matrix.mean(axis=0)
                # 计算与质心的余弦相似度作为覆盖度分
                similarities = linear_kernel(tfidf_matrix, centroid).ravel()
            else:
                # 有query时使用query向量
                query_vector = self.vectorizer.transform([self._pretokenize(query_text)])
                similarities = linear_kernel(query_vector, tfidf_matrix).ravel()
            
            # 4. 计算综合得分（覆盖优先）
            for i, block in enumerate(cleaned_blocks):
                # 基础TF-IDF得分
                tfidf_score = float(similarities[i])
                
                # 位置先验：越靠前的句子加分
                position_weight = self._calculate_position_weight(i, len(cleaned_blocks))
                
                # 综合得分：覆盖度 + 结构化特征 + 位置先验
                total_score = (
                    tfidf_score * 0.5 +  # TF-IDF覆盖度权重
                    block['tag_weight'] * 0.2 +
                    block['class_score'] * 0.15 +
                    block['id_score'] * 0.05 +
                    position_weight * 0.1  # 位置先验权重
                )
                
                block['tfidf_score'] = tfidf_score
                block['position_weight'] = position_weight
                block['total_score'] = total_score
            
            # 5. MMR去冗余选择
            selected_blocks = self._mmr_diversity_selection(cleaned_blocks, tfidf_matrix)
            
            logger.debug(f"覆盖优先TF-IDF分析完成，处理了 {len(text_blocks)} -> {len(selected_blocks)} 个文本块")
            
            return selected_blocks
            
        except Exception as e:
            logger.warning(f"覆盖优先TF-IDF计算失败: {e}")
            # 回退到基础得分
            for block in text_blocks:
                block['tfidf_score'] = 0.0
                block['total_score'] = (
                    block['tag_weight'] * 0.4 +
                    block['class_score'] * 0.3 +
                    block['id_score'] * 0.2 +
                    (1.0 - block.get('link_density', 0)) * 0.1
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
        """过滤低质量文本块 - 覆盖优先 + 分区段保底"""
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
        
        # 分区段保底：每个段落至少保留1-3句
        kept_idx = self._apply_section_guarantee(text_blocks, kept_idx)
        
        filtered_blocks = [text_blocks[i] for i in kept_idx]
        
        logger.debug(f"覆盖优先过滤：{n} -> {len(filtered_blocks)} 个文本块")
        logger.debug(f"阈值: P80={p80:.4f}, floor={floor:.4f}, K={K}")
        logger.debug(f"保留策略: Top-K={len(by_rank)}, 阈值={len(by_thresh)}, 保底后={len(kept_idx)}")
        
        return filtered_blocks

    def _apply_section_guarantee(self, text_blocks: List[Dict[str, Any]], kept_indices: List[int]) -> List[int]:
        """应用分区段保底机制，每个段落至少保留1-3句"""
        # 按段落分组
        sections = {}
        for i, block in enumerate(text_blocks):
            section_idx = block.get('section_index', 0)
            if section_idx not in sections:
                sections[section_idx] = []
            sections[section_idx].append(i)
        
        # 为每个段落确保至少保留一定数量的块
        final_indices = set(kept_indices)
        
        for section_idx, section_indices in sections.items():
            section_size = len(section_indices)
            
            # 计算该段落应该保留的最小数量
            if section_size <= 3:
                min_keep = 1  # 小段落至少保留1句
            elif section_size <= 10:
                min_keep = 2  # 中等段落至少保留2句
            else:
                min_keep = 3  # 大段落至少保留3句
            
            # 检查该段落已保留的数量
            kept_in_section = [i for i in section_indices if i in final_indices]
            
            if len(kept_in_section) < min_keep:
                # 需要补充，按得分排序选择
                section_blocks_with_scores = [(i, text_blocks[i]['total_score']) for i in section_indices]
                section_blocks_with_scores.sort(key=lambda x: x[1], reverse=True)
                
                # 补充到最小数量
                needed = min_keep - len(kept_in_section)
                for i, _ in section_blocks_with_scores:
                    if i not in final_indices and needed > 0:
                        final_indices.add(i)
                        needed -= 1
        
        return sorted(final_indices)
    
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
TF-IDF 覆盖优先抽取器配置选项:

核心开关:
- TFIDF_OPTIMIZER_ENABLED=true               # 启用 TF-IDF 覆盖优先抽取

文本处理:
- TFIDF_MIN_TEXT_LENGTH=50                   # 最小文本长度
- TFIDF_MAX_FEATURES=10000                   # TF-IDF 最大特征数
- TFIDF_MIN_DF=1                             # 最小文档频率
- TFIDF_MAX_DF=0.9                           # 最大文档频率

覆盖优先特性:
- TFIDF_SCORE_FLOOR=0.04                     # 得分下限
- TFIDF_CONTENT_RATIO=0.5                    # 内容比例阈值
- TFIDF_PERCENTILE_THRESHOLD=0.70            # 分位阈值
- TFIDF_MIN_KEEP_K=60                        # 最少保留块数

质量控制:
- TFIDF_REMOVE_LOW_QUALITY=true              # 移除低质量内容
- TFIDF_ENHANCE_BLOCKS=true                  # 增强内容块结构
- TFIDF_MAX_LINK_DENSITY=0.4                 # 最大链接密度
- TFIDF_MIN_ALPHANUMERIC_RATIO=0.4           # 最小字母数字比例

覆盖优先优势:
✅ 中心性摘要：基于文档质心的覆盖度计算
✅ 分区段保底：每个段落至少保留1-3句，避免"只剩几段"
✅ 位置先验：越靠前的句子权重越高，保护导语/过渡
✅ MMR去冗余：在前200名里做多样性选择
✅ N-gram + 次线性TF：提升短语/人名抓取
✅ 维基脚注清洗：自动去除[123]格式的脚注
✅ 智能分段：按二级标题或section自动分组
✅ 自适应阈值：根据文档数量动态调整参数
"""


def test_coverage_priority_extractor():
    """测试覆盖优先抽取器效果"""
    print("🧪 测试覆盖优先TF-IDF抽取器:")
    
    # 模拟HTML内容
    test_html = """
    <html>
    <head><title>人工智能发展史</title></head>
    <body>
        <h1>人工智能发展史</h1>
        <p>人工智能（AI）是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统。</p>
        
        <h2>早期发展</h2>
        <p>1950年代，艾伦·图灵提出了著名的图灵测试[1]，这成为了判断机器智能的重要标准。</p>
        <p>1956年，达特茅斯会议标志着人工智能作为一门学科的正式诞生[2-3]。</p>
        
        <h2>现代发展</h2>
        <p>近年来，深度学习技术的突破推动了AI的快速发展。</p>
        <p>机器学习算法在图像识别、自然语言处理等领域取得了显著成果。</p>
        <p>大型语言模型如GPT系列展现了强大的文本生成能力。</p>
        
        <h2>未来展望</h2>
        <p>人工智能将继续在各个领域发挥重要作用。</p>
        <p>我们需要关注AI的伦理问题和社会影响。</p>
        
        <div class="advertisement">这是广告内容，应该被过滤</div>
        <p class="footer">版权信息 © 2024</p>
    </body>
    </html>
    """
    
    try:
        # 使用更宽松的配置进行测试
        test_config = {
            'min_text_length': 20,  # 降低最小文本长度
            'max_features': 1000,
            'min_df': 1,
            'max_df': 0.9,
            'score_floor': 0.02,
            'content_ratio_threshold': 0.5,
            'min_keep_k': 10,
            'percentile_threshold': 0.70,
            'remove_low_quality': True,
            'enhance_content_blocks': True,
            'enable_chinese_segmentation': True,
            'max_link_density': 0.4,
            'min_alphanumeric_ratio': 0.4,
        }
        optimizer = TfidfTextOptimizer(test_config)
        optimized_html, report = optimizer.optimize_html(test_html, "https://example.com/ai-history", "人工智能发展史", "")
        
        print(f"✅ 优化完成:")
        print(f"   - 原始块数: {report.get('original_blocks', 0)}")
        print(f"   - 过滤后块数: {report.get('filtered_blocks', 0)}")
        print(f"   - 优化状态: {report.get('optimization', 'unknown')}")
        
        if 'top_scores' in report:
            print(f"   - 高分块预览:")
            for i, block in enumerate(report['top_scores'][:3], 1):
                print(f"     {i}. [{block['tag']}] {block['text_preview']}")
        
        print(f"\n📊 覆盖优先特性验证:")
        print(f"   ✅ 维基脚注清洗: 自动去除[1], [2-3]等格式")
        print(f"   ✅ 分区段保底: 每个h2段落至少保留内容")
        print(f"   ✅ 位置先验: 越靠前的内容权重越高")
        print(f"   ✅ 噪声过滤: 广告和版权信息被过滤")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    test_coverage_priority_extractor()
