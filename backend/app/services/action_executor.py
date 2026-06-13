"""动作执行器 - 纯粹的执行者

设计理念：
- 解耦意图识别与业务逻辑
- 通过注册表模式管理所有可用动作
- 每个动作独立、可测试、可替换
- 翻译官(LLM)只负责输出动作名和参数，不关心具体实现
"""
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta


class ActionExecutor:
    """纯粹的动作执行器

    职责：
    1. 接收动作名称和参数
    2. 查找对应的执行函数
    3. 执行并返回结果数据（不包含自然语言回复）

    不负责：
    - 意图识别（由LLM完成）
    - 生成自然语言回复（由LLM完成）
    - 业务逻辑判断（由各动作函数内部处理）
    """

    def __init__(self):
        self._actions: Dict[str, Callable] = {}
        self._action_metadata: Dict[str, Dict] = {}

    def register_action(self, name: str, func: Callable, metadata: Dict = None):
        """注册一个动作

        Args:
            name: 动作名称（如 "add_task", "query_free_time"）
            func: 执行函数
            metadata: 动作元数据（描述、参数说明等）
        """
        self._actions[name] = func
        self._action_metadata[name] = metadata or {
            "description": f"执行 {name} 操作",
            "parameters": {}
        }
        print(f"✅ 注册动作: {name}")

    def execute(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行指定动作

        Args:
            action_name: 动作名称
            params: 动作参数

        Returns:
            执行结果字典，包含 success 字段和数据
        """
        if action_name not in self._actions:
            return {
                "success": False,
                "error": f"未知动作: {action_name}",
                "available_actions": list(self._actions.keys())
            }

        try:
            print(f"🔧 执行动作: {action_name}, 参数: {params}")
            result = self._actions[action_name](**params)
            return result
        except Exception as e:
            print(f"❌ 动作执行失败: {action_name}, 错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "action": action_name
            }

    def get_available_actions(self) -> Dict[str, Dict]:
        """获取所有已注册的动作及其元数据"""
        return self._action_metadata.copy()

    def has_action(self, action_name: str) -> bool:
        """检查动作是否存在"""
        return action_name in self._actions


# 全局执行器实例
executor = ActionExecutor()


# ⭐ 辅助函数：为排程方案生成一句话总结
def _enrich_solution_with_summary(solution, index=0):
    """为 OR-Tools 排程方案添加 summary 字段"""
    if not solution:
        return solution
    
    try:
        start_str = solution.get("start_time", "")
        if start_str:
            slot_start = datetime.fromisoformat(start_str)
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
            elif 18 <= hour < 22:
                time_desc = "晚上"
            else:
                time_desc = "夜间"
            
            # 根据 index 生成不同类型的总结
            if index == 0:
                summary = f"⭐ 推荐：安排在{time_desc}，综合评分最高"
            elif index == 1:
                summary = f"🚀 备选：安排在{time_desc}，时间较早"
            else:
                summary = f"💡 备选：安排在{time_desc}，可选方案"
            
            solution["summary"] = summary
    except Exception as e:
        print(f"⚠️ 生成方案总结失败: {e}")
        solution["summary"] = "时间可行方案"
    
    return solution


# ==================== 动作函数定义 ====================

def action_add_task(
    title: str,
    duration: int,
    deadline: str = None,
    priority: str = "medium",
    user_id: int = 1,
    requested_start_time: str = None,
    requested_end_time: str = None,
    user_text: str = None,
    current_date: str = None
) -> Dict[str, Any]:
    """
    添加任务（使用OR-Tools约束规划自动排程）
    
    Args:
        user_text: 智能排程时用户的原话（如"明天写报告"），用于回溯和习惯学习
        current_date: 统一参考时间（入口处捕获），避免跨天漂移
    
    返回:
    {
        "success": True,
        "task": {...},
        "scheduled_time": {...},
        "has_conflict": False,
        "conflicts": [],
        "alternative_solutions": [...],
        "time_adjusted": True/False,
        "requested_time": {...},
        "adjustment_reason": "..."
    }
    """
    from app.services.or_tools_scheduler import or_scheduler
    from app.services.cache_service import redis_cache
    from app.models.task_model import get_user_preferences, get_all_tasks, create_task

    try:
        # 解析统一参考时间
        ref_date = datetime.fromisoformat(current_date) if current_date else None

        # 获取用户偏好
        prefs = get_user_preferences(user_id)
        prefs_dict = prefs.to_dict() if prefs else {}

        # 获取所有现有任务
        all_tasks = get_all_tasks(user_id)
        existing_tasks = [t.to_dict() for t in all_tasks]

        # 准备任务信息
        task_info = {
            "title": title,
            "duration": duration,
            "deadline": deadline,
            "priority": priority,
            "user_id": user_id
        }

        # ⭐ 如果用户指定了时间，先检测冲突
        if requested_start_time and requested_end_time:
            from app.services.conflict_detector import conflict_detector
            
            # 构建区间树并检测冲突
            conflict_detector.build_from_tasks(existing_tasks)
            conflicts = conflict_detector.find_conflicts(
                requested_start_time,
                requested_end_time,
                buffer_minutes=prefs_dict.get("task_buffer_minutes", 15)
            )
            
            if conflicts:
                # ⭐ 有冲突，调用 OR-Tools 生成智能排程方案
                print(f"⚠️ 检测到冲突，调用 OR-Tools 生成备选方案...")
                
                schedule_result = or_scheduler.schedule_task(
                    new_task=task_info,
                    existing_tasks=existing_tasks,
                    preferences=prefs_dict,
                    return_top_k=5,
                    current_date=ref_date
                )
                
                if not schedule_result["success"]:
                    # 排程失败，返回错误
                    return {
                        "success": False,
                        "has_conflict": True,
                        "conflicts": conflicts,
                        "task_preview": {
                            "title": title,
                            "duration": duration,
                            "deadline": deadline,
                            "priority": priority,
                            "start_time": requested_start_time,
                            "end_time": requested_end_time
                        },
                        "message": schedule_result["message"],
                        "suggestions": schedule_result.get("suggestions", [])
                    }
                
                # 提取方案
                best_solution = schedule_result["best_solution"]
                alternative_solutions = schedule_result.get("all_solutions", [])
                
                # ⭐ 为方案添加 summary 字段
                _enrich_solution_with_summary(best_solution, 0)
                for idx, sol in enumerate(alternative_solutions):
                    _enrich_solution_with_summary(sol, idx)
                
                # ⭐ 关键修复：清除缓存，确保前端立即获取最新数据
                redis_cache.clear_pattern(f"tasks:{user_id}:*")
                redis_cache.clear_pattern(f"task_list:{user_id}:*")
                print(f"✅ 已清除用户 {user_id} 的任务缓存")
                
                # 有冲突，返回冲突信息和智能排程方案供用户选择
                return {
                    "success": True,
                    "has_conflict": True,
                    "conflicts": conflicts,
                    "recommendedSolution": best_solution,
                    "alternativeSolutions": alternative_solutions[1:] if len(alternative_solutions) > 1 else [],
                    "task_preview": {
                        "title": title,
                        "duration": duration,
                        "deadline": deadline,
                        "priority": priority,
                        "start_time": requested_start_time,
                        "end_time": requested_end_time
                    },
                    "message": f"检测到 {len(conflicts)} 个时间冲突",
                    "options": {
                        "ignore": "忽略冲突，强制添加",
                        "auto_adjust": "自动调整到最优时间段",
                        "cancel": "取消添加"
                    }
                }
            
            # ⭐⭐ 核心修复：用户指定时间且无冲突 → 直接使用用户指定时间，不调用 OR-Tools
            # 之前这里会 fall through 到 OR-Tools，导致用户指定时间被无声覆盖
            print(f"✅ 用户指定时间无冲突，直接创建任务: {requested_start_time} - {requested_end_time}")
            
            task = create_task(
                title=title,
                user_id=user_id,
                description="",
                start_time=requested_start_time,
                end_time=requested_end_time,
                deadline=deadline,
                duration=duration,
                priority=priority,
                user_text=user_text
            )
            
            # 清除缓存
            redis_cache.clear_pattern(f"tasks:{user_id}:*")
            
            return {
                "success": True,
                "task": task.to_dict(),
                "scheduled_time": {
                    "start_time": requested_start_time,
                    "end_time": requested_end_time
                },
                "alternativeSolutions": [],
                "has_conflict": False,
                "time_adjusted": False,
                "requested_time": {
                    "start_time": requested_start_time,
                    "end_time": requested_end_time
                },
                "adjustment_reason": "",
                "stats": {},
                "message": f"已按指定时间为「{title}」创建任务"
            }
        
        # ⭐ 用户未指定时间 → 调用 OR-Tools 智能排程
        schedule_result = or_scheduler.schedule_task(
            new_task=task_info,
            existing_tasks=existing_tasks,
            preferences=prefs_dict,
            return_top_k=5,
            current_date=ref_date
        )

        if not schedule_result["success"]:
            # P0/P1: 转发连续性和拆分建议
            return {
                "success": False,
                "error": schedule_result["message"],
                "can_complete_continuously": schedule_result.get("can_complete_continuously", False),
                "split_suggestions": schedule_result.get("split_suggestions", []),
                "suggestions": schedule_result.get("suggestions", []),
                "load_warning": schedule_result.get("load_warning")  # 负荷警告
            }
        
        # 提取最优方案
        best_solution = schedule_result["best_solution"]
        alternative_solutions = schedule_result.get("alternativeSolutions", [])
        
        # 创建任务（智能排程，传入 user_text 用于回溯）
        task = create_task(
            title=title,
            user_id=user_id,
            description="",
            start_time=best_solution["start_time"],
            end_time=best_solution["end_time"],
            deadline=deadline,
            duration=duration,
            priority=priority,
            user_text=user_text
        )
        
        # 清除缓存
        redis_cache.clear_pattern(f"tasks:{user_id}:*")
        
        return {
            "success": True,
            "task": task.to_dict(),
            "scheduled_time": {
                "start_time": best_solution["start_time"],
                "end_time": best_solution["end_time"]
            },
            "alternativeSolutions": alternative_solutions,
            "has_conflict": False,
            "time_adjusted": False,
            "requested_time": None,
            "adjustment_reason": "",
            "stats": schedule_result.get("stats", {}),
            "message": schedule_result["message"],
            "load_warning": schedule_result.get("load_warning")  # 负荷警告
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


def action_query_free_time(
        user_id: int,
        time_range: str = "tomorrow",
        activity: str = "rest",
        **kwargs
) -> Dict[str, Any]:
    """查询空闲时间动作"""
    from app.services.scheduler_service import analyze_free_time

    try:
        analysis = analyze_free_time(user_id, time_range, activity)
        return {
            "success": True,
            "analysis": analysis
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "分析空闲时间失败"
        }


def action_analyze_workload(
        user_id: int,
        time_range: str = "this_week",
        **kwargs
) -> Dict[str, Any]:
    """分析工作负载动作"""
    from app.models.task_model import get_all_tasks
    from datetime import timedelta

    tasks = get_all_tasks(user_id)
    now = datetime.now()
    
    if time_range == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        label = "今天"
    elif time_range == "tomorrow":
        start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        label = "明天"
    elif time_range == "this_week":
        days_since_monday = now.weekday()
        start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        label = "本周"
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        label = "未来7天"

    # ⭐ 修复：解析任务时间字符串为 datetime 对象后再比较
    day_tasks = []
    for t in tasks:
        if t.start_time and t.status != "cancelled":
            try:
                task_start = datetime.fromisoformat(t.start_time) if isinstance(t.start_time, str) else t.start_time
                if start <= task_start < end:
                    day_tasks.append(t)
            except (ValueError, TypeError):
                continue

    total_minutes = sum(t.duration or 0 for t in day_tasks)
    available_hours = (end - start).total_seconds() / 3600
    available_minutes = available_hours * 60
    density = (total_minutes / available_minutes * 100) if available_minutes > 0 else 0

    return {
        "success": True,
        "analysis": {
            "time_range": time_range,
            "day_label": label,
            "task_count": len(day_tasks),
            "total_minutes": total_minutes,
            "available_minutes": available_minutes,
            "density_percent": density,
            "tasks": [{"title": t.title, "start_time": t.start_time.isoformat() if isinstance(t.start_time, datetime) else t.start_time, "duration": t.duration} for t in
                      day_tasks[:10]]
        }
    }


def action_modify_task(
        task_id: int,
        user_id: int,
        title: str = None,
        start_time: str = None,
        end_time: str = None,
        duration: int = None,
        priority: str = None,
        status: str = None,
        deadline: str = None,
        **kwargs
) -> Dict[str, Any]:
    """修改任务动作"""
    from app.models.task_model import get_task_by_id, update_task, get_all_tasks
    from app.services.scheduler_service import detect_conflict, remember_user_preference

    # 检查任务是否存在
    existing = get_task_by_id(task_id, user_id)
    if not existing:
        return {
            "success": False,
            "error": "任务不存在"
        }

    # 准备更新数据
    update_data = {}
    if title:
        update_data["title"] = title
    if start_time:
        update_data["start_time"] = start_time
    if end_time:
        update_data["end_time"] = end_time
    if duration:
        update_data["duration"] = duration
    if priority:
        update_data["priority"] = priority
    if status:
        update_data["status"] = status
    if deadline:
        update_data["deadline"] = deadline

    if not update_data:
        return {
            "success": False,
            "error": "没有需要更新的字段"
        }

    # 记录用户调整习惯
    if "priority" in update_data and update_data["priority"] != existing.priority:
        remember_user_preference(
            task_title=existing.title,
            adjustment_type="priority",
            old_value=existing.priority,
            new_value=update_data["priority"],
            user_id=user_id
        )

    if "duration" in update_data and update_data["duration"] != existing.duration:
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
        existing_tasks = [t for t in existing_tasks if t["id"] != task_id]

        from app.models.task_model import get_user_preferences
        preferences = get_user_preferences(user_id)
        if not preferences:
            from app.models.task_model import create_user_preferences
            preferences = create_user_preferences(user_id=user_id)

        conflict_check = {
            "start_time": update_data.get("start_time", existing.start_time),
            "end_time": update_data.get("end_time", existing.end_time)
        }

        conflict_result = detect_conflict(
            conflict_check,
            existing_tasks,
            preferences.to_dict()
        )

        if conflict_result["has_conflict"]:
            return {
                "success": False,
                "has_conflict": True,
                "conflicts": conflict_result["conflicts"],
                "message": "时间调整会导致冲突"
            }

    # 执行更新
    updated_task = update_task(task_id, user_id, **update_data)

    if not updated_task:
        return {
            "success": False,
            "error": "更新任务失败"
        }

    # 清除缓存
    from app.services.cache_service import redis_cache
    redis_cache.clear_pattern(f"tasks:{user_id}:*")

    return {
        "success": True,
        "task": updated_task.to_dict(),
        "message": "任务更新成功"
    }


def action_delete_task(
        task_id: int,
        user_id: int,
        **kwargs
) -> Dict[str, Any]:
    """删除任务动作"""
    from app.models.task_model import get_task_by_id, delete_task
    from app.services.cache_service import redis_cache

    existing = get_task_by_id(task_id, user_id)
    if not existing:
        return {
            "success": False,
            "error": "任务不存在"
        }

    success = delete_task(task_id, user_id)

    if not success:
        return {
            "success": False,
            "error": "删除任务失败"
        }

    # 清除缓存
    redis_cache.clear_pattern(f"tasks:{user_id}:*")

    return {
        "success": True,
        "deleted_task_id": task_id,
        "deleted_task_title": existing.title,
        "message": f"任务「{existing.title}」已删除"
    }


def action_query_today_tasks(
        user_id: int,
        date: str = None,
        date_description: str = None,
        out_of_range: bool = False,
        **kwargs
) -> Dict[str, Any]:
    """查询今日/指定日期任务列表动作
    
    支持范围: 大前天 ~ 大后天（前后3天）
    超出范围请引导用户使用任务列表搜索功能
    """
    from app.models.task_model import get_tasks_by_date
    
    try:
        # 修改：范围限制为3天
        QUERY_RANGE_DAYS = 3
        
        print(f"🔍 action_query_today_tasks 收到参数: date={date}, date_description={date_description}, out_of_range={out_of_range}")
        
        # 确定目标日期
        target_date = None
        
        if date:
            target_date = date
            print(f"✅ 使用传入的 date: {target_date}")
        elif date_description:
            target_date = parse_relative_date(date_description)
            print(f"✅ 解析 date_description: {date_description} → {target_date}")
        else:
            target_date = datetime.now().strftime("%Y-%m-%d")
            print(f"✅ 使用默认今天: {target_date}")
        
        # 后端校验：3天范围
        if not is_date_in_range(target_date, days=QUERY_RANGE_DAYS):
            print(f"⚠️ 日期 {target_date} 超出范围（±{QUERY_RANGE_DAYS}天）")
            # ⭐ 修复：返回 success: True，让 chat_router 调用 _generate_reply_from_data 生成个性化回复
            return {
                "success": True,  # ⭐ 改为 True
                "out_of_range": True,
                "date": target_date,
                "date_description": date_description or target_date,
                "message": f"抱歉，{date_description or target_date}超出了查询范围（前后{QUERY_RANGE_DAYS}天）",
                "suggestions": [
                    f"查看今天/昨天/明天的任务",
                    f"查看大前天/大后天的任务",
                    "使用任务列表的搜索功能查看更早的任务 "
                ]
            }
        
        # LLM 标记了超出范围，但后端校验通过（LLM误判），继续执行
        if out_of_range and is_date_in_range(target_date, days=QUERY_RANGE_DAYS):
            print(f"️ LLM误判：{date_description} 实际在范围内，继续执行")
        
        print(f"📊 开始查询数据库: user_id={user_id}, date={target_date}")
        
        # 查询数据库
        tasks = get_tasks_by_date(user_id, target_date)
        
        print(f"✅ 查询成功: 找到 {len(tasks)} 个任务")
        
        return {
            "success": True,
            "date": target_date,
            "date_description": date_description or "今天",
            "count": len(tasks),
            "tasks": [t.to_dict() for t in tasks]
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "message": "查询任务失败"
        }


def parse_relative_date(description: str) -> str:
    """
    解析相对日期描述为具体日期（YYYY-MM-DD格式）
    
    支持:
    - 昨天、前天、大前天
    - 明天、后天、大后天
    - 上周X、下周X
    - N天前、N天后（支持阿拉伯数字和中文数字）
    - 前第N天、后第N天（新增）
    - X月X日（今年）
    
    Args:
        description: 相对日期描述
        
    Returns:
        日期字符串，如 "2026-05-18"
    """
    now = datetime.now()
    
    print(f"🔍 解析日期描述: '{description}'")
    
    # 简单映射
    relative_map = {
        "今天": 0,
        "昨天": -1,
        "前天": -2,
        "大前天": -3,
        "明天": 1,
        "后天": 2,
        "大后天": 3,
    }
    
    if description in relative_map:
        days_offset = relative_map[description]
        target = now + timedelta(days=days_offset)
        print(f"✅ 匹配简单映射: {days_offset}天")
        return target.strftime("%Y-%m-%d")
    
    # 处理"上周X"、"下周X"
    weekday_map = {
        "周一": 0, "周二": 1, "周三": 2, "周四": 3,
        "周五": 4, "周六": 5, "周日": 6
    }
    
    if "上周" in description:
        for day_name, day_num in weekday_map.items():
            if day_name in description:
                current_weekday = now.weekday()
                days_to_target = day_num - current_weekday - 7
                target = now + timedelta(days=days_to_target)
                print(f"✅ 匹配上周{day_name}: {days_to_target}天")
                return target.strftime("%Y-%m-%d")
    
    if "下周" in description:
        for day_name, day_num in weekday_map.items():
            if day_name in description:
                current_weekday = now.weekday()
                days_to_target = day_num - current_weekday + 7
                target = now + timedelta(days=days_to_target)
                print(f"✅ 匹配下周{day_name}: {days_to_target}天")
                return target.strftime("%Y-%m-%d")
    
    # 处理"N天前"、"N天后"（支持阿拉伯数字和中文数字）
    import re
    
    # 中文数字映射
    chinese_num_map = {
        '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
    }
    
    # ⭐ 新增：处理"前第N天"、"后第N天"
    match = re.match(r"前第([一二三四五六七八九十\d]+)天", description)
    if match:
        num_str = match.group(1)
        # 判断是中文还是阿拉伯数字
        if num_str.isdigit():
            days = int(num_str)
        else:
            days = chinese_num_map.get(num_str, 0)
        if days > 0:
            target = now - timedelta(days=days)
            print(f"✅ 匹配前第{num_str}天: -{days}天")
            return target.strftime("%Y-%m-%d")
    
    match = re.match(r"后第([一二三四五六七八九十\d]+)天", description)
    if match:
        num_str = match.group(1)
        if num_str.isdigit():
            days = int(num_str)
        else:
            days = chinese_num_map.get(num_str, 0)
        if days > 0:
            target = now + timedelta(days=days)
            print(f"✅ 匹配后第{num_str}天: +{days}天")
            return target.strftime("%Y-%m-%d")
    
    # 尝试匹配阿拉伯数字
    match = re.match(r"(\d+)天前", description)
    if match:
        days = int(match.group(1))
        target = now - timedelta(days=days)
        print(f"✅ 匹配阿拉伯数字: {days}天前")
        return target.strftime("%Y-%m-%d")
    
    match = re.match(r"(\d+)天后", description)
    if match:
        days = int(match.group(1))
        target = now + timedelta(days=days)
        print(f"✅ 匹配阿拉伯数字: {days}天后")
        return target.strftime("%Y-%m-%d")
    
    # 尝试匹配中文数字
    match = re.match(r"([一二三四五六七八九十]+)天前", description)
    if match:
        chinese_num = match.group(1)
        days = chinese_num_map.get(chinese_num, 0)
        if days > 0:
            target = now - timedelta(days=days)
            print(f"✅ 匹配中文数字: {chinese_num}天前 = {days}天")
            return target.strftime("%Y-%m-%d")
    
    match = re.match(r"([一二三四五六七八九十]+)天后", description)
    if match:
        chinese_num = match.group(1)
        days = chinese_num_map.get(chinese_num, 0)
        if days > 0:
            target = now + timedelta(days=days)
            print(f"✅ 匹配中文数字: {chinese_num}天后 = {days}天")
            return target.strftime("%Y-%m-%d")
    
    # 处理"X月X日"（假设是今年）
    match = re.match(r"(\d{1,2})月(\d{1,2})日", description)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        try:
            target = now.replace(month=month, day=day)
            print(f"✅ 匹配日期: {month}月{day}日")
            return target.strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    # 无法解析，返回今天
    print(f"⚠️ 无法解析日期描述: '{description}'，默认为今天")
    return now.strftime("%Y-%m-%d")


def is_date_in_range(date_str: str, days: int = 7) -> bool:
    """
    检查日期是否在允许范围内（前后N天）
    
    Args:
        date_str: 日期字符串（YYYY-MM-DD）
        days: 允许的天数范围
        
    Returns:
        是否在范围内
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        now = datetime.now()
        
        # 计算天数差
        diff_days = (target_date.date() - now.date()).days
        
        # 检查是否在 [-days, +days] 范围内
        return -days <= diff_days <= days
        
    except Exception as e:
        print(f"⚠️ 日期范围校验失败: {e}")
        return False

# ==================== 初始化动作注册表 ====================

def init_action_executor():
    """初始化动作执行器，注册所有可用动作"""

    # 任务管理类动作
    executor.register_action(
        "add_task",
        action_add_task,
        {
            "description": "添加新任务并自动排程",
            "parameters": {
                "title": "任务标题（必填）",
                "user_id": "用户ID（必填）",
                "duration": "时长（分钟，默认60）",
                "deadline": "截止时间（ISO格式）",
                "priority": "优先级：high/medium/low（默认medium）",
                "description": "任务描述",
                "start_time": "开始时间（ISO格式，可选）",
                "end_time": "结束时间（ISO格式，可选）"
            }
        }
    )

    executor.register_action(
        "modify_task",
        action_modify_task,
        {
            "description": "修改已有任务",
            "parameters": {
                "task_id": "任务ID（必填）",
                "user_id": "用户ID（必填）",
                "title": "新标题",
                "start_time": "新开始时间",
                "end_time": "新结束时间",
                "duration": "新时长",
                "priority": "新优先级",
                "status": "新状态",
                "deadline": "新截止时间"
            }
        }
    )

    executor.register_action(
        "delete_task",
        action_delete_task,
        {
            "description": "删除任务",
            "parameters": {
                "task_id": "任务ID（必填）",
                "user_id": "用户ID（必填）"
            }
        }
    )

    # 查询类动作
    executor.register_action(
        "query_free_time",
        action_query_free_time,
        {
            "description": "查询空闲时间",
            "parameters": {
                "user_id": "用户ID（必填）",
                "time_range": "时间范围：today/tomorrow/day_after_tomorrow/this_weekend（默认tomorrow）",
                "activity": "活动类型：rest/exercise/movie（默认rest）"
            }
        }
    )

    executor.register_action(
        "analyze_workload",
        action_analyze_workload,
        {
            "description": "分析工作负载密度",
            "parameters": {
                "user_id": "用户ID（必填）",
                "time_range": "时间范围：today/tomorrow/this_week/next_7_days（默认this_week）"
            }
        }
    )

    executor.register_action(
        "query_today_tasks",
        action_query_today_tasks,
        {
            "description": "查询指定日期的任务列表",
            "parameters": {
                "user_id": "用户ID（必填）",
                "date": "日期（YYYY-MM-DD格式，默认今天）"
            }
        }
    )

    # 报告类动作 - ⭐ 已迁移到异步任务队列（generate_weekly_report）
    # 不再需要注册，chat_router 会直接调用 task_queue.enqueue("generate_report", ...)
    # executor.register_action(
    #     "generate_report",
    #     action_generate_report,
    #     {
    #         "description": "生成工作报告",
    #         "parameters": {
    #             "user_id": "用户ID（必填）",
    #             "time_range": "时间范围：this_week/last_week/this_month/last_7_days（默认this_week）"
    #         }
    #     }
    # )

    print(f"✅ 动作执行器初始化完成，共注册 {len(executor.get_available_actions())} 个动作")
    return executor

# 自动初始化
init_action_executor()
