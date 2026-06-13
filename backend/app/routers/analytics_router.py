# backend/app/routers/analytics_router.py - 新建文件
"""数据分析路由 - 收集前端性能指标"""
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional
import json
from datetime import datetime

router = APIRouter(prefix="/analytics", tags=["analytics"])


class CacheStats(BaseModel):
    """缓存统计数据"""
    memoryHit: int = 0
    localStorageHit: int = 0
    serverRequest: int = 0
    avgResponseTime: float = 0
    cacheHitRate: str = "0%"
    totalRequests: int = 0
    uptimeSeconds: int = 0
    requestsPerMinute: float = 0
    errors: int = 0
    preloadCount: int = 0
    preloadSuccess: int = 0


@router.post("/cache-stats")
async def receive_cache_stats(stats: CacheStats, request: Request):
    """
    接收前端缓存统计数据

    用于分析是否需要启用 Redis
    """
    try:
        # 获取客户端 IP
        client_ip = request.client.host if request.client else "unknown"

        # 记录到日志文件
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "client_ip": client_ip,
            "stats": stats.dict()
        }

        # 写入日志文件（实际项目中可以用专门的日志系统）
        with open("logs/cache_stats.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_data, ensure_ascii=False) + "\n")

        # 分析是否需要启用 Redis
        needs_redis = analyze_redis_need(stats)

        return {
            "success": True,
            "needs_redis": needs_redis,
            "message": "统计数据已记录"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def analyze_redis_need(stats: CacheStats) -> dict:
    """
    分析是否需要启用 Redis

    返回建议和操作项
    """
    recommendations = []
    priority = "low"

    # 条件1：请求频率高
    if stats.requestsPerMinute > 10:
        recommendations.append("请求频率较高，建议优化")
        priority = "medium"

    # 条件2：缓存命中率低
    hit_rate = float(stats.cacheHitRate.replace('%', ''))
    if hit_rate < 50:
        recommendations.append("缓存命中率低，检查缓存策略")
        priority = "high"

    # 条件3：响应时间长
    if stats.avgResponseTime > 300:
        recommendations.append("平均响应时间长，考虑服务端缓存")
        priority = "high"

    # 条件4：错误率高
    if stats.totalRequests > 0:
        error_rate = (stats.errors / stats.totalRequests) * 100
        if error_rate > 5:
            recommendations.append("错误率较高，需要排查")
            priority = "critical"

    # 综合判断
    if len(recommendations) >= 2 or priority in ["high", "critical"]:
        recommendations.append("建议评估是否启用 Redis 缓存")

    return {
        "priority": priority,
        "recommendations": recommendations,
        "should_enable_redis": len(recommendations) >= 2
    }


@router.get("/cache-analysis")
async def get_cache_analysis():
    """
    获取缓存分析报告

    读取最近的统计数据并生成报告
    """
    try:
        import os
        log_file = "logs/cache_stats.jsonl"

        if not os.path.exists(log_file):
            return {
                "success": True,
                "message": "暂无统计数据",
                "data": []
            }

        # 读取最近100条记录
        stats_list = []
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-100:]:
                stats_list.append(json.loads(line))

        # 简单统计分析
        total_requests = sum(s["stats"]["totalRequests"] for s in stats_list)
        avg_hit_rate = sum(
            float(s["stats"]["cacheHitRate"].replace('%', ''))
            for s in stats_list
        ) / max(len(stats_list), 1)

        return {
            "success": True,
            "summary": {
                "total_records": len(stats_list),
                "total_requests": total_requests,
                "avg_cache_hit_rate": f"{avg_hit_rate:.2f}%",
                "unique_clients": len(set(s["client_ip"] for s in stats_list))
            },
            "recent_stats": stats_list[-10:]  # 最近10条
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
