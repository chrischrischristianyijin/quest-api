from typing import List, Dict, Any, Optional, Tuple
import os
import logging
import re
from collections import defaultdict, Counter
import unicodedata

logger = logging.getLogger(__name__)

# 延迟导入，避免启动时的依赖问题
_SUMY_AVAILABLE = None
_NLTK_INITIALIZED = False

def _check_sumy_available() -> bool:
    """检查 Sumy 是否可用"""
    global _SUMY_AVAILABLE
    if _SUMY_AVAILABLE is not None:
        return _SUMY_AVAILABLE
    
    try:
        # 首先检查 numpy
        import numpy
        logger.debug(f"NumPy 版本: {numpy.__version__}")
        
        # 然后检查 sumy
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.summarizers.lex_rank import LexRankSummarizer
        from sumy.summarizers.text_rank import TextRankSummarizer
        _SUMY_AVAILABLE = True
        logger.info("Sumy 库加载成功")
        return True
    except ImportError as e:
        _SUMY_AVAILABLE = False
        logger.warning(f"Sumy 库不可用 (这是正常的，系统会使用简单的文本筛选): {e}")
        return False
    except Exception as e:
        _SUMY_AVAILABLE = False
        logger.warning(f"Sumy 库检查失败 (这是正常的，系统会使用简单的文本筛选): {e}")
        return False


def _ensure_nltk_data():
    """确保 NLTK 数据已下载"""
    global _NLTK_INITIALIZED
    if _NLTK_INITIALIZED:
        return
    
    try:
        import nltk
        # 尝试使用 punkt，如果失败则下载
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            logger.info("下载 NLTK punkt 数据...")
            nltk.download('punkt', quiet=True)
        
        # 尝试下载中文停用词（如果需要）
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            logger.info("下载 NLTK stopwords 数据...")
            nltk.download('stopwords', quiet=True)
            
        _NLTK_INITIALIZED = True
        logger.info("NLTK 数据初始化完成")
    except Exception as e:
        logger.warning(f"NLTK 数据初始化失败: {e}")


def _detect_language(text: str) -> str:
    """简单的语言检测"""
    try:
        # 计算中文字符比例
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(re.sub(r'\s+', '', text))
        
        if total_chars == 0:
            return "english"
        
        chinese_ratio = chinese_chars / total_chars
        
        # 如果中文字符超过20%，认为是中文
        if chinese_ratio > 0.2:
            return "chinese"
        else:
            return "english"
    except Exception:
        return "english"


def _clean_and_split_paragraphs(text: str) -> List[str]:
    """清理文本并分割段落"""
    try:
        if not text or not text.strip():
            return []
        
        # 规范化Unicode
        text = unicodedata.normalize('NFKC', text)
        
        # 按双换行分割段落
        paragraphs = re.split(r'\n\s*\n', text.strip())
        
        # 清理每个段落
        cleaned_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 合并段落内的换行
            para = re.sub(r'\n+', ' ', para)
            # 压缩多余空格
            para = re.sub(r'\s+', ' ', para)
            
            # 过滤太短的段落（少于20个字符）
            if len(para) >= 20:
                cleaned_paragraphs.append(para)
        
        return cleaned_paragraphs
    except Exception as e:
        logger.warning(f"段落分割失败: {e}")
        return []


def _extract_key_sentences_sumy(
    text: str, 
    sentence_count: int = 8,
    algorithm: str = "lexrank"
) -> List[str]:
    """使用 Sumy 提取关键句"""
    try:
        if not _check_sumy_available():
            return []
        
        _ensure_nltk_data()
        
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.summarizers.lex_rank import LexRankSummarizer
        from sumy.summarizers.text_rank import TextRankSummarizer
        
        # 检测语言
        language = _detect_language(text)
        logger.info(f"检测到语言: {language}")
        
        # 创建解析器
        parser = PlaintextParser.from_string(text, Tokenizer(language))
        
        # 选择摘要算法
        if algorithm.lower() == "textrank":
            summarizer = TextRankSummarizer()
        else:  # 默认使用 lexrank
            summarizer = LexRankSummarizer()
        
        # 设置停用词（如果可用）
        try:
            if language == "english":
                summarizer.stop_words = "english"
            elif language == "chinese":
                # 中文停用词处理（Sumy对中文支持有限）
                pass
        except Exception:
            pass
        
        # 提取关键句
        sentences = summarizer(parser.document, sentence_count)
        
        # 转换为字符串列表
        key_sentences = [str(sentence) for sentence in sentences]
        
        logger.info(f"Sumy 提取了 {len(key_sentences)} 个关键句")
        return key_sentences
        
    except Exception as e:
        logger.warning(f"Sumy 关键句提取失败: {e}")
        return []


