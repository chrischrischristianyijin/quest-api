"""
Trafilatura 正文提取器
用于替换原有的 BeautifulSoup + Readability + Curator 组合
"""

import logging
from typing import Dict, Any, Optional, Tuple
import os

logger = logging.getLogger(__name__)

# TF-IDF 预处理优化
_TFIDF_AVAILABLE = None

def _check_tfidf_available() -> bool:
    """检查 TF-IDF 优化器是否可用"""
    global _TFIDF_AVAILABLE
    if _TFIDF_AVAILABLE is not None:
        return _TFIDF_AVAILABLE
    
    try:
        from app.utils.tfidf_optimizer import optimize_html_with_tfidf, is_tfidf_enabled
        _TFIDF_AVAILABLE = True
        logger.info("TF-IDF 优化器加载成功")
        return True
    except ImportError as e:
        _TFIDF_AVAILABLE = False
        logger.warning(f"TF-IDF 优化器不可用: {e}")
        return False

# 延迟导入，避免启动时的依赖问题
_TRAFILATURA_AVAILABLE = None

def _check_trafilatura_available() -> bool:
    """检查 Trafilatura 是否可用"""
    global _TRAFILATURA_AVAILABLE
    if _TRAFILATURA_AVAILABLE is not None:
        return _TRAFILATURA_AVAILABLE
    
    try:
        import trafilatura
        _TRAFILATURA_AVAILABLE = True
        logger.info("Trafilatura 库加载成功")
        return True
    except ImportError as e:
        _TRAFILATURA_AVAILABLE = False
        logger.warning(f"Trafilatura 库不可用: {e}")
        return False

def extract_content_with_trafilatura(
    html: str, 
    url: str,
    include_comments: bool = False,
    include_tables: bool = True,
    include_formatting: bool = False,
    deduplicate: bool = True,
    favor_precision: bool = True,
    favor_recall: bool = False
) -> Optional[Dict[str, Any]]:
    """
    使用 Trafilatura 提取网页正文内容
    
    Args:
        html: HTML 内容
        url: 页面 URL
        include_comments: 是否包含评论
        include_tables: 是否包含表格
        include_formatting: 是否保留格式
        deduplicate: 是否去重
        favor_precision: 是否优先精确度（更严格的提取）
        favor_recall: 是否优先召回率（更宽松的提取）
    
    Returns:
        包含提取结果的字典，或 None（如果失败）
        {
            "text": str,                # 提取的正文
            "raw_text_length": int,     # 原始文本长度
            "comments_length": int,     # 评论长度
            "extraction_method": str,   # 提取方法
            "tfidf_optimization": dict  # TF-IDF 优化报告
        }
    """
    try:
        if not _check_trafilatura_available():
            logger.warning("Trafilatura 不可用，跳过提取")
            return None
        
        import trafilatura
        from trafilatura.settings import use_config
        from trafilatura.meta import reset_caches
        
        logger.debug(f"开始 Trafilatura 正文提取: {url}")
        
        # 步骤 1: TF-IDF 预处理优化（可选）
        tfidf_report = {}
        if _check_tfidf_available():
            from app.utils.tfidf_optimizer import optimize_html_with_tfidf, is_tfidf_enabled
            if is_tfidf_enabled():
                logger.debug("启用 TF-IDF 预处理优化")
                # 从 URL 中提取标题作为查询
                title = url.split('/')[-1].replace('-', ' ').replace('_', ' ') if url else ""
                html, tfidf_report = optimize_html_with_tfidf(html, url, title, "")
                logger.debug(f"TF-IDF 优化结果: {tfidf_report.get('optimization', 'unknown')}")
        
        # 重置缓存（避免内存泄漏）
        reset_caches()
        
        # 配置提取选项 - 调整为更宽松的参数
        config = use_config()
        config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
        config.set("DEFAULT", "MIN_EXTRACTED_SIZE", "50")   # 降低最小提取长度
        config.set("DEFAULT", "MIN_OUTPUT_SIZE", "25")      # 降低最小输出长度
        
        # 设置提取策略 - 优先召回率
        if favor_recall:
            config.set("DEFAULT", "MIN_EXTRACTED_SIZE", "30")  # 进一步降低
            config.set("DEFAULT", "MIN_OUTPUT_SIZE", "15")     # 进一步降低
            config.set("DEFAULT", "MIN_EXTRACTED_COMM_SIZE", "5")
            config.set("DEFAULT", "MIN_DUPLCHECK_SIZE", "50")
        elif favor_precision:
            config.set("DEFAULT", "MIN_EXTRACTED_COMM_SIZE", "10")
            config.set("DEFAULT", "MIN_DUPLCHECK_SIZE", "100")
        
        # 提取正文内容
        extracted_text = trafilatura.extract(
            html,
            url=url,
            include_comments=include_comments,
            include_tables=include_tables,
            include_formatting=include_formatting,
            deduplicate=deduplicate,
            config=config,
            output_format='txt'  # 纯文本格式
        )
        
        if not extracted_text or not extracted_text.strip():
            logger.warning("Trafilatura 未提取到有效内容")
            return None
        
        # 构建结果（不提取元数据）
        result = {
            "text": extracted_text.strip(),
            "raw_text_length": len(extracted_text),
            "comments_length": 0,  # 暂时不支持评论长度统计
            "extraction_method": "trafilatura_with_tfidf" if tfidf_report.get('optimization') == 'success' else "trafilatura",
            "tfidf_optimization": tfidf_report  # TF-IDF 预处理报告
        }
        
        # 如果需要评论，单独提取
        if include_comments:
            try:
                comments = trafilatura.extract(
                    html,
                    url=url,
                    include_comments=True,
                    include_tables=False,
                    include_formatting=False,
                    deduplicate=deduplicate,
                    config=config,
                    output_format='txt',
                    only_with_metadata=False
                )
                if comments and comments != extracted_text:
                    result["comments_length"] = len(comments) - len(extracted_text)
            except Exception as e:
                logger.warning(f"评论提取失败: {e}")
        
        logger.info(f"Trafilatura 提取成功: 文本长度={len(extracted_text)}")
        return result
        
    except Exception as e:
        logger.error(f"Trafilatura 提取失败: {e}")
        return None

