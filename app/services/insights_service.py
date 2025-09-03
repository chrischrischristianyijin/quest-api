from typing import List, Optional, Dict, Any
from uuid import UUID
from app.core.database import get_supabase, get_supabase_service
from app.models.insight import InsightCreate, InsightUpdate, InsightResponse, InsightListResponse
from app.services.insight_tag_service import InsightTagService
from app.utils.metadata import fetch_page_content
import logging
import os
from copy import deepcopy
import asyncio
from app.utils.summarize import generate_summary
from datetime import datetime, date
import re
import hashlib
import json
from functools import lru_cache
import time

logger = logging.getLogger(__name__)

# 简单的内存缓存，用于减少重复查询
_query_cache = {}
_cache_ttl = 30  # 30秒缓存

def _cache_key(func_name: str, *args, **kwargs) -> str:
    """生成缓存键"""
    key_parts = [func_name] + [str(arg) for arg in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
    return hashlib.md5("|".join(key_parts).encode()).hexdigest()

def _get_cache(key: str):
    """获取缓存"""
    if key in _query_cache:
        cached_data, timestamp = _query_cache[key]
        if time.time() - timestamp < _cache_ttl:
            return cached_data
        else:
            del _query_cache[key]
    return None

def _set_cache(key: str, data):
    """设置缓存"""
    _query_cache[key] = (data, time.time())
    # 简单的缓存清理：保持最多100个缓存项
    if len(_query_cache) > 100:
        oldest_key = min(_query_cache.keys(), key=lambda k: _query_cache[k][1])
        del _query_cache[oldest_key]

class InsightsService:
    """Insights服务类"""
    
    @staticmethod
    async def get_insights(
        user_id: UUID,
        page: int = 1,
        limit: int = 10,
        search: Optional[str] = None,
        target_user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """获取insights列表（分页）"""
        try:
            supabase = get_supabase()
            supabase_service = get_supabase_service()
            
            # 确定要查询的用户ID - 如果没有指定target_user_id，默认查询当前用户
            query_user_id = str(target_user_id) if target_user_id else str(user_id)
            
            # 权限检查：如果指定了target_user_id，验证是否为当前用户
            # 如果没有指定target_user_id，则查询当前用户的insights（这是安全的）
            if target_user_id and str(target_user_id) != str(user_id):
                logger.warning(f"用户 {user_id} 尝试访问用户 {target_user_id} 的insights")
                return {
                    "success": False,
                    "message": "只能查看自己的insights"
                }
            
            logger.info(f"查询用户 {query_user_id} 的insights，当前用户: {user_id}")
            
            # 构建查询 - 只选择必要字段，避免传输大量数据
            query = supabase.table('insights').select(
                'id, title, description, url, image_url, created_at, updated_at'
            ).eq('user_id', query_user_id)
            
            # 添加搜索条件
            if search:
                query = query.or_(f'title.ilike.%{search}%,description.ilike.%{search}%')
            
            # 添加排序和分页
            query = query.order('created_at', desc=True).range((page - 1) * limit, page * limit - 1)
            
            # 执行查询
            response = query.execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"获取insights失败: {response.error}")
                return {"success": False, "message": "获取insights失败"}
            
            insights = response.data or []
            logger.info(f"成功获取 {len(insights)} 条insights")
            
            # 获取总数
            count_query = supabase.table('insights').select('id', count='exact').eq('user_id', query_user_id)
            if search:
                count_query = count_query.or_(f'title.ilike.%{search}%,description.ilike.%{search}%')
            
            count_response = count_query.execute()
            total = count_response.count if hasattr(count_response, 'count') else len(insights)
            
            # 优化：使用缓存减少重复标签查询
            cache_key = _cache_key("user_tags", str(user_id))
            cached_tags = _get_cache(cache_key)
            
            if cached_tags is None and insights:
                # 批量获取标签
                insight_ids = [UUID(insight['id']) for insight in insights]
                tags_result = await InsightTagService.get_tags_by_insight_ids(insight_ids, user_id)
                _set_cache(cache_key, tags_result)
            else:
                tags_result = cached_tags or {"success": True, "data": {}}
            
            # 构建响应数据 - 优化版本，避免重复 UUID 转换
            insight_responses = []
            for insight in insights:
                insight_tags = tags_result.get('data', {}).get(insight['id'], [])
                
                insight_response = {
                    "id": insight['id'],
                    "user_id": query_user_id,  # 直接使用查询的 user_id
                    "title": insight['title'],
                    "description": insight['description'],
                    "url": insight.get('url'),
                    "image_url": insight.get('image_url'),
                    "created_at": insight['created_at'],
                    "updated_at": insight['updated_at'],
                    "tags": insight_tags
                }
                insight_responses.append(insight_response)
            
            return {
                "success": True,
                "data": {
                    "insights": insight_responses,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": total,
                        "total_pages": (total + limit - 1) // limit
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"获取insights失败: {str(e)}")
            return {"success": False, "message": f"获取insights失败: {str(e)}"}
    
    @staticmethod
    async def get_all_user_insights(
        user_id: UUID,
        search: Optional[str] = None,
        target_user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """获取用户所有insights（不分页）"""
        try:
            supabase = get_supabase()
            
            # 确定要查询的用户ID - 如果没有指定target_user_id，默认查询当前用户
            query_user_id = str(target_user_id) if target_user_id else str(user_id)
            
            # 权限检查：如果指定了target_user_id，验证是否为当前用户
            # 如果没有指定target_user_id，则查询当前用户的insights（这是安全的）
            if target_user_id and str(target_user_id) != str(user_id):
                logger.warning(f"用户 {user_id} 尝试访问用户 {target_user_id} 的insights")
                return {
                    "success": False,
                    "message": "只能查看自己的insights"
                }
            
            logger.info(f"查询用户 {query_user_id} 的所有insights，当前用户: {user_id}")
            
            # 构建查询 - 只选择必要字段，避免传输大量数据
            query = supabase.table('insights').select(
                'id, title, description, url, image_url, created_at, updated_at'
            ).eq('user_id', query_user_id)
            
            # 添加搜索条件
            if search:
                query = query.or_(f'title.ilike.%{search}%,description.ilike.%{search}%')
            
            # 添加排序和限制（避免一次性获取过多数据）
            query = query.order('created_at', desc=True)
            
            # 性能保护：如果是获取所有数据，限制最大数量
            MAX_INSIGHTS_LIMIT = int(os.getenv('MAX_INSIGHTS_LIMIT', '1000'))
            query = query.limit(MAX_INSIGHTS_LIMIT)
            
            # 执行查询
            response = query.execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"获取所有insights失败: {response.error}")
                return {"success": False, "message": "获取所有insights失败"}
            
            insights = response.data or []
            logger.info(f"成功获取 {len(insights)} 条insights")
            
            # 优化：如果 insights 数量很大，考虑分批处理标签
            if len(insights) > 100:
                logger.warning(f"用户 {query_user_id} 有大量 insights ({len(insights)})，可能影响性能")
            
            # 批量获取标签 - 优化版本
            insight_responses = []
            if insights:
                insight_ids = [UUID(insight['id']) for insight in insights]
                tags_result = await InsightTagService.get_tags_by_insight_ids(insight_ids, user_id)
                
                # 构建响应数据
                for insight in insights:
                    insight_tags = tags_result.get('data', {}).get(insight['id'], [])
                    
                    insight_response = {
                        "id": insight['id'],
                        "user_id": query_user_id,  # 直接使用查询的 user_id，避免重复转换
                        "title": insight['title'],
                        "description": insight['description'],
                        "url": insight.get('url'),
                        "image_url": insight.get('image_url'),
                        "created_at": insight['created_at'],
                        "updated_at": insight['updated_at'],
                        "tags": insight_tags
                    }
                    insight_responses.append(insight_response)
            
            return {
                "success": True,
                "data": {
                    "insights": insight_responses
                }
            }
            
        except Exception as e:
            logger.error(f"获取所有insights失败: {str(e)}")
            return {"success": False, "message": f"获取所有insights失败: {str(e)}"}
    
    @staticmethod
    async def get_insights_incremental(
        user_id: UUID,
        since: Optional[str] = None,
        etag: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """增量获取用户insights（只返回变动的数据）- 新接口"""
        try:
            supabase = get_supabase()
            
            logger.info(f"增量查询用户 {user_id} 的insights，since={since}, etag={etag}")
            
            # 构建基础查询 - 只选择必要字段
            query = supabase.table('insights').select(
                'id, title, description, url, image_url, created_at, updated_at'
            ).eq('user_id', str(user_id))
            
            # 时间过滤：只获取指定时间之后的数据
            if since:
                try:
                    # 解析时间戳（支持多种格式）
                    if since.endswith('Z'):
                        since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                    else:
                        since_dt = datetime.fromisoformat(since)
                    
                    query = query.gte('updated_at', since_dt.isoformat())
                    logger.info(f"过滤时间: {since_dt}")
                except Exception as time_err:
                    logger.warning(f"时间格式解析失败: {time_err}")
                    return {"success": False, "message": "时间格式错误"}
            
            # 添加排序和限制
            query = query.order('updated_at', desc=True).limit(limit)
            
            # 执行查询
            response = query.execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"增量获取insights失败: {response.error}")
                return {"success": False, "message": "增量获取insights失败"}
            
            insights = response.data or []
            logger.info(f"增量查询获取 {len(insights)} 条insights")
            
            # 生成数据指纹用于 ETag 缓存
            data_hash = _generate_etag(insights)
            
            # ETag 检查：如果数据没有变化，返回 304
            if etag and etag == data_hash and insights:
                logger.info("数据未变化，返回 304 Not Modified")
                return {
                    "success": True,
                    "not_modified": True,
                    "etag": data_hash
                }
            
            # 批量获取标签
            insight_responses = []
            if insights:
                insight_ids = [UUID(insight['id']) for insight in insights]
                tags_result = await InsightTagService.get_tags_by_insight_ids(insight_ids, user_id)
                
                # 构建响应数据
                for insight in insights:
                    insight_tags = tags_result.get('data', {}).get(insight['id'], [])
                    
                    insight_response = {
                        "id": insight['id'],
                        "user_id": str(user_id),
                        "title": insight['title'],
                        "description": insight['description'],
                        "url": insight.get('url'),
                        "image_url": insight.get('image_url'),
                        "created_at": insight['created_at'],
                        "updated_at": insight['updated_at'],
                        "tags": insight_tags
                    }
                    insight_responses.append(insight_response)
            
            # 计算是否还有更多数据
            has_more = len(insights) >= limit
            last_updated = insights[0]['updated_at'] if insights else datetime.utcnow().isoformat()
            
            return {
                "success": True,
                "data": {
                    "insights": insight_responses,
                    "has_more": has_more,
                    "last_updated": last_updated,
                    "etag": data_hash,
                    "count": len(insight_responses)
                }
            }
            
        except Exception as e:
            logger.error(f"增量获取insights失败: {str(e)}")
            return {"success": False, "message": f"增量获取insights失败: {str(e)}"}
    
    @staticmethod
    async def get_insight(insight_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """获取单个insight详情"""
        try:
            supabase = get_supabase()
            
            # 获取insight
            response = supabase.table('insights').select('*').eq('id', str(insight_id)).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"获取insight失败: {response.error}")
                return {"success": False, "message": "获取insight失败"}
            
            if not response.data:
                return {"success": False, "message": "Insight不存在"}
            
            insight = response.data[0]
            
            # 权限检查：只能查看自己的insight
            if insight['user_id'] != str(user_id):
                return {"success": False, "message": "无权查看此insight"}
            
            # 获取标签
            tags_result = await InsightTagService.get_insight_tags(insight_id, user_id)
            insight_tags = tags_result.get('data', []) if tags_result.get('success') else []
            
            # 构建响应数据
            insight_response = InsightResponse(
                id=UUID(insight['id']),
                user_id=UUID(insight['user_id']),
                title=insight['title'],
                description=insight['description'],
                url=insight.get('url'),
                image_url=insight.get('image_url'),
                meta=insight.get('meta'),
                created_at=insight['created_at'],
                updated_at=insight['updated_at'],
                tags=insight_tags
            )
            
            return {"success": True, "data": insight_response}
            
        except Exception as e:
            logger.error(f"获取insight失败: {str(e)}")
            return {"success": False, "message": f"获取insight失败: {str(e)}"}
    
    @staticmethod
    async def create_insight(insight_data: InsightCreate, user_id: UUID) -> Dict[str, Any]:
        """创建新insight"""
        try:
            supabase = get_supabase()
            supabase_service = get_supabase_service()
            
            # 准备insight数据（不包含tags，让数据库自动生成UUID）
            insight_insert_data = {
                'title': insight_data.title,
                'description': insight_data.description,
                'url': insight_data.url,
                'image_url': insight_data.image_url,
                'user_id': str(user_id)
                # 移除手动UUID生成，让数据库自动生成
            }

            # 可选写入 meta（如列存在），以 JSON 形式存储网页元数据
            try:
                if hasattr(insight_data, 'meta') and isinstance(getattr(insight_data, 'meta'), dict):
                    insight_insert_data['meta'] = getattr(insight_data, 'meta')
            except Exception:
                pass
            
            # 创建insight（使用 service role 以避免 RLS 造成的插入失败）
            logger.info(f"准备创建 insight：user_id={user_id}, url={insight_data.url}")
            response = supabase_service.table('insights').insert(insight_insert_data).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"创建insight失败: {response.error}")
                return {"success": False, "message": "创建insight失败"}
            
            if not response.data:
                return {"success": False, "message": "创建insight失败"}
            
            insight = response.data[0]
            logger.info(f"insight 创建成功: id={insight.get('id')}, user_id={insight.get('user_id')}")
            insight_id = UUID(insight['id'])

            # 启动异步后台任务处理内容抓取和摘要生成
            if os.getenv('FETCH_PAGE_CONTENT_ENABLED', '').lower() in ('1', 'true', 'yes'):
                try:
                    import asyncio
                    # 创建后台任务，不等待完成
                    asyncio.create_task(InsightsService._fetch_and_save_content(
                        insight_id=insight_id,
                        user_id=user_id,
                        url=insight_data.url
                    ))
                    logger.info("已启动异步内容处理 pipeline 后台任务")
                except Exception as task_err:
                    logger.warning(f"启动异步内容处理任务失败: {task_err}")
            else:
                logger.info("FETCH_PAGE_CONTENT_ENABLED 未开启，跳过全文抓取与保存")
            
            # 处理标签
            if insight_data.tag_ids:
                tags_result = await InsightTagService.update_insight_tags_by_ids(
                    insight_id, insight_data.tag_ids, user_id
                )
                if not tags_result.get('success'):
                    logger.warning(f"创建insight成功，但标签处理失败: {tags_result.get('message')}")
            
            # 获取完整的insight数据（包含标签）
            # 使用 service role 来避免 RLS 权限问题
            try:
                response = supabase_service.table('insights').select('*').eq('id', str(insight_id)).execute()
                
                if not response.data:
                    logger.warning(f"刚创建的insight {insight_id} 无法立即查询到，可能是数据库延迟")
                    # 返回基础创建成功信息
                    return {
                        "success": True,
                        "message": "Insight创建成功",
                        "data": {
                            "id": str(insight_id),
                            "user_id": str(user_id),
                            "title": insight_data.title,
                            "description": insight_data.description,
                            "url": insight_data.url,
                            "image_url": insight_data.image_url,
                            "tags": []
                        }
                    }
                
                insight_detail = response.data[0]
                
                # 获取标签
                tags_result = await InsightTagService.get_insight_tags(insight_id, user_id)
                insight_tags = tags_result.get('data', []) if tags_result.get('success') else []
                
                # 构建响应数据
                return {
                    "success": True,
                    "message": "Insight创建成功",
                    "data": {
                        "id": insight_detail['id'],
                        "user_id": insight_detail['user_id'],
                        "title": insight_detail['title'],
                        "description": insight_detail['description'],
                        "url": insight_detail.get('url'),
                        "image_url": insight_detail.get('image_url'),
                        "meta": insight_detail.get('meta'),
                        "created_at": insight_detail['created_at'],
                        "updated_at": insight_detail['updated_at'],
                        "tags": insight_tags
                    }
                }
                
            except Exception as get_error:
                logger.error(f"获取刚创建的insight失败: {get_error}")
                # 即使获取失败，也返回创建成功信息
                return {
                    "success": True,
                    "message": "Insight创建成功（详情获取失败）",
                    "data": {
                        "id": str(insight_id),
                        "user_id": str(user_id),
                        "title": insight_data.title,
                        "description": insight_data.description,
                        "url": insight_data.url,
                        "image_url": insight_data.image_url,
                        "tags": []
                    }
                }
            
        except Exception as e:
            logger.error(f"创建insight失败: {str(e)}")
            return {"success": False, "message": f"创建insight失败: {str(e)}"}

    @staticmethod
    async def _fetch_and_save_content(insight_id: UUID, user_id: UUID, url: str) -> None:
        """完整的 insight 内容处理 pipeline（异步后台任务）。

        流程：
        1. 检查缓存中是否有摘要
        2. 如果没有，抓取页面内容
        3. 生成摘要（如果缓存中没有）
        4. 保存到 insight_contents 表
        5. 更新缓存状态

        作为后台任务运行，不阻塞主流程。所有错误仅记录日志。
        """
        try:
            logger.info(f"[后台任务] 开始处理 insight 内容: insight_id={insight_id}, url={url}")
            
            # 1. 抓取页面内容（先抓页面，再根据页面内容生成摘要）
            page = await fetch_page_content(url)
            logger.info(
                f"[后台任务] 抓取页面内容完成：status={page.get('status_code')}, ct={page.get('content_type')},"
                f" html={'Y' if page.get('html') else 'N'}, text_len={len(page.get('text') or '')},"
                f" blocked={page.get('blocked_reason')}"
            )

            # 2. 清理文本（标准化、压缩空白、长度限制）
            raw_text = page.get('text') or ''
            if not raw_text:
                try:
                    desc_res = (
                        get_supabase_service()
                        .table('insights')
                        .select('description')
                        .eq('id', str(insight_id))
                        .single()
                        .execute()
                    )
                    if getattr(desc_res, 'data', None):
                        raw_text = (desc_res.data.get('description') or '').strip()
                except Exception:
                    pass

            cleaned_text = raw_text.strip()
            if cleaned_text:
                cleaned_text = re.sub(r"\s+", " ", cleaned_text)
                # 限长，避免超出模型输入限制（与 SUMMARY_INPUT_CHAR_LIMIT 对齐）
                try:
                    input_limit = int(os.getenv('SUMMARY_INPUT_CHAR_LIMIT', '16000') or '16000')
                except Exception:
                    input_limit = 16000
                if len(cleaned_text) > input_limit:
                    cleaned_text = cleaned_text[:input_limit]
            logger.info(f"[后台任务] 清理后文本长度: {len(cleaned_text) if cleaned_text else 0}")

            # 3. 生成摘要（基于清理后的文本）
            summary_text = None
            try:
                if cleaned_text:
                    logger.info(f"[后台任务] 开始生成摘要: {url}")
                    summary_text = await generate_summary(cleaned_text)
                    from app.routers.metadata import summary_cache
                    if summary_text:
                        logger.info(f"[后台任务] 生成摘要完成: {url}，长度={len(summary_text)}")
                        summary_cache[url] = {
                            'status': 'completed',
                            'created_at': datetime.now(),
                            'summary': summary_text,
                            'error': None
                        }
                    else:
                        logger.warning("[后台任务] 生成摘要为空，标记为失败")
                        summary_cache[url] = {
                            'status': 'failed',
                            'created_at': datetime.now(),
                            'summary': None,
                            'error': 'empty-summary'
                        }
            except Exception as _sum_err:
                from app.routers.metadata import summary_cache
                logger.warning(f"[后台任务] 摘要生成失败: {_sum_err}")
                summary_cache[url] = {
                    'status': 'failed',
                    'created_at': datetime.now(),
                    'summary': None,
                    'error': str(_sum_err)
                }

            # 4. 准备内容数据
            # 4. 准备内容数据（统一规范时间字段为 ISO 字符串）
            extracted_at_val = page.get('extracted_at')
            if isinstance(extracted_at_val, (datetime, date)):
                extracted_at_val = extracted_at_val.isoformat()
            content_payload = {
                'insight_id': str(insight_id),
                'user_id': str(user_id),
                'url': url,
                'html': page.get('html'),
                'text': page.get('text'),
                'markdown': page.get('markdown'),
                'content_type': page.get('content_type'),
                'extracted_at': extracted_at_val,
                'summary': summary_text
            }

            # 记录摘要长度，便于排查是否为空
            try:
                logger.info(f"即将写入 insight_contents.summary 长度: {len(summary_text) if summary_text else 0}")
            except Exception:
                pass

            # 5. 数据清理
            def _sanitize_for_pg(obj: Any) -> Any:
                try:
                    if obj is None:
                        return None
                    if isinstance(obj, str):
                        return obj.replace('\x00', ' ').replace('\u0000', ' ')
                    if isinstance(obj, (datetime, date)):
                        return obj.isoformat()
                    if isinstance(obj, dict):
                        clean = {}
                        for k, v in obj.items():
                            clean[k] = _sanitize_for_pg(v)
                        return clean
                    if isinstance(obj, list):
                        return [_sanitize_for_pg(v) for v in obj]
                    return obj
                except Exception:
                    return obj

            safe_payload = _sanitize_for_pg(deepcopy(content_payload))

            # 6. 保存到数据库
            supabase_service = get_supabase_service()
            content_res = (
                supabase_service
                .table('insight_contents')
                .insert(safe_payload)
                .execute()
            )
            if hasattr(content_res, 'error') and content_res.error:
                logger.warning(f"[后台任务] 保存 insight_contents 失败: {content_res.error}")
            else:
                logger.info(f"[后台任务] insight_contents 保存成功: {url}")
                
                # 6.1 保存后回读校验，如 summary 为空且我们本地有 summary_text，则进行一次回填更新
                try:
                    check_res = (
                        supabase_service
                        .table('insight_contents')
                        .select('id, summary')
                        .eq('insight_id', str(insight_id))
                        .order('created_at', desc=True)
                        .limit(1)
                        .execute()
                    )
                    row = check_res.data[0] if getattr(check_res, 'data', None) else None
                    db_summary = row.get('summary') if row else None
                    if summary_text and not db_summary and row and row.get('id'):
                        upd = (
                            supabase_service
                            .table('insight_contents')
                            .update({'summary': summary_text})
                            .eq('id', row['id'])
                            .execute()
                        )
                        if hasattr(upd, 'error') and upd.error:
                            logger.warning(f"[后台任务] insight_contents 回填 summary 失败: {upd.error}")
                        else:
                            logger.info("[后台任务] insight_contents 回填 summary 成功")
                except Exception as verify_err:
                    logger.warning(f"[后台任务] insight_contents 回读/回填校验失败: {verify_err}")
                
        except Exception as content_err:
            logger.error(f"[后台任务] 内容处理失败: {content_err}")
            # 更新缓存状态为失败
            try:
                from app.routers.metadata import summary_cache
                summary_cache[url] = {
                    'status': 'failed',
                    'created_at': datetime.now(),
                    'summary': None,
                    'error': str(content_err)
                }
            except Exception:
                pass
        finally:
            logger.info(f"[后台任务] 内容处理任务结束: insight_id={insight_id}, url={url}")


def _generate_etag(insights: list) -> str:
    """生成数据的 ETag 指纹"""
    try:
        # 创建数据指纹：基于 ID 和更新时间
        fingerprint_data = []
        for insight in insights:
            fingerprint_data.append({
                'id': insight.get('id'),
                'updated_at': insight.get('updated_at')
            })
        
        # 生成 MD5 哈希
        data_str = json.dumps(fingerprint_data, sort_keys=True, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()
    except Exception:
        # 如果生成失败，返回基于时间的简单哈希
        return hashlib.md5(str(datetime.utcnow()).encode()).hexdigest()
    
    @staticmethod
    async def update_insight(insight_id: UUID, insight_data: InsightUpdate, user_id: UUID) -> Dict[str, Any]:
        """更新insight"""
        try:
            supabase = get_supabase()
            
            # 检查insight是否存在且属于该用户
            existing_response = supabase.table('insights').select('user_id').eq('id', str(insight_id)).execute()
            
            if hasattr(existing_response, 'error') and existing_response.error:
                logger.error(f"检查insight失败: {existing_response.error}")
                return {"success": False, "message": "检查insight失败"}
            
            if not existing_response.data:
                return {"success": False, "message": "Insight不存在"}
            
            if existing_response.data[0]['user_id'] != str(user_id):
                return {"success": False, "message": "无权更新此insight"}
            
            # 准备更新数据（不包含tags）
            update_data = {}
            if insight_data.title is not None:
                update_data['title'] = insight_data.title
            if insight_data.description is not None:
                update_data['description'] = insight_data.description
            if insight_data.url is not None:
                update_data['url'] = insight_data.url
            if insight_data.image_url is not None:
                update_data['image_url'] = insight_data.image_url
            
            # 更新insight
            if update_data:
                response = supabase.table('insights').update(update_data).eq('id', str(insight_id)).execute()
                
                if hasattr(response, 'error') and response.error:
                    logger.error(f"更新insight失败: {response.error}")
                    return {"success": False, "message": "更新insight失败"}
            
            # 处理标签更新
            if insight_data.tag_ids is not None:
                tags_result = await InsightTagService.update_insight_tags_by_ids(
                    insight_id, insight_data.tag_ids, user_id
                )
                if not tags_result.get('success'):
                    logger.warning(f"更新insight成功，但标签处理失败: {tags_result.get('message')}")
            
            # 获取更新后的insight数据
            return await InsightsService.get_insight(insight_id, user_id)
            
        except Exception as e:
            logger.error(f"更新insight失败: {str(e)}")
            return {"success": False, "message": f"更新insight失败: {str(e)}"}
    
    @staticmethod
    async def delete_insight(insight_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """删除insight"""
        try:
            supabase = get_supabase()
            
            # 检查insight是否存在且属于该用户
            existing_response = supabase.table('insights').select('user_id').eq('id', str(insight_id)).execute()
            
            if hasattr(existing_response, 'error') and existing_response.error:
                logger.error(f"检查insight失败: {existing_response.error}")
                return {"success": False, "message": "检查insight失败"}
            
            if not existing_response.data:
                return {"success": False, "message": "Insight不存在"}
            
            if existing_response.data[0]['user_id'] != str(user_id):
                return {"success": False, "message": "无权删除此insight"}
            
            # 删除insight（标签关联会通过CASCADE自动删除）
            response = supabase.table('insights').delete().eq('id', str(insight_id)).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"删除insight失败: {response.error}")
                return {"success": False, "message": "删除insight失败"}
            
            return {"success": True, "message": "Insight删除成功"}
            
        except Exception as e:
            logger.error(f"删除insight失败: {str(e)}")
            return {"success": False, "message": f"删除insight失败: {str(e)}"}