def _map_sentences_to_paragraphs(
    key_sentences: List[str], 
    paragraphs: List[str]
) -> Dict[int, int]:
    """将关键句映射到段落，返回 {段落索引: 命中次数}"""
    try:
        paragraph_scores = defaultdict(int)
        
        for sentence in key_sentences:
            sentence_clean = re.sub(r'\s+', ' ', sentence.strip().lower())
            if not sentence_clean:
                continue
            
            # 在每个段落中查找这个句子
            for para_idx, paragraph in enumerate(paragraphs):
                para_clean = re.sub(r'\s+', ' ', paragraph.strip().lower())
                
                # 检查句子是否在段落中（允许部分匹配）
                if sentence_clean in para_clean:
                    paragraph_scores[para_idx] += 1
                    continue
                
                # 更宽松的匹配：检查句子的主要词汇是否在段落中
                sentence_words = set(re.findall(r'\w+', sentence_clean))
                para_words = set(re.findall(r'\w+', para_clean))
                
                if sentence_words and para_words:
                    # 计算词汇重叠比例
                    overlap = len(sentence_words & para_words)
                    overlap_ratio = overlap / len(sentence_words)
                    
                    # 如果重叠比例超过60%，认为匹配
                    if overlap_ratio > 0.6:
                        paragraph_scores[para_idx] += 0.5
        
        return dict(paragraph_scores)
        
    except Exception as e:
        logger.warning(f"句子到段落映射失败: {e}")
        return {}


