#!/usr/bin/env python3
"""
数据迁移脚本：将现有的 insights.tags 字段数据迁移到新的 insight_tags 桥表

使用方法：
1. 确保已经运行了数据库迁移文件创建了 insight_tags 表
2. 运行此脚本：python migrate_tags_to_bridge_table.py

注意：此脚本会读取现有的 tags 数据并创建新的关联关系
"""

import asyncio
import sys
import os
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_supabase
from app.services.insight_tag_service import InsightTagService

async def migrate_tags_to_bridge_table():
    """迁移tags数据到桥表"""
    try:
        print("🚀 开始迁移tags数据到桥表...")
        
        supabase = get_supabase()
        
        # 步骤1：获取所有有tags的insights
        print("📋 获取所有有tags的insights...")
        response = supabase.table('insights').select('id, user_id, tags').not_.is_('tags', 'null').execute()
        
        if hasattr(response, 'error') and response.error:
            print(f"❌ 获取insights失败: {response.error}")
            return False
        
        insights_with_tags = response.data or []
        print(f"✅ 找到 {len(insights_with_tags)} 个有tags的insight")
        
        if not insights_with_tags:
            print("ℹ️ 没有找到需要迁移的数据")
            return True
        
        # 步骤2：为每个insight创建标签关联
        print("🔗 开始创建标签关联...")
        success_count = 0
        error_count = 0
        
        for insight in insights_with_tags:
            insight_id = insight['id']
            user_id = insight['user_id']
            tags = insight.get('tags', [])
            
            if not tags:
                continue
            
            print(f"  - 处理insight {insight_id}，标签: {tags}")
            
            try:
                # 使用现有的标签名称创建关联
                result = await InsightTagService.update_insight_tags(
                    insight_id, tags, user_id
                )
                
                if result.get('success'):
                    success_count += 1
                    print(f"    ✅ 成功创建 {len(tags)} 个标签关联")
                else:
                    error_count += 1
                    print(f"    ❌ 失败: {result.get('message')}")
                    
            except Exception as e:
                error_count += 1
                print(f"    ❌ 异常: {str(e)}")
        
        # 步骤3：验证迁移结果
        print("\n🔍 验证迁移结果...")
        total_insights = len(insights_with_tags)
        print(f"总insights数: {total_insights}")
        print(f"成功迁移: {success_count}")
        print(f"迁移失败: {error_count}")
        
        if success_count > 0:
            # 检查桥表中的数据
            bridge_response = supabase.table('insight_tags').select('insight_id', count='exact').execute()
            if hasattr(bridge_response, 'count'):
                total_relationships = bridge_response.count
                print(f"桥表中的关联关系总数: {total_relationships}")
        
        # 步骤4：询问是否要清理旧的tags字段
        print("\n⚠️  迁移完成！")
        print("现在你可以安全地删除 insights 表中的 tags 字段")
        print("运行以下SQL语句：")
        print("ALTER TABLE insights DROP COLUMN IF EXISTS tags;")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ 迁移过程中发生错误: {str(e)}")
        return False

async def verify_migration():
    """验证迁移结果"""
    try:
        print("\n🔍 验证迁移结果...")
        
        supabase = get_supabase()
        
        # 检查桥表数据
        bridge_response = supabase.table('insight_tags').select(
            'insight_id, tag_id, user_tags(name, color)'
        ).limit(5).execute()
        
        if hasattr(bridge_response, 'error') and bridge_response.error:
            print(f"❌ 验证失败: {bridge_response.error}")
            return
        
        if bridge_response.data:
            print("✅ 桥表数据示例:")
            for item in bridge_response.data[:3]:
                insight_id = item['insight_id']
                tag_name = item.get('user_tags', {}).get('name', 'Unknown')
                tag_color = item.get('user_tags', {}).get('color', '#000000')
                print(f"  - Insight {insight_id} -> Tag: {tag_name} ({tag_color})")
        else:
            print("ℹ️ 桥表中还没有数据")
        
        # 统计信息
        count_response = supabase.table('insight_tags').select('id', count='exact').execute()
        if hasattr(count_response, 'count'):
            print(f"桥表中的关联关系总数: {count_response.count}")
        
    except Exception as e:
        print(f"❌ 验证失败: {str(e)}")

async def main():
    """主函数"""
    print("=" * 60)
    print("🔧 Quest API - Tags数据迁移工具")
    print("=" * 60)
    
    try:
        # 执行迁移
        success = await migrate_tags_to_bridge_table()
        
        if success:
            # 验证结果
            await verify_migration()
            print("\n🎉 迁移完成！")
        else:
            print("\n❌ 迁移失败！")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断了迁移过程")
    except Exception as e:
        print(f"\n❌ 迁移过程中发生未预期的错误: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
