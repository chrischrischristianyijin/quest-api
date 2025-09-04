#!/usr/bin/env python3
"""
测试 NLTK 数据下载修复
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_nltk_data():
    """测试 NLTK 数据是否正确下载"""
    print("🧪 测试 NLTK 数据下载...")
    
    try:
        import nltk
        
        # 检查 punkt
        try:
            nltk.data.find('tokenizers/punkt')
            print("✅ punkt 数据已存在")
        except LookupError:
            print("📥 下载 punkt 数据...")
            nltk.download('punkt', quiet=True)
            print("✅ punkt 数据下载完成")
        
        # 检查 punkt_tab
        try:
            nltk.data.find('tokenizers/punkt_tab')
            print("✅ punkt_tab 数据已存在")
        except LookupError:
            print("📥 下载 punkt_tab 数据...")
            nltk.download('punkt_tab', quiet=True)
            print("✅ punkt_tab 数据下载完成")
        
        # 检查 stopwords
        try:
            nltk.data.find('corpora/stopwords')
            print("✅ stopwords 数据已存在")
        except LookupError:
            print("📥 下载 stopwords 数据...")
            nltk.download('stopwords', quiet=True)
            print("✅ stopwords 数据下载完成")
        
        print("\n🎉 所有 NLTK 数据检查完成！")
        
        # 测试 Sumy 是否能正常工作
        print("\n🧪 测试 Sumy 功能...")
        try:
            from app.utils.sumy_summarizer import extract_key_content_with_sumy
            
            test_text = """
            This is a test document. It contains multiple sentences.
            The second sentence provides more information.
            The third sentence adds additional context.
            This sentence is important for understanding the topic.
            Finally, this sentence concludes the test document.
            """
            
            result = extract_key_content_with_sumy(test_text)
            print(f"✅ Sumy 测试成功！提取了 {len(result.get('key_sentences', []))} 个关键句")
            print(f"📊 压缩率: {result.get('compression_ratio', 0):.1%}")
            
        except Exception as e:
            print(f"❌ Sumy 测试失败: {e}")
        
    except Exception as e:
        print(f"❌ NLTK 测试失败: {e}")

if __name__ == "__main__":
    test_nltk_data()
