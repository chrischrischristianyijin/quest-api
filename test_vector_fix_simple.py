#!/usr/bin/env python3
"""
简化的vector(1536)数据处理测试
"""

import sys
import os
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_service import RAGService

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_vector_processing():
    """测试vector(1536)数据处理"""
    try:
        rag_service = RAGService()
        
        # 模拟PostgreSQL vector(1536)数据的不同格式
        test_embeddings = [
            # 1. 正常列表格式（Supabase Python客户端通常返回的格式）
            [0.1] * 1536,
            
            # 2. 字符串格式（某些情况下可能返回）
            str([0.1] * 1536),
            
            # 3. 元组格式
            tuple([0.1] * 1536),
            
            # 4. 包含numpy数组的情况
            None,  # 将在测试中动态创建
        ]
        
        logger.info("测试PostgreSQL vector(1536)数据处理...")
        
        for i, embedding_data in enumerate(test_embeddings):
            if embedding_data is None:
                # 测试numpy数组
                try:
                    import numpy as np
                    embedding_data = np.array([0.1] * 1536)
                    logger.info(f"测试用例 {i+1}: numpy数组")
                except ImportError:
                    logger.info(f"测试用例 {i+1}: 跳过numpy测试（numpy未安装）")
                    continue
            else:
                logger.info(f"测试用例 {i+1}: {type(embedding_data)}")
            
            try:
                # 测试标准化
                normalized = rag_service._normalize_embedding_data(embedding_data, f"test-{i}")
                
                if normalized:
                    logger.info(f"  ✅ 标准化成功: 长度={len(normalized)}, 类型={type(normalized)}")
                    logger.info(f"  📊 前3个值: {normalized[:3]}")
                    
                    # 测试余弦相似度计算
                    query_vec = [0.2] * 1536
                    similarity = rag_service._calculate_cosine_similarity(query_vec, normalized)
                    logger.info(f"  🎯 相似度: {similarity:.4f}")
                else:
                    logger.info(f"  ❌ 标准化失败")
                    
            except Exception as e:
                logger.error(f"  ❌ 处理失败: {e}")
        
        logger.info("✅ vector(1536)数据处理测试完成")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔧 测试PostgreSQL vector(1536)数据处理修复...")
    test_vector_processing()