def is_trafilatura_enabled() -> bool:
    """检查是否启用 Trafilatura 提取"""
    return (
        _check_trafilatura_available() and 
        os.getenv('TRAFILATURA_ENABLED', 'true').lower() in ('1', 'true', 'yes', 'on')
    )

def get_trafilatura_config() -> Dict[str, Any]:
    """获取 Trafilatura 配置"""
    return {
        'include_comments': os.getenv('TRAFILATURA_INCLUDE_COMMENTS', 'false').lower() in ('1', 'true', 'yes'),
        'include_tables': os.getenv('TRAFILATURA_INCLUDE_TABLES', 'true').lower() in ('1', 'true', 'yes'),
        'include_formatting': os.getenv('TRAFILATURA_INCLUDE_FORMATTING', 'false').lower() in ('1', 'true', 'yes'),
        'deduplicate': os.getenv('TRAFILATURA_DEDUPLICATE', 'true').lower() in ('1', 'true', 'yes'),
        'favor_precision': os.getenv('TRAFILATURA_FAVOR_PRECISION', 'true').lower() in ('1', 'true', 'yes'),
        'favor_recall': os.getenv('TRAFILATURA_FAVOR_RECALL', 'false').lower() in ('1', 'true', 'yes'),
    }

# 配置说明
TRAFILATURA_CONFIG_HELP = """
Trafilatura 配置选项:

核心开关:
- TRAFILATURA_ENABLED=true                    # 启用 Trafilatura 提取

内容控制:
- TRAFILATURA_INCLUDE_COMMENTS=false          # 不包含评论（避免噪声）
- TRAFILATURA_INCLUDE_TABLES=true             # 包含表格（学术/报告类有用）
- TRAFILATURA_INCLUDE_FORMATTING=false        # 不保留格式标记（纯文本）
- TRAFILATURA_DEDUPLICATE=true                # 去重重复段落（新闻站点常见）

质量优化:
- TRAFILATURA_FAVOR_PRECISION=true            # 优先精确度（严格正文检测）
- TRAFILATURA_FAVOR_RECALL=false              # 不优先召回率（避免宽松模式）

严格模式:
- no_fallback=True                            # 失败就返回空，不降级到宽松模式

当前配置优势:
✅ 更严格的正文检测，减少噪声和广告
✅ 自动去重重复段落
✅ 避免评论和导航内容
✅ 纯文本输出，便于后续处理
✅ 严格模式确保内容质量

推荐配置（新闻/学术类）:
TRAFILATURA_ENABLED=true
TRAFILATURA_INCLUDE_COMMENTS=false
TRAFILATURA_INCLUDE_TABLES=true
TRAFILATURA_INCLUDE_FORMATTING=false
TRAFILATURA_DEDUPLICATE=true
TRAFILATURA_FAVOR_PRECISION=true
TRAFILATURA_FAVOR_RECALL=false
"""
