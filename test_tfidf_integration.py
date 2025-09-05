#!/usr/bin/env python3
"""
测试 TF-IDF + Trafilatura 集成
"""

import os
import sys
sys.path.append('.')

# 设置环境变量
os.environ['TFIDF_OPTIMIZER_ENABLED'] = 'true'
os.environ['TRAFILATURA_ENABLED'] = 'true'

def test_tfidf_integration():
    """测试 TF-IDF + Trafilatura 集成"""
    
    # 测试 HTML 内容
    test_html = """
    <html>
    <head>
        <title>测试文章</title>
        <meta name="description" content="这是一个测试文章">
    </head>
    <body>
        <!-- 导航噪声 -->
        <nav class="navigation">
            <a href="/">首页</a>
            <a href="/about">关于</a>
        </nav>
        
        <!-- 广告噪声 -->
        <div class="advertisement">
            <p>广告内容：购买我们的产品！</p>
            <p>特价优惠，限时抢购！</p>
        </div>
        
        <!-- 主要内容 -->
        <article class="content">
            <h1>人工智能的发展历程</h1>
            <p>人工智能（Artificial Intelligence，AI）是计算机科学的一个重要分支，旨在创建能够执行通常需要人类智能的任务的系统。</p>
            <p>从1956年达特茅斯会议开始，人工智能经历了多次起伏。早期的符号主义方法试图通过逻辑推理来模拟人类思维。</p>
            <p>近年来，深度学习的突破性进展推动了人工智能的快速发展，特别是在图像识别、自然语言处理等领域取得了显著成果。</p>
        </article>
        
        <!-- 更多噪声 -->
        <div class="sidebar">
            <h3>相关链接</h3>
            <a href="/link1">链接1</a>
            <a href="/link2">链接2</a>
        </div>
        
        <!-- 评论区 -->
        <div class="comments">
            <p>用户评论：很好的文章！</p>
            <p>用户评论：学到了很多。</p>
        </div>
        
        <!-- 页脚噪声 -->
        <footer>
            <p>版权所有 © 2024</p>
        </footer>
    </body>
    </html>
    """
    
    print("🧪 测试 TF-IDF + Trafilatura 集成")
    print("=" * 60)
    
    try:
        # 测试 TF-IDF 优化器
        from app.utils.tfidf_optimizer import optimize_html_with_tfidf, is_tfidf_enabled
        
        print(f"📊 TF-IDF 优化器状态: {'启用' if is_tfidf_enabled() else '禁用'}")
        
        if is_tfidf_enabled():
            print("\n🔍 步骤 1: TF-IDF 预处理优化")
            optimized_html, tfidf_report = optimize_html_with_tfidf(test_html, "https://example.com/test")
            
            print(f"📈 优化结果: {tfidf_report.get('optimization', 'unknown')}")
            if tfidf_report.get('optimization') == 'success':
                print(f"📋 原始内容块: {tfidf_report.get('original_blocks', 0)}")
                print(f"✅ 过滤后内容块: {tfidf_report.get('filtered_blocks', 0)}")
                
                print("\n🏆 Top 3 内容块:")
                for i, block in enumerate(tfidf_report.get('top_scores', [])[:3], 1):
                    print(f"  {i}. 得分: {block['score']:.3f}, TF-IDF: {block['tfidf_score']:.3f}")
                    print(f"     标签: {block['tag']}, 预览: {block['text_preview'][:50]}...")
        
        # 测试 Trafilatura 提取
        print("\n🔍 步骤 2: Trafilatura 内容提取")
        from app.utils.trafilatura_extractor import extract_content_with_trafilatura
        
        result = extract_content_with_trafilatura(
            html=test_html,
            url="https://example.com/test",
            favor_precision=True,
            deduplicate=True
        )
        
        if result:
            print(f"✅ 提取成功!")
            print(f"📝 标题: {result.get('title', 'N/A')}")
            print(f"📏 文本长度: {len(result.get('text', ''))} 字符")
            print(f"🔧 提取方法: {result.get('extraction_method', 'unknown')}")
            
            # TF-IDF 优化信息
            tfidf_info = result.get('tfidf_optimization', {})
            if tfidf_info:
                print(f"🧠 TF-IDF 优化: {tfidf_info.get('optimization', 'N/A')}")
            
            print(f"\n📄 提取的文本内容:")
            print("-" * 40)
            text_preview = result.get('text', '')[:500]
            print(text_preview)
            if len(result.get('text', '')) > 500:
                print("...(内容截断)")
        else:
            print("❌ 提取失败")
        
        print("\n" + "=" * 60)
        print("✅ 测试完成!")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tfidf_integration()