def _create_preserve_mode_content(
    paragraphs: List[str],
    key_sentences: List[str],
    paragraph_scores: Dict[int, int],
    preserve_ratio: float = 0.8
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    保存模式：保留大部分原文，但标记重要句子
    
    Args:
        paragraphs: 原始段落列表
        key_sentences: 关键句子列表
        paragraph_scores: 段落评分
        preserve_ratio: 保留比例（0.8 表示保留 80% 的段落）
    
    Returns:
        (processed_text, paragraphs_info)
    """
    try:
        # 计算要保留的段落数量
        total_paragraphs = len(paragraphs)
        keep_count = max(1, int(total_paragraphs * preserve_ratio))
        
        # 获取有评分的段落（包含关键句子的段落）
        scored_paragraphs = set(paragraph_scores.keys())
        
        # 选择策略：优先保留有评分的段落，然后按顺序保留其他段落
        selected_indices = set()
        
        # 1. 添加所有有评分的段落
        selected_indices.update(scored_paragraphs)
        
        # 2. 如果还需要更多段落，按原始顺序添加
        if len(selected_indices) < keep_count:
            for i in range(total_paragraphs):
                if len(selected_indices) >= keep_count:
                    break
                selected_indices.add(i)
        
        # 3. 如果有评分的段落太多，按评分排序，保留评分最高的
        if len(selected_indices) > keep_count:
            # 按评分排序，保留 Top 段落
            sorted_by_score = sorted(
                [(idx, paragraph_scores.get(idx, 0)) for idx in selected_indices],
                key=lambda x: x[1],
                reverse=True
            )
            selected_indices = set([idx for idx, _ in sorted_by_score[:keep_count]])
        
        # 构建结果
        processed_parts = []
        paragraphs_info = []
        
        for i in range(total_paragraphs):
            if i in selected_indices:
                paragraph = paragraphs[i]
                score = paragraph_scores.get(i, 0)
                is_key = score > 0
                
                # 如果是关键段落，可以添加标记（可选）
                if is_key:
                    # 这里可以添加重要性标记，但为了保持原文完整性，暂时不添加
                    processed_parts.append(paragraph)
                else:
                    processed_parts.append(paragraph)
                
                paragraphs_info.append({
                    "index": i,
                    "score": score,
                    "length": len(paragraph),
                    "is_key": is_key,
                    "included": True
                })
            else:
                paragraphs_info.append({
                    "index": i,
                    "score": paragraph_scores.get(i, 0),
                    "length": len(paragraphs[i]),
                    "is_key": False,
                    "included": False
                })
        
        processed_text = "\n\n".join(processed_parts)
        
        logger.info(f"保存模式处理完成: {total_paragraphs} → {len(processed_parts)} 段落 "
                  f"(保留率: {len(processed_parts)/total_paragraphs:.1%})")
        
        return processed_text, paragraphs_info
        
    except Exception as e:
        logger.warning(f"保存模式处理失败: {e}")
        # 回退：返回所有段落
        processed_text = "\n\n".join(paragraphs)
        paragraphs_info = [
            {"index": i, "score": paragraph_scores.get(i, 0), "length": len(para), 
             "is_key": paragraph_scores.get(i, 0) > 0, "included": True}
            for i, para in enumerate(paragraphs)
        ]
        return processed_text, paragraphs_info


def _get_top_k_paragraphs_with_context(
    paragraphs: List[str],
    paragraph_scores: Dict[int, int],
    k: int = 4,
    context_window: int = 1
) -> List[Tuple[int, str, float]]:
    """获取 Top-K 段落，包含上下文窗口"""
    try:
        if not paragraph_scores:
            # 如果没有评分，返回前K个段落
            return [(i, para, 0.0) for i, para in enumerate(paragraphs[:k])]
        
        # 按分数排序段落
        sorted_paragraphs = sorted(
            paragraph_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # 取前K个
        top_k_indices = [idx for idx, _ in sorted_paragraphs[:k]]
        
        # 添加上下文窗口
        extended_indices = set()
        for idx in top_k_indices:
            # 添加当前段落
            extended_indices.add(idx)
            # 添加前后context_window个段落
            for offset in range(-context_window, context_window + 1):
                new_idx = idx + offset
                if 0 <= new_idx < len(paragraphs):
                    extended_indices.add(new_idx)
        
        # 按原始顺序排序
        final_indices = sorted(extended_indices)
        
        # 构建结果
        result = []
        for idx in final_indices:
            score = paragraph_scores.get(idx, 0.0)
            result.append((idx, paragraphs[idx], score))
        
        logger.info(f"选择了 {len(result)} 个段落 (Top-{k} + 上下文)")
        return result
        
    except Exception as e:
        logger.warning(f"Top-K 段落选择失败: {e}")
        return [(i, para, 0.0) for i, para in enumerate(paragraphs[:k])]


def extract_key_content_with_sumy(
    text: str,
    max_sentences: int = 8,
    top_k_paragraphs: int = 4,
    context_window: int = 1,
    algorithm: str = "lexrank",
    preserve_mode: str = "balanced"  # "strict", "balanced", "preserve"
) -> Optional[Dict[str, Any]]:
    """
    使用 Sumy 提取关键内容段落（作为预处理步骤）
    
    Args:
        text: 输入文本
        max_sentences: 最大关键句数量
        top_k_paragraphs: 选择的顶级段落数量
        context_window: 上下文窗口大小
        algorithm: 摘要算法 ("lexrank" 或 "textrank")
        preserve_mode: 保存模式
            - "strict": 严格模式，仅保存 Top-K 段落
            - "balanced": 平衡模式，Top-K + 上下文窗口（默认）
            - "preserve": 保存模式，标记重要句子但保留更多原文
    
    Returns:
        包含提取结果的字典，或 None（如果失败）
        {
            "processed_text": str,          # 提取后的文本
            "original_length": int,         # 原始文本长度
            "processed_length": int,        # 处理后文本长度
            "compression_ratio": float,     # 压缩比例
            "method": str,                  # 处理方法
            "key_sentences": list,          # 关键句子列表
            "paragraphs_info": list,        # 段落信息
            "preserve_mode": str            # 使用的保存模式
        }
    """
    try:
        if not text or not text.strip():
            return None
        
        if not _check_sumy_available():
            logger.warning("Sumy 不可用，使用简单段落筛选")
            # 回退到简单的段落筛选
            paragraphs = _clean_and_split_paragraphs(text)
            if not paragraphs:
                return None
            
            # 选择前几个段落，控制总长度
            max_length = int(os.getenv('SUMY_FALLBACK_MAX_LENGTH', '100000'))
            selected = []
            current_length = 0
            
            for para in paragraphs:
                if current_length + len(para) > max_length:
                    break
                selected.append(para)
                current_length += len(para)
            
            processed_text = "\n\n".join(selected)
            return {
                "processed_text": processed_text,
                "original_length": len(text),
                "processed_length": len(processed_text),
                "compression_ratio": len(processed_text) / len(text) if text else 0,
                "method": "fallback_simple",
                "paragraphs_count": len(selected),
                "key_sentences_count": 0,
                "algorithm": "none",
                "preserve_mode": preserve_mode,
                "key_sentences": [],
                "paragraphs_info": [
                    {"index": i, "score": 0.0, "length": len(para), 
                     "is_key": False, "included": True}
                    for i, para in enumerate(selected)
                ]
            }
        
        logger.info(f"开始 Sumy 摘要生成，算法: {algorithm}")
        
        # 1. 分割段落
        paragraphs = _clean_and_split_paragraphs(text)
        if not paragraphs:
            logger.warning("没有有效段落，跳过 Sumy 摘要")
            return None
        
        logger.info(f"分割得到 {len(paragraphs)} 个段落")
        
        # 2. 提取关键句
        key_sentences = _extract_key_sentences_sumy(
            text, 
            sentence_count=max_sentences,
            algorithm=algorithm
        )
        
        if not key_sentences:
            logger.warning("未提取到关键句，使用前几个段落")
            # 回退策略：直接使用前几个段落
            selected_paragraphs = paragraphs[:top_k_paragraphs]
            processed_text = "\n\n".join(selected_paragraphs)
            
            original_length = len(text)
            processed_length = len(processed_text)
            compression_ratio = processed_length / original_length if original_length > 0 else 0.0
            
            return {
                "processed_text": processed_text,
                "original_length": original_length,
                "processed_length": processed_length,
                "compression_ratio": compression_ratio,
                "method": "fallback_first_k",
                "paragraphs_count": len(selected_paragraphs),
                "key_sentences_count": 0,
                "algorithm": algorithm,
                "paragraphs_info": [
                    {"index": i, "score": 0.0, "length": len(para)}
                    for i, para in enumerate(selected_paragraphs)
                ]
            }
        
        # 3. 映射关键句到段落
        paragraph_scores = _map_sentences_to_paragraphs(key_sentences, paragraphs)
        
        # 4. 根据保存模式处理内容
        if preserve_mode == "preserve":
            # 保存模式：保留更多原文，标记重要句子
            preserve_ratio = float(os.getenv('SUMY_PRESERVE_RATIO', '0.5'))
            processed_text, paragraphs_info = _create_preserve_mode_content(
                paragraphs, key_sentences, paragraph_scores, preserve_ratio
            )
            method = "sumy_preserve"
        else:
            # 传统模式：Top-K 段落选择
            top_paragraphs = _get_top_k_paragraphs_with_context(
                paragraphs,
                paragraph_scores,
                k=top_k_paragraphs,
                context_window=context_window if preserve_mode == "balanced" else 0
            )
            
            # 构建处理后的文本
            processed_parts = []
            for idx, paragraph, score in top_paragraphs:
                processed_parts.append(paragraph)
            
            processed_text = "\n\n".join(processed_parts)
            
            # 构建段落信息
            paragraphs_info = [
                {"index": idx, "score": score, "length": len(para), 
                 "is_key": score > 0, "included": True}
                for idx, para, score in top_paragraphs
            ]
            
            method = f"sumy_{preserve_mode}"
        
        # 6. 计算压缩统计
        original_length = len(text)
        processed_length = len(processed_text)
        compression_ratio = processed_length / original_length if original_length > 0 else 0.0
        
        # 7. 返回结果
        return {
            "processed_text": processed_text,
            "original_length": original_length,
            "processed_length": processed_length,
            "compression_ratio": compression_ratio,
            "method": method,
            "paragraphs_count": len([p for p in paragraphs_info if p.get("included", True)]),
            "key_sentences_count": len(key_sentences),
            "algorithm": algorithm,
            "preserve_mode": preserve_mode,
            "key_sentences": key_sentences,  # 新增：关键句子列表
            "paragraph_scores": paragraph_scores,
            "paragraphs_info": paragraphs_info
        }
        
    except Exception as e:
        logger.error(f"Sumy 摘要生成失败: {e}")
        return None


def _is_enabled() -> bool:
    """检查 Sumy 内容预处理是否启用"""
    try:
        return (os.getenv('SUMY_PREPROCESSING_ENABLED', 'true').lower() in ('1', 'true', 'yes', 'on'))
    except Exception:
        return True  # 默认启用


# 环境变量配置说明
SUMY_CONFIG_HELP = """
Sumy 内容预处理配置环境变量:

SUMY_PREPROCESSING_ENABLED=1        # 启用 Sumy 内容预处理（默认启用）
SUMY_MAX_SENTENCES=8                # 最大关键句数量
SUMY_TOP_K_PARAGRAPHS=4             # Top-K 段落数量
SUMY_CONTEXT_WINDOW=1               # 上下文窗口大小
SUMY_ALGORITHM=lexrank              # 摘要算法 (lexrank/textrank)
SUMY_PRESERVE_MODE=preserve         # 保存模式 (strict/balanced/preserve)
SUMY_PRESERVE_RATIO=0.8             # 保存模式下的保留比例 (0.1-1.0)
SUMY_MIN_PARAGRAPH_LENGTH=20        # 最小段落长度

保存模式说明:
- strict: 严格模式，仅保存 Top-K 段落
- balanced: 平衡模式，Top-K + 上下文窗口（默认）
- preserve: 保存模式，标记重要句子但保留更多原文（推荐用于保存更多内容）
"""
