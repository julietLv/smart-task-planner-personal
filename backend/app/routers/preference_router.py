"""用户偏好设置路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.scheduler_service import (
    get_learned_habits_summary, 
    delete_learned_habit, 
    reset_all_habits,
    add_custom_keyword
)
from app.models.task_model import get_user_preferences, update_user_preferences

router = APIRouter(prefix="/preferences", tags=["preferences"])


class PreferenceRequest(BaseModel):
    blocked_time_start: Optional[str] = "22:00"
    blocked_time_end: Optional[str] = "08:00"
    default_priority: Optional[str] = "medium"
    assistant_nickname: Optional[str] = ""
    user_nickname: Optional[str] = ""
    task_buffer_minutes: Optional[int] = 15
    user_city: Optional[str] = "北京"
    user_type: Optional[str] = "worker"  # ⭐ Phase 3: 用户类型
    user_id: Optional[int] = 1


class CustomKeywordRequest(BaseModel):
    keyword: str
    category: str
    user_id: Optional[int] = 1


class AssistantNicknameRequest(BaseModel):
    """助手称谓请求"""
    nickname: str
    user_id: Optional[int] = 1

    class Config:
        json_schema_extra = {
            "example": {
                "nickname": "小智",
                "user_id": 1
            }
        }


class UserNicknameRequest(BaseModel):
    """用户称谓请求"""
    nickname: str
    user_id: Optional[int] = 1

    class Config:
        json_schema_extra = {
            "example": {
                "nickname": "小明",
                "user_id": 1
            }
        }


class UserTypeRequest(BaseModel):
    """⭐ Phase 3: 用户类型选择请求"""
    user_type: str  # student/worker/elderly
    user_id: Optional[int] = 1

    class Config:
        json_schema_extra = {
            "example": {
                "user_type": "student",
                "user_id": 1
            }
        }


class PersonalizationParamsRequest(BaseModel):
    """⭐ Phase 3: 个性化参数请求"""
    workday_hours: Optional[float] = None  # 工作日时长（小时）
    preferred_time_slot: Optional[str] = None  # 偏好时段 (morning/afternoon/evening)
    max_continuous_work: Optional[float] = None  # 最大连续工作时长（小时）
    min_break_minutes: Optional[float] = None  # 最小休息间隔（分钟）
    time_slot_offset: Optional[int] = None  # 时间段偏移（小时）
    user_id: Optional[int] = 1

    class Config:
        json_schema_extra = {
            "example": {
                "workday_hours": 8,
                "preferred_time_slot": "evening",
                "max_continuous_work": 4,
                "min_break_minutes": 15,
                "time_slot_offset": 1,
                "user_id": 1
            }
        }


@router.get("/")
def get_preferences(user_id: int = 1):
    """
    获取用户偏好设置

    Args:
        user_id: 用户ID

    Returns:
        用户偏好设置
    """
    try:
        preferences = get_user_preferences(user_id)
        
        # 如果用户没有偏好记录，创建默认记录
        if not preferences:
            from app.models.task_model import create_user_preferences
            preferences = create_user_preferences(user_id)

        return {
            "success": True,
            "preferences": preferences.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取偏好设置失败: {str(e)}")


@router.post("/")
def set_preferences(request: PreferenceRequest):
    """
    设置或更新用户偏好

    Args:
        request: 偏好设置请求

    Returns:
        更新后的偏好设置
    """
    try:
        update_data = request.dict(exclude_unset=True)
        user_id = update_data.pop("user_id", 1)

        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供需要更新的字段")

        if "default_priority" in update_data:
            valid_priorities = ["high", "medium", "low"]
            if update_data["default_priority"] not in valid_priorities:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的优先级值，必须是: {', '.join(valid_priorities)}"
                )

        for time_field in ["blocked_time_start", "blocked_time_end"]:
            if time_field in update_data:
                time_value = update_data[time_field]
                if not isinstance(time_value, str) or len(time_value) != 5:
                    raise HTTPException(
                        status_code=400,
                        detail=f"时间格式错误，请使用 HH:MM 格式，如：22:00"
                    )

        updated_preferences = update_user_preferences(user_id, **update_data)

        return {
            "success": True,
            "message": "偏好设置已更新",
            "preferences": updated_preferences.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新偏好设置失败: {str(e)}")


@router.get("/habits")
def get_habits(user_id: int = 1):
    """
    获取已学习的习惯摘要

    Args:
        user_id: 用户ID

    Returns:
        学习习惯摘要
    """
    try:
        result = get_learned_habits_summary(user_id)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "未知错误"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取习惯摘要失败: {str(e)}")


@router.delete("/habits/{keyword}")
def delete_habit(keyword: str, user_id: int = 1):
    """
    删除指定的学习习惯

    Args:
        keyword: 习惯关键词
        user_id: 用户ID

    Returns:
        操作结果
    """
    try:
        success = delete_learned_habit(keyword, user_id)
        if success:
            return {
                "success": True,
                "message": f"已删除习惯: {keyword}"
            }
        else:
            raise HTTPException(status_code=404, detail=f"习惯不存在: {keyword}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除习惯失败: {str(e)}")


@router.post("/habits/reset")
def reset_habits(user_id: int = 1):
    """
    重置所有学习习惯

    Args:
        user_id: 用户ID

    Returns:
        操作结果
    """
    try:
        success = reset_all_habits(user_id)
        if success:
            return {
                "success": True,
                "message": "已重置所有学习习惯"
            }
        else:
            raise HTTPException(status_code=500, detail="重置失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置习惯失败: {str(e)}")


@router.post("/keywords/custom")
def add_keyword(request: CustomKeywordRequest):
    """
    添加自定义关键词

    Args:
        request: 自定义关键词请求

    Returns:
        操作结果
    """
    try:
        success = add_custom_keyword(request.keyword, request.category, request.user_id)
        if success:
            return {
                "success": True,
                "message": f"已添加自定义关键词: {request.keyword} -> {request.category}"
            }
        else:
            raise HTTPException(status_code=500, detail="添加失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加关键词失败: {str(e)}")


@router.post("/nickname")
def set_assistant_nickname(request: AssistantNicknameRequest):
    """设置智能助手的称谓"""
    try:
        if not request.nickname or len(request.nickname.strip()) == 0:
            raise HTTPException(status_code=400, detail="称谓不能为空")
        
        if len(request.nickname) > 20:
            raise HTTPException(status_code=400, detail="称谓不能超过20个字符")
        
        from app.models.task_model import update_user_preferences
        
        nickname = request.nickname.strip()
        update_user_preferences(request.user_id, assistant_nickname=nickname)
        
        return {
            "success": True,
            "message": f"已成功设置助手称谓为「{nickname}」",
            "nickname": nickname
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置称谓失败: {str(e)}")


@router.post("/user-nickname")
def set_user_nickname(request: UserNicknameRequest):
    """设置用户的称谓（助手如何称呼你）"""
    try:
        if not request.nickname or len(request.nickname.strip()) == 0:
            raise HTTPException(status_code=400, detail="称谓不能为空")
        
        if len(request.nickname) > 20:
            raise HTTPException(status_code=400, detail="称谓不能超过20个字符")
        
        from app.models.task_model import update_user_preferences
        
        nickname = request.nickname.strip()
        update_user_preferences(request.user_id, user_nickname=nickname)
        
        return {
            "success": True,
            "message": f"已成功设置你的称谓为「{nickname}」，助手会这样称呼你",
            "nickname": nickname
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置称谓失败: {str(e)}")


@router.get("/nickname")
def get_assistant_nickname(user_id: int = 1):
    """获取智能助手的称谓"""
    try:
        from app.models.task_model import get_user_preferences
        
        preferences = get_user_preferences(user_id)
        nickname = preferences.assistant_nickname if preferences else ""
        
        return {
            "success": True,
            "nickname": nickname,
            "has_nickname": bool(nickname)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取称谓失败: {str(e)}")


@router.get("/user-nickname")
def get_user_nickname(user_id: int = 1):
    """获取用户的称谓"""
    try:
        from app.models.task_model import get_user_preferences
        
        preferences = get_user_preferences(user_id)
        nickname = preferences.user_nickname if preferences else ""
        
        return {
            "success": True,
            "nickname": nickname,
            "has_nickname": bool(nickname)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取称谓失败: {str(e)}")


# ==================== ⭐ Phase 3: 用户画像管理 ====================

@router.post("/user-type")
def set_user_type(request: UserTypeRequest):
    """
    ⭐ Phase 3: 设置用户类型
    
    Args:
        request: 用户类型请求
    
    Returns:
        更新后的偏好设置
    """
    try:
        # 验证用户类型
        valid_types = ["student", "worker", "elderly"]
        if request.user_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"无效的用户类型，必须是: {', '.join(valid_types)}"
            )
        
        updated_preferences = update_user_preferences(
            request.user_id,
            user_type=request.user_type
        )
        
        return {
            "success": True,
            "message": f"用户类型已设置为: {request.user_type}",
            "preferences": updated_preferences.to_dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置用户类型失败: {str(e)}")


@router.get("/standard-profiles")
def get_standard_profiles():
    """
    ⭐ Phase 3: 获取所有标准作息模板
    
    Returns:
        标准作息模板列表
    """
    try:
        from app.services.standard_profile_service import standard_profile_service
        
        profiles = {}
        for profile_type in ["student", "worker", "elderly"]:
            profile = standard_profile_service.get_profile(profile_type)
            if profile:
                profiles[profile_type] = profile
        
        return {
            "success": True,
            "profiles": profiles
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取标准模板失败: {str(e)}")


@router.post("/personalization-params")
def set_personalization_params(request: PersonalizationParamsRequest):
    """
    ⭐ Phase 3: 设置个性化参数（带自动校验）
    
    Args:
        request: 个性化参数请求
    
    Returns:
        校验结果和更新后的偏好
    """
    try:
        from app.services.standard_profile_service import standard_profile_service
        
        user_id = request.user_id
        validation_errors = []
        validated_params = {}
        
        # 1. 校验工作时长
        if request.workday_hours is not None:
            is_valid, message, corrected_value = standard_profile_service.validate_personalization(
                "workday_hours",
                request.workday_hours
            )
            if is_valid:
                validated_params["workday_hours"] = corrected_value
            else:
                validation_errors.append({
                    "param": "workday_hours",
                    "error": message,
                    "corrected_value": corrected_value
                })
        
        # 2. 校验时间段偏移
        if request.time_slot_offset is not None:
            # ⚠️ validate_personalization 使用 time_slot_shift 作为参数名
            is_valid, message, corrected_value = standard_profile_service.validate_personalization(
                "time_slot_shift",
                request.time_slot_offset
            )
            if is_valid:
                validated_params["time_slot_offset"] = corrected_value
            else:
                validation_errors.append({
                    "param": "time_slot_offset",
                    "error": message,
                    "corrected_value": corrected_value
                })
        
        # 3. 校验最大连续工作时长
        if request.max_continuous_work is not None:
            if request.max_continuous_work < 1 or request.max_continuous_work > 8:
                validation_errors.append({
                    "param": "max_continuous_work",
                    "error": "最大连续工作时长必须在1-8小时之间",
                    "corrected_value": min(max(request.max_continuous_work, 1), 8)
                })
            else:
                validated_params["max_continuous_work"] = request.max_continuous_work
        
        # 4. 校验最小休息间隔
        if request.min_break_minutes is not None:
            if request.min_break_minutes < 5 or request.min_break_minutes > 60:
                validation_errors.append({
                    "param": "min_break_minutes",
                    "error": "最小休息间隔必须在5-60分钟之间",
                    "corrected_value": min(max(request.min_break_minutes, 5), 60)
                })
            else:
                validated_params["min_break_minutes"] = request.min_break_minutes
        
        # 5. 校验偏好时段
        if request.preferred_time_slot is not None:
            valid_slots = ["morning", "noon", "afternoon", "evening", "night"]
            if request.preferred_time_slot not in valid_slots:
                validation_errors.append({
                    "param": "preferred_time_slot",
                    "error": f"无效的时段，必须是: {', '.join(valid_slots)}"
                })
            else:
                validated_params["preferred_time_slot"] = request.preferred_time_slot
        
        # 如果有校验错误，返回警告信息
        has_warnings = len(validation_errors) > 0
        
        # 更新偏好设置（只更新通过校验的参数）
        if validated_params:
            update_user_preferences(user_id, **validated_params)
        
        return {
            "success": True,
            "message": "个性化参数已更新" + ("（部分参数已自动校正）" if has_warnings else ""),
            "validation_errors": validation_errors,
            "validated_params": validated_params
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置个性化参数失败: {str(e)}")
