"""周报路由 - 提供周报生成和下载功能"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncio

from app.services.report_generator import generate_weekly_report
from app.models.task_model import get_user_preferences

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/weekly/generate")
async def generate_weekly_report_endpoint(
    user_id: int = 1,
    time_range: str = "this_week"
):
    """
    生成周报（异步）
    
    Args:
        user_id: 用户ID
        time_range: 时间范围 (this_week/last_week/this_month)
    
    Returns:
        任务提交状态
    """
    try:
        # ⭐ 防止重复提交：检查是否正在生成
        from app.services.cache_service import redis_cache
        
        submit_key = f"report_submitting:{user_id}:{time_range}"
        
        if redis_cache.enabled:
            is_submitting = redis_cache.get(submit_key)
            if is_submitting:
                return {
                    "success": False,
                    "message": "周报正在生成中，请稍后再试",
                    "async": True
                }
            
            # 标记为正在生成（缓存5分钟）
            redis_cache.set(submit_key, True, ttl=300)
        
        # 异步生成周报
        payload = {
            "user_id": user_id,
            "time_range": time_range
        }
        
        # 在后台启动任务
        asyncio.create_task(generate_weekly_report(payload))
        
        return {
            "success": True,
            "message": "周报生成任务已提交，将通过 WebSocket 推送结果",
            "async": True,
            "time_range": time_range
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成周报失败: {str(e)}")


@router.get("/weekly/{user_id}/download")
def download_weekly_report(
    user_id: int,
    time_range: str = "this_week"
):
    """
    下载 Word 格式的周报
    
    Args:
        user_id: 用户ID
        time_range: 时间范围 (this_week/last_week/this_month)
    
    Returns:
        Word 文档文件流
    """
    try:
        from io import BytesIO
        from app.services.cache_service import redis_cache
        from datetime import datetime
        
        # ⭐ 尝试从 Redis 缓存中获取已生成的 Word 文档
        cache_key = f"report_word:{user_id}:{time_range}:{datetime.now().strftime('%Y%m%d')}"
        
        if redis_cache.enabled:
            cached_word = redis_cache.get(cache_key)
            if cached_word:
                print(f"✅ 从缓存中获取 Word 文档: {cache_key}")
                word_content = cached_word
            else:
                print(f"⚠️ 缓存未命中，重新生成 Word 文档")
                # 如果缓存中没有，则实时生成
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                payload = {
                    "user_id": user_id,
                    "time_range": time_range
                }
                
                result = loop.run_until_complete(generate_weekly_report(payload))
                loop.close()
                
                if not result["success"]:
                    raise HTTPException(
                        status_code=500,
                        detail=result.get("error", "生成报告失败")
                    )
                
                word_content = result.get("word_content")
                if not word_content:
                    raise HTTPException(
                        status_code=500,
                        detail="Word 文档生成失败"
                    )
                
                # 缓存 Word 文档（24小时）
                redis_cache.set(cache_key, word_content, ttl=86400)
        else:
            # Redis 未启用，直接生成
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            payload = {
                "user_id": user_id,
                "time_range": time_range
            }
            
            result = loop.run_until_complete(generate_weekly_report(payload))
            loop.close()
            
            if not result["success"]:
                raise HTTPException(
                    status_code=500,
                    detail=result.get("error", "生成报告失败")
                )
            
            word_content = result.get("word_content")
            if not word_content:
                raise HTTPException(
                    status_code=500,
                    detail="Word 文档生成失败"
                )
        
        # 创建文件流响应
        stream = BytesIO(word_content)
        
        # 生成文件名
        filename = f"周报_{user_id}_{time_range}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        
        # ⭐ 正确处理中文文件名：使用 RFC 5987 编码
        from urllib.parse import quote
        encoded_filename = quote(filename.encode('utf-8'))
        
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ 下载失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")
