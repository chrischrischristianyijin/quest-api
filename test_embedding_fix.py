#!/usr/bin/env python3
"""
测试embedding数据格式和余弦相似度计算修复
"""

import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_service import RAGService

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_embedding_processing():
    """测试embedding数据处理"""
    try:
        rag_service = RAGService()
        
        # 测试文本嵌入
        test_query = "什么是人工智能？"
        logger.info(f"测试查询: {test_query}")
        
        # 获取embedding
        query_embedding = await rag_service.embed_text(test_query)
        logger.info(f"查询embedding维度: {len(query_embedding)}")
        logger.info(f"查询embedding类型: {type(query_embedding)}")
        logger.info(f"查询embedding前5个值: {query_embedding[:5]}")
        
        # 测试RAG检索
        logger.info("开始RAG检索测试...")
        rag_context = await rag_service.retrieve(
            query=test_query,
            user_id=None,  # 测试所有用户的数据
            k=3,
            min_score=0.1  # 降低阈值以便看到更多结果
        )
        
        logger.info(f"检索到 {len(rag_context.chunks)} 个相关分块")
        logger.info(f"上下文总token数: {rag_context.total_tokens}")
        
        for i, chunk in enumerate(rag_context.chunks):
            logger.info(f"分块 {i+1}:")
            logger.info(f"  - ID: {chunk.id}")
            logger.info(f"  - 相似度: {chunk.score:.4f}")
            logger.info(f"  - 文本长度: {len(chunk.chunk_text)}")
            logger.info(f"  - 文本预览: {chunk.chunk_text[:100]}...")
        
        logger.info("✅ 测试完成，没有出现数据类型错误")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_embedding_normalization():
    """测试embedding数据标准化"""
    try:
        rag_service = RAGService()
        
        # 测试不同数据类型的embedding
        test_cases = [
            # 正常列表
            ([0.1, 0.2, 0.3, 0.4, 0.5] + [0.0] * 1531, "正常列表"),
            # 字符串格式
            ("[0.1, 0.2, 0.3, 0.4, 0.5" + ", 0.0" * 1531 + "]", "字符串格式"),
            # 元组格式
            (tuple([0.1, 0.2, 0.3, 0.4, 0.5] + [0.0] * 1531), "元组格式"),
            # 错误维度
            ([0.1, 0.2, 0.3], "错误维度"),
            # 包含非数值
            ([0.1, "invalid", 0.3] + [0.0] * 1533, "包含非数值"),
        ]
        
        for i, (embedding_data, description) in enumerate(test_cases):
            logger.info(f"测试用例 {i+1}: {description}")
            try:
                normalized = rag_service._normalize_embedding_data(embedding_data, f"test-{i}")
                if normalized:
                    logger.info(f"  标准化成功: 长度={len(normalized)}, 类型={type(normalized)}")
                    logger.info(f"  前5个值: {normalized[:5]}")
                else:
                    logger.info(f"  标准化失败（预期）")
            except Exception as e:
                logger.error(f"  错误: {e}")
        
        logger.info("✅ embedding标准化测试完成")
        
    except Exception as e:
        logger.error(f"❌ embedding标准化测试失败: {e}")

def test_cosine_similarity_directly():
    """直接测试余弦相似度计算"""
    try:
        rag_service = RAGService()
        
        # 创建1536维的测试向量
        vec1 = [0.1] * 1536
        vec2 = [0.2] * 1536
        
        logger.info("测试余弦相似度计算...")
        try:
            similarity = rag_service._calculate_cosine_similarity(vec1, vec2)
            logger.info(f"  相似度: {similarity:.4f}")
        except Exception as e:
            logger.error(f"  错误: {e}")
        
        logger.info("✅ 余弦相似度测试完成")
        
    except Exception as e:
        logger.error(f"❌ 余弦相似度测试失败: {e}")

if __name__ == "__main__":
    print("🔧 测试embedding数据处理修复...")
    
    # 1. 测试embedding数据标准化
    print("\n1. 测试embedding数据标准化...")
    test_embedding_normalization()
    
    # 2. 测试余弦相似度计算
    print("\n2. 测试余弦相似度计算...")
    test_cosine_similarity_directly()
    
    # 3. 测试完整的RAG流程
    print("\n3. 测试完整RAG流程...")
    asyncio.run(test_embedding_processing())
