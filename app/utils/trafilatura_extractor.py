"""
Trafilatura 正文提取器
用于替换原有的 BeautifulSoup + Readability + Curator 组合
"""

import logging
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

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
            "title": str,               # 标题
            "author": str,              # 作者
            "date": str,                # 发布日期
            "description": str,         # 描述
            "sitename": str,            # 站点名称
            "hostname": str,            # 主机名
            "language": str,            # 语言
            "source": str,              # 来源URL
            "categories": list,         # 分类
            "tags": list,               # 标签
            "fingerprint": str,         # 内容指纹
            "raw_text_length": int,     # 原始文本长度
            "comments_length": int,     # 评论长度
            "extraction_method": str    # 提取方法
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
        
        # 重置缓存（避免内存泄漏）
        reset_caches()
        
        # 配置提取选项
        config = use_config()
        config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
        config.set("DEFAULT", "MIN_EXTRACTED_SIZE", "200")  # 最小提取长度
        config.set("DEFAULT", "MIN_OUTPUT_SIZE", "100")     # 最小输出长度
        
        # 设置提取策略
        if favor_precision:
            config.set("DEFAULT", "MIN_EXTRACTED_COMM_SIZE", "10")
            config.set("DEFAULT", "MIN_DUPLCHECK_SIZE", "100")
        elif favor_recall:
            config.set("DEFAULT", "MIN_EXTRACTED_SIZE", "50")
            config.set("DEFAULT", "MIN_OUTPUT_SIZE", "25")
        
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
        
        # 提取元数据
        metadata = trafilatura.extract_metadata(html, fast=False, url=url)
        
        # 构建结果
        result = {
            "text": extracted_text.strip(),
            "title": metadata.title if metadata else None,
            "author": metadata.author if metadata else None,
            "date": metadata.date if metadata else None,
            "description": metadata.description if metadata else None,
            "sitename": metadata.sitename if metadata else None,
            "hostname": metadata.hostname if metadata else None,
            "language": metadata.language if metadata else None,
            "source": metadata.url if metadata else url,
            "categories": list(metadata.categories) if metadata and metadata.categories else [],
            "tags": list(metadata.tags) if metadata and metadata.tags else [],
            "fingerprint": metadata.fingerprint if metadata else None,
            "raw_text_length": len(extracted_text),
            "comments_length": 0,  # 暂时不支持评论长度统计
            "extraction_method": "trafilatura"
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
        
        logger.info(f"Trafilatura 提取成功: 文本长度={len(extracted_text)}, 标题='{result['title'][:50] if result['title'] else 'N/A'}'")
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

提取选项:
- TRAFILATURA_INCLUDE_COMMENTS=false          # 包含评论内容
- TRAFILATURA_INCLUDE_TABLES=true             # 包含表格内容
- TRAFILATURA_INCLUDE_FORMATTING=false        # 保留格式标记
- TRAFILATURA_DEDUPLICATE=true                # 去重复内容

策略选项:
- TRAFILATURA_FAVOR_PRECISION=true            # 优先精确度（更严格）
- TRAFILATURA_FAVOR_RECALL=false              # 优先召回率（更宽松）

推荐配置:
- 新闻文章: PRECISION=true, TABLES=true
- 博客内容: PRECISION=false, RECALL=true
- 学术论文: TABLES=true, FORMATTING=true
"""
