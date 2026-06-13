"""任务管理路由"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from fastapi.responses import JSONResponse, StreamingResponse

from app.services.llm_service import parse_user_intent
from app.services.scheduler_service import schedule_task, detect_conflict, remember_user_preference
from app.services.or_tools_scheduler import ORToolsScheduler
from app.services.cache_service import redis_cache
from app.models.task_model import (
    create_task, get_task_by_id, get_all_tasks,
    update_task, delete_task, get_user_preferences
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ⭐ Phase 2A: 辅助函数 - 生成方案总结（从时间对象）
def _generate_schedule_summary_from_time(slot_start, entities):
    """为排程方案生成一句话总结"""
    hour = slot_start.hour
    
    # 根据时间段生成描述
    if 6 <= hour < 9:
        time_desc = "早晨"
    elif 9 <= hour < 12:
        time_desc = "上午"
    elif 12 <= hour < 14:
        time_desc = "中午"
    elif 14 <= hour < 18:
        time_desc = "下午"
    else:
        time_desc = "晚上"
    
    return f"安排在{time_desc}，符合您的习惯偏好"


# ⭐ Phase 2A: 辅助函数 - 获取方案优势（从时间对象）
def _get_schedule_advantages_from_time(slot_start, solution):
    """获取方案的优势标签"""
    advantages = []
    score = solution["score"]
    
    if score >= 80:
        advantages.append("综合评分高")
    
    # 检查是否在黄金时段
    hour = slot_start.hour
    if 9 <= hour <= 11 or 14 <= hour <= 16:
        advantages.append("黄金时段")
    
    # 检查是否当天完成
    if slot_start.date() == datetime.now().date():
        advantages.append("当天完成")
    
    if not advantages:
        advantages.append("时间可行")
    
    return advantages


# ⭐ Phase 2A: 辅助函数 - 获取方案劣势（从时间对象）
def _get_schedule_disadvantages_from_time(slot_start, solution):
    """获取方案的劣势标签"""
    disadvantages = []
    
    # 如果评分较低，给出提示
    score = solution["score"]
    if score < 50:
        disadvantages.append("评分较低")
    
    # 如果是晚上时段
    hour = slot_start.hour
    if hour >= 20:
        disadvantages.append("较晚时段")
    
    return disadvantages


# 请求模型
class ParseRequest(BaseModel):
    text: str


class TaskCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    duration: Optional[int] = None
    deadline: Optional[str] = None
    priority: Optional[str] = "medium"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    user_id: Optional[int] = 1


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    deadline: Optional[str] = None
    duration: Optional[int] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    force: Optional[bool] = False  # ✅ 新增：是否忽略冲突强制更新


@router.post("/parse")
def parse_task_text(request: ParseRequest):
    """
    解析自然语言输入，识别任务信息

    Args:
        request: 包含用户输入文本的请求

    Returns:
        解析后的任务信息
    """
    try:
        print(f"🔥 收到解析请求: {request.text}")
        
        result = parse_user_intent(request.text)
        
        # ⭐ 类型检查：确保 result 是字典
        if not isinstance(result, dict):
            print(f"❌ parse_user_intent 返回了非字典类型: {type(result)}")
            print(f"   返回值: {result}")
            raise ValueError(f"解析函数返回了错误类型: {type(result).__name__}")
        
        print(f"✅ 解析成功: intent={result.get('intent')}, confidence={result.get('confidence')}")
        print(f"📋 实体数据: {result.get('entities', {})}")
        
        # ⭐ Phase 1: 返回应用的 habit 信息
        response = {
            "success": True,
            "intent": result.get("intent", "add_task"),
            "entities": result.get("entities", {})
        }
        
        # 如果有应用的 habit，添加到响应中
        if result.get("applied_habits"):
            response["applied_habits"] = result["applied_habits"]
            print(f"✨ [Phase 1] 返回 {len(result['applied_habits'])} 个应用的习惯")
        
        # ⭐ Phase 2A: 智能排程方案生成（仅在检测到时间冲突时触发）
        entities = result.get("entities", {})
        if entities.get("start_time") or entities.get("deadline"):
            try:
                # 获取用户偏好和现有任务
                user_id = 1  # 默认用户ID
                preferences = get_user_preferences(user_id)
                prefs_dict = preferences.to_dict() if preferences else {}
                existing_tasks = [t.to_dict() for t in get_all_tasks(user_id)]
                
                # 检测冲突
                conflict_result = detect_conflict(entities, existing_tasks, prefs_dict)
                
                # 如果检测到冲突或即将创建定时任务，生成智能排程方案
                if conflict_result["has_conflict"] or entities.get("start_time"):
                    scheduler = ORToolsScheduler()
                    current_dt = datetime.now()
                    
                    # 生成 Top-3 方案（最优 + 2个备选）
                    schedule_result = scheduler.schedule_task(
                        new_task=entities,
                        existing_tasks=existing_tasks,
                        preferences=prefs_dict,
                        return_top_k=3,
                        current_date=current_dt
                    )
                    
                    if schedule_result["success"]:
                        # 格式化方案数据供前端展示
                        formatted_options = []
                        all_solutions = schedule_result.get("all_solutions", [])
                        
                        for idx, solution in enumerate(all_solutions):
                            # ⭐ OR-Tools 返回的已经是 ISO 格式字符串
                            start_time_str = solution["start_time"]
                            end_time_str = solution["end_time"]
                            
                            # 解析时间用于生成总结
                            slot_start = datetime.fromisoformat(start_time_str)
                            
                            # 生成方案类型标签
                            if idx == 0:
                                option_type = "最优平衡方案"
                                summary = f"⭐ 推荐：综合评分最高，{_generate_schedule_summary_from_time(slot_start, entities)}"
                            elif idx == 1:
                                option_type = "时间最早方案"
                                summary = f"🚀 最快完成：{_generate_schedule_summary_from_time(slot_start, entities)}"
                            else:
                                option_type = "最小改动方案"
                                summary = f"💡 备选方案：{_generate_schedule_summary_from_time(slot_start, entities)}"
                            
                            formatted_option = {
                                "rank": idx + 1,
                                "is_recommended": idx == 0,
                                "summary": summary,
                                "type": option_type,
                                "task_params": {
                                    "start_time": start_time_str,
                                    "end_time": end_time_str,
                                    "duration": entities.get("duration", 60),
                                    "priority": entities.get("priority", "medium")
                                },
                                "score": round(solution["score"], 1),
                                "advantages": _get_schedule_advantages_from_time(slot_start, solution),
                                "disadvantages": _get_schedule_disadvantages_from_time(slot_start, solution)
                            }
                            formatted_options.append(formatted_option)
                        
                        response["schedule_options"] = formatted_options
                        print(f"✨ [Phase 2A] 生成 {len(formatted_options)} 个智能排程方案")
                    
            except Exception as e:
                print(f"⚠️ 智能排程失败: {e}")
                import traceback
                traceback.print_exc()
                # 不影响主流程，仅记录日志
        
        return response
    except ValueError as e:
        # 捕获配置错误（如 API Key 缺失）
        print(f"❌ 配置错误: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"配置错误: {str(e)}。请检查后端 .env 文件中的 API 密钥配置。"
        )
    except Exception as e:
        # 捕获其他所有异常
        print(f"❌ 解析失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 返回更友好的错误信息
        error_detail = str(e)
        if "API" in error_detail or "api" in error_detail:
            error_detail = "LLM API 调用失败，请稍后重试或检查网络连接"
        elif "JSON" in error_detail or "json" in error_detail:
            error_detail = "解析结果格式错误，请尝试重新输入"
        elif "timeout" in error_detail.lower() or "超时" in error_detail:
            error_detail = "请求超时，请稍后重试"
        
        raise HTTPException(
            status_code=500, 
            detail=f"解析失败: {error_detail}"
        )


@router.post("/")
def create_new_task(request: TaskCreateRequest):
    """
    创建新任务并自动排程（含冲突检测）

    Args:
        request: 任务创建请求

    Returns:
        创建的任务信息及冲突信息
    """
    try:
        # 获取用户偏好
        preferences = get_user_preferences(request.user_id)
        prefs_dict = preferences.to_dict()

        # 捕获统一参考时间
        current_date = datetime.now()

        # 如果提供了start_time和end_time，直接创建任务并检测冲突
        if request.start_time and request.end_time:
            # 先检测冲突，不直接创建
            existing_tasks = [t.to_dict() for t in get_all_tasks(request.user_id)]
            
            conflict_result = detect_conflict(
                {"start_time": request.start_time, "end_time": request.end_time},
                existing_tasks,
                prefs_dict
            )

            # 如果有冲突，返回冲突信息，让用户决定
            if conflict_result["has_conflict"]:
                return {
                    "success": True,
                    "has_conflict": True,
                    "conflicts": conflict_result["conflicts"],
                    "task_preview": {
                        "title": request.title,
                        "description": request.description,
                        "start_time": request.start_time,
                        "end_time": request.end_time,
                        "deadline": request.deadline,
                        "duration": request.duration,
                        "priority": request.priority or "medium"
                    },
                    "message": f"检测到 {len(conflict_result['conflicts'])} 个时间冲突",
                    "options": {
                        "auto_adjust": "自动调整到空闲时间段",
                        "ignore": "忽略冲突，强制添加",
                        "cancel": "取消添加"
                    }
                }

            # 没有冲突，直接创建
            task = create_task(
                title=request.title,
                user_id=request.user_id,
                description=request.description,
                start_time=request.start_time,
                end_time=request.end_time,
                deadline=request.deadline,
                duration=request.duration,
                priority=request.priority or "medium"
            )

            # 清除缓存
            redis_cache.clear_pattern(f"tasks:{request.user_id}:*")

            return {
                "success": True,
                "has_conflict": False,
                "task": task.to_dict(),
                "message": "任务创建成功"
            }

        # 否则使用排程服务自动安排时间（会自动避开冲突）
        new_task_info = {
            "title": request.title,
            "duration": request.duration,
            "deadline": request.deadline,
            "priority": request.priority or "medium"
        }

        existing_tasks = [t.to_dict() for t in get_all_tasks(request.user_id)]

        schedule_result = schedule_task(new_task_info, existing_tasks, prefs_dict, current_date=current_date)

        if not schedule_result["success"]:
            return {
                "success": False,
                "message": schedule_result["message"],
                "suggestions": schedule_result.get("suggestions", []),
                "task_preview": {
                    "title": request.title,
                    "duration": request.duration,
                    "deadline": request.deadline,
                    "priority": request.priority
                }
            }

        # 创建任务
        task = create_task(
            title=request.title,
            user_id=request.user_id,
            description=request.description,
            start_time=schedule_result["scheduled_time"]["start_time"],
            end_time=schedule_result["scheduled_time"]["end_time"],
            deadline=request.deadline,
            duration=request.duration,
            priority=request.priority or "medium"
        )

        # 清除缓存
        redis_cache.clear_pattern(f"tasks:{request.user_id}:*")

        return {
            "success": True,
            "has_conflict": False,
            "task": task.to_dict(),
            "schedule_info": schedule_result,
            "message": "已自动安排到合适时间"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


# 新增：确认添加任务（处理冲突后的操作）
class ConfirmTaskRequest(BaseModel):
    action: str  # "auto_adjust" | "ignore" | "cancel"
    task_data: dict
    user_id: Optional[int] = 1


@router.post("/confirm")
def confirm_create_task(request: ConfirmTaskRequest):
    """
    确认添加任务（处理冲突后的用户选择）
    
    Args:
        request: 包含用户选择的动作和任务数据
    
    Returns:
        处理结果
    """
    try:
        task_data = request.task_data
        user_id = request.user_id
        
        # 捕获统一参考时间
        current_date = datetime.now()
        
        # 获取用户偏好
        preferences = get_user_preferences(user_id)
        prefs_dict = preferences.to_dict()
        
        if request.action == "cancel":
            return {
                "success": True,
                "message": "已取消添加任务"
            }
        
        elif request.action == "ignore":
            # 忽略冲突，直接创建
            task = create_task(
                title=task_data["title"],
                user_id=user_id,
                description=task_data.get("description"),
                start_time=task_data.get("start_time"),
                end_time=task_data.get("end_time"),
                deadline=task_data.get("deadline"),
                duration=task_data.get("duration"),
                priority=task_data.get("priority", "medium")
            )
            
            # ⭐ 清除缓存，确保任务列表立即更新
            redis_cache.clear_pattern(f"tasks:{user_id}:*")
            
            return {
                "success": True,
                "task": task.to_dict(),
                "message": "任务已添加（存在时间冲突）",
                "warning": "该任务与已有任务时间重叠，请手动调整"
            }
        
        elif request.action == "auto_adjust":
            # 自动调整到空闲时间段
            existing_tasks = [t.to_dict() for t in get_all_tasks(user_id)]
            
            schedule_result = schedule_task(task_data, existing_tasks, prefs_dict, current_date=current_date)
            
            if not schedule_result["success"]:
                return {
                    "success": False,
                    "message": schedule_result["message"],
                    "suggestions": schedule_result.get("suggestions", [])
                }
            
            # 创建任务
            task = create_task(
                title=task_data["title"],
                user_id=user_id,
                description=task_data.get("description"),
                start_time=schedule_result["scheduled_time"]["start_time"],
                end_time=schedule_result["scheduled_time"]["end_time"],
                deadline=task_data.get("deadline"),
                duration=task_data.get("duration"),
                priority=task_data.get("priority", "medium")
            )
            
            # ⭐ 清除缓存，确保任务列表立即更新
            redis_cache.clear_pattern(f"tasks:{user_id}:*")
            
            return {
                "success": True,
                "task": task.to_dict(),
                "adjusted_time": schedule_result["scheduled_time"],
                "message": f"已自动调整时间: {schedule_result['scheduled_time']['start_time'][11:16]}-{schedule_result['scheduled_time']['end_time'][11:16]}"
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"未知的动作: {request.action}")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/")
def list_tasks(user_id: int = 1, status: Optional[str] = None):
    """
    获取用户的所有任务（带 Redis 缓存，自动检查超时状态）

    Args:
        user_id: 用户ID
        status: 可选的状态过滤（pending/done/cancelled/overdue）

    Returns:
        任务列表
    """
    try:
        from app.services.scheduler_service import check_deadline_reminders
        
        #  先检查并更新超时任务（每次获取任务列表时都检查）
        check_deadline_reminders(user_id)
        
        #  清除缓存，确保获取最新的任务状态
        redis_cache.clear_pattern(f"tasks:{user_id}:*")
        
        # 查询数据库（获取最新数据）
        tasks = get_all_tasks(user_id, status)
        task_dicts = [task.to_dict() for task in tasks]
        
        # 写入缓存（5分钟）
        ttl = int(os.getenv("CACHE_TTL_TASKS", 300))
        cache_key = f"tasks:{user_id}:{status or 'all'}"
        redis_cache.set(cache_key, task_dicts, ttl=ttl)
        
        return {
            "success": True,
            "count": len(task_dicts),
            "tasks": task_dicts,
            "from_cache": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.put("/{task_id}")
def update_existing_task(task_id: int, request: TaskUpdateRequest, user_id: int = 1):
    """
    更新任务信息（支持拖拽调整时间，含冲突检测）

    Args:
        task_id: 任务ID
        request: 更新请求（包含 force 参数用于忽略冲突）
        user_id: 用户ID

    Returns:
        更新后的任务信息或冲突信息
    """
    try:
        # 检查任务是否存在
        existing = get_task_by_id(task_id, user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 准备更新数据
        update_data = request.dict(exclude_unset=True)
        force_update = update_data.pop("force", False)  # ✅ 提取 force 参数

        if not update_data:
            return {
                "success": True,
                "task": existing.to_dict(),
                "message": "没有需要更新的字段"
            }

        # ✅ 添加调试日志
        print(f"📝 更新任务 {task_id}: {update_data}")

        # ⭐ 新增：记录用户的调整习惯（用于长期记忆）
        # 在更新前记录优先级调整
        if "priority" in update_data and update_data["priority"] != existing.priority:
            print(f"🧠 检测到优先级调整: {existing.title} | {existing.priority} → {update_data['priority']}")
            remember_user_preference(
                task_title=existing.title,
                adjustment_type="priority",
                old_value=existing.priority,
                new_value=update_data["priority"],
                user_id=user_id
            )
        
        # 在更新前记录时长调整
        if "duration" in update_data and update_data["duration"] != existing.duration:
            print(f"🧠 检测到时长调整: {existing.title} | {existing.duration}分钟 → {update_data['duration']}分钟")
            remember_user_preference(
                task_title=existing.title,
                adjustment_type="duration",
                old_value=existing.duration,
                new_value=update_data["duration"],
                user_id=user_id,
                context={"original_estimate": existing.duration}
            )

        # 如果更新了时间，检测冲突
        if "start_time" in update_data or "end_time" in update_data:
            existing_tasks = [t.to_dict() for t in get_all_tasks(user_id)]
            # 排除当前任务
            existing_tasks = [t for t in existing_tasks if t["id"] != task_id]

            conflict_check = {
                "start_time": update_data.get("start_time", existing.start_time),
                "end_time": update_data.get("end_time", existing.end_time)
            }

            # ✅ 修复：获取用户偏好，如果不存在则创建默认偏好
            preferences = get_user_preferences(user_id)
            if not preferences:
                from app.models.task_model import create_user_preferences
                print(f"⚠️ 用户 {user_id} 没有偏好设置，创建默认偏好")
                preferences = create_user_preferences(user_id=user_id)
            
            conflict_result = detect_conflict(
                conflict_check,
                existing_tasks,
                preferences.to_dict()
            )

            if conflict_result["has_conflict"]:
                if force_update:
                    # ✅ 用户选择忽略冲突，强制更新
                    updated_task = update_task(task_id, user_id, **update_data)
                    
                    if not updated_task:
                        raise HTTPException(status_code=500, detail="更新任务失败")
                    
                    return {
                        "success": True,
                        "task": updated_task.to_dict(),
                        "message": "任务更新成功（存在时间冲突）",
                        "has_conflict": True,
                        "conflicts": conflict_result["conflicts"],
                        "warning": "该任务与已有任务时间重叠，请手动处理"
                    }
                else:
                    # ✅ 有冲突且用户未选择强制更新，返回冲突信息
                    return {
                        "success": False,
                        "message": "时间调整会导致冲突",
                        "has_conflict": True,
                        "conflicts": conflict_result["conflicts"],
                        "task": existing.to_dict()
                    }

        # 执行更新
        updated_task = update_task(task_id, user_id, **update_data)

        if not updated_task:
            raise HTTPException(status_code=500, detail="更新任务失败")

        # ⭐ 清除任务缓存，确保前端能获取最新数据
        redis_cache.clear_pattern(f"tasks:{user_id}:*")
        print(f"✅ 已更新任务 {task_id}，并清除缓存")

        return {
            "success": True,
            "task": updated_task.to_dict(),
            "message": "任务更新成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        # ✅ 增强错误日志
        import traceback
        print(f"❌ 更新任务失败: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"更新任务失败: {str(e)}")


@router.delete("/{task_id}")
def delete_existing_task(task_id: int, user_id: int = 1):
    """
    删除任务

    Args:
        task_id: 任务ID
        user_id: 用户ID

    Returns:
        删除结果
    """
    try:
        existing = get_task_by_id(task_id, user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="任务不存在")

        success = delete_task(task_id, user_id)

        if not success:
            raise HTTPException(status_code=500, detail="删除任务失败")

        # ⭐ 清除任务缓存，确保前端能获取最新数据
        redis_cache.clear_pattern(f"tasks:{user_id}:*")
        print(f"️ 已删除任务 {task_id}，并清除缓存")

        return {
            "success": True,
            "message": f"任务「{existing.title}」已删除",
            "deleted_task_id": task_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


class BatchDeleteRequest(BaseModel):
    task_ids: List[int]
    user_id: Optional[int] = 1


@router.post("/batch-delete")
def batch_delete_tasks(request: BatchDeleteRequest):
    """
    批量删除任务

    Args:
        request: 包含任务ID列表的请求

    Returns:
        批量删除结果
    """
    try:
        deleted_count = 0
        failed_tasks = []
        
        for task_id in request.task_ids:
            try:
                existing = get_task_by_id(task_id, request.user_id)
                if existing:
                    success = delete_task(task_id, request.user_id)
                    if success:
                        deleted_count += 1
                    else:
                        failed_tasks.append({"id": task_id, "reason": "删除失败"})
                else:
                    failed_tasks.append({"id": task_id, "reason": "任务不存在"})
            except Exception as e:
                failed_tasks.append({"id": task_id, "reason": str(e)})
        
        # ⭐ 清除任务缓存，确保前端能获取最新数据
        if deleted_count > 0:
            redis_cache.clear_pattern(f"tasks:{request.user_id}:*")
            print(f"️ 已批量删除 {deleted_count} 个任务，并清除缓存")
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "failed_count": len(failed_tasks),
            "failed_tasks": failed_tasks,
            "message": f"成功删除 {deleted_count} 个任务" + (f"，{len(failed_tasks)} 个失败" if failed_tasks else "")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")


@router.get("/conflicts")
def check_conflicts(user_id: int = 1):
    """
    检测用户所有任务的冲突情况

    Args:
        user_id: 用户ID

    Returns:
        冲突检测结果
    """
    try:
        tasks = get_all_tasks(user_id)
        preferences = get_user_preferences(user_id)

        conflicts = []

        # 检查每个任务与其他任务的冲突
        for i, task1 in enumerate(tasks):
            if not task1.start_time or not task1.end_time:
                continue

            for j, task2 in enumerate(tasks):
                if i >= j or not task2.start_time or not task2.end_time:
                    continue

                # 检查时间重叠
                from app.services.scheduler_service import check_overlap, parse_time

                start1 = parse_time(task1.start_time)
                end1 = parse_time(task1.end_time)
                start2 = parse_time(task2.start_time)
                end2 = parse_time(task2.end_time)

                if start1 and end1 and start2 and end2:
                    if check_overlap(start1, end1, start2, end2):
                        conflicts.append({
                            "type": "time_overlap",
                            "task1": {
                                "id": task1.id,
                                "title": task1.title,
                                "time": f"{task1.start_time} - {task1.end_time}"
                            },
                            "task2": {
                                "id": task2.id,
                                "title": task2.title,
                                "time": f"{task2.start_time} - {task2.end_time}"
                            }
                        })

        return {
            "success": True,
            "total_tasks": len(tasks),
            "conflict_count": len(conflicts),
            "conflicts": conflicts
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检测冲突失败: {str(e)}")
