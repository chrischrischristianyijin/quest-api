#!/usr/bin/env python3
"""
设置 Sumy 和 NLTK 依赖
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def install_dependencies():
    """安装依赖"""
    try:
        import subprocess
        
        logger.info("安装 NumPy, Sumy 和 NLTK...")
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', 
            'numpy==1.26.4', 'sumy==0.11.0', 'nltk==3.8.1', 'scikit-learn==1.4.2'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("依赖安装成功")
        else:
            logger.error(f"依赖安装失败: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"安装依赖时出错: {e}")
        return False
    
    return True

def setup_nltk_data():
    """设置 NLTK 数据"""
    try:
        import nltk
        
        logger.info("下载 NLTK 数据...")
        
        # 下载 punkt tokenizer
        try:
            nltk.data.find('tokenizers/punkt')
            logger.info("punkt 数据已存在")
        except LookupError:
            logger.info("下载 punkt 数据...")
            nltk.download('punkt', quiet=True)
        
        # 下载停用词
        try:
            nltk.data.find('corpora/stopwords')
            logger.info("stopwords 数据已存在")
        except LookupError:
            logger.info("下载 stopwords 数据...")
            nltk.download('stopwords', quiet=True)
        
        logger.info("NLTK 数据设置完成")
        return True
        
    except Exception as e:
        logger.error(f"NLTK 数据设置失败: {e}")
        return False

def test_sumy_basic():
    """基本的 Sumy 功能测试"""
    try:
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.summarizers.lex_rank import LexRankSummarizer
        
        # 简单测试文本
        text = """
        This is the first paragraph. It contains some important information about artificial intelligence.
        
        This is the second paragraph. It discusses machine learning and its applications in various fields.
        
        This is the third paragraph. It talks about the future of AI and its potential impact on society.
        """
        
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LexRankSummarizer()
        
        sentences = summarizer(parser.document, 2)
        
        logger.info("Sumy 基本功能测试成功:")
        for sentence in sentences:
            logger.info(f"- {sentence}")
        
        return True
        
    except Exception as e:
        logger.error(f"Sumy 基本功能测试失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("开始设置 Sumy 环境...")
    
    # 1. 安装依赖
    if not install_dependencies():
        logger.error("依赖安装失败，退出")
        return False
    
    # 2. 设置 NLTK 数据
    if not setup_nltk_data():
        logger.error("NLTK 数据设置失败，退出")
        return False
    
    # 3. 基本功能测试
    if not test_sumy_basic():
        logger.error("Sumy 基本功能测试失败")
        return False
    
    logger.info("Sumy 环境设置完成！")
    
    # 4. 显示环境变量配置建议
    logger.info("\n推荐的环境变量配置:")
    logger.info("SUMY_SUMMARY_ENABLED=1")
    logger.info("SUMY_MAX_SENTENCES=8")
    logger.info("SUMY_TOP_K_PARAGRAPHS=4")
    logger.info("SUMY_CONTEXT_WINDOW=1")
    logger.info("SUMY_ALGORITHM=lexrank")
    logger.info("SUMMARY_ENABLED=1")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
