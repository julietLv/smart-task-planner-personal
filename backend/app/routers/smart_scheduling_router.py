"""上下文感知与权重调整路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/smart-scheduling", tags=["smart-scheduling"])


class CompletionRateRequest(BaseModel):
    user_id: Optional[int] = 1
    days: Optional[int] = 7


class WeightAdjustmentRequest(BaseModel):
    user_id: Optional[int] = 1
    days: Optional[int] = 30
    dry_run: Optional[bool] = False


@router.get("/completion-rate")
def get_completion_rate(user_id: int = 1, days: int = 7):
    """
    获取用户任务完成率统计

    Args:
        user_id: 用户ID
        days: 统计天数

    Returns:
        完成率统计数据
    """
    try:
        from app.services.context_aware_scheduler import get_completion_rate

        result = get_completion_rate(user_id, days)

        return {
            "success": True,
            **result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取完成率失败: {str(e)}")


@router.get("/productivity-insights")
def get_productivity_insights(user_id: int = 1):
    """
    获取生产力洞察报告

    Args:
        user_id: 用户ID

    Returns:
        洞察力报告
    """
    try:
        from app.services.context_aware_scheduler import get_productivity_insights

        result = get_productivity_insights(user_id)

        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "未知错误"))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取洞察力失败: {str(e)}")


@router.post("/adjust-weights")
def adjust_weights(request: WeightAdjustmentRequest):
    """
    自动调整评分权重

    Args:
        request: 包含用户ID、分析天数、是否模拟运行

    Returns:
        权重调整结果
    """
    try:
        from app.services.weight_adaptor import auto_adjust_weights_endpoint

        result = auto_adjust_weights_endpoint(
            user_id=request.user_id,
            days=request.days,
            dry_run=request.dry_run
        )

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"权重调整失败: {str(e)}")


@router.get("/current-weights")
def get_current_weights():
    """
    获取当前权重配置

    Returns:
        当前权重配置
    """
    try:
        from app.services.weight_adaptor import weight_adaptor

        config = weight_adaptor.load_current_weights()

        return {
            "success": True,
            "dimensions": config["dimensions"],
            "total_weight": sum(
                dim["weight"]
                for dim in config["dimensions"].values()
                if dim.get("enabled", True)
            )
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取权重配置失败: {str(e)}")
