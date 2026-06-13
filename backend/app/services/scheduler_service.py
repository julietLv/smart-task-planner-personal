"""排程服务 - 约束规划算法（python-constraint）"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from constraint import Problem, AllDifferentConstraint
import math


def parse_time(time_str: str) -> datetime:
    """解析时间字符串为datetime对象"""
    if not time_str:
        return None
    try:
        return datetime.fromisoformat(time_str)
    except (ValueError, TypeError):
        return None


def format_time(dt: datetime) -> str:
    """格式化datetime对象为ISO字符串"""
    if not dt:
        return None
    return dt.isoformat()


def get_blocked_periods(preferences: Dict) -> List[Tuple[str, str]]:
    """获取用户的免安排时段"""
    blocked_start = preferences.get("blocked_time_start", "22:00")
    blocked_end = preferences.get("blocked_time_end", "08:00")
    return [(blocked_start, blocked_end)]


def is_in_blocked_period(start_dt: datetime, end_dt: datetime,
                         blocked_periods: List[Tuple[str, str]]) -> bool:
    """检查时间段是否在免安排时段内"""
    for blocked_start_str, blocked_end_str in blocked_periods:
        blocked_start_time = datetime.strptime(blocked_start_str, "%H:%M").time()
        blocked_end_time = datetime.strptime(blocked_end_str, "%H:%M").time()

        current_date = start_dt.date()
        end_date = end_dt.date()

        while current_date <= end_date:
            blocked_start_dt = datetime.combine(current_date, blocked_start_time)

            if blocked_end_time <= blocked_start_time:
                blocked_end_dt = datetime.combine(current_date + timedelta(days=1), blocked_end_time)
            else:
                blocked_end_dt = datetime.combine(current_date, blocked_end_time)

            if start_dt < blocked_end_dt and end_dt > blocked_start_dt:
                return True

            current_date += timedelta(days=1)

    return False


def check_overlap(task1_start: datetime, task1_end: datetime,
                  task2_start: datetime, task2_end: datetime,
                  buffer_minutes: int = 0) -> bool:
    """
    检查两个时间段是否重叠（支持缓冲时间）
    
    Args:
        task1_start: 任务1开始时间
        task1_end: 任务1结束时间
        task2_start: 任务2开始时间
        task2_end: 任务2结束时间
        buffer_minutes: 缓冲时间（分钟），防止任务紧挨着
    
    Returns:
        是否重叠
    """
    # 如果有缓冲时间，在task1结束后增加缓冲期
    if buffer_minutes > 0:
        task1_end_with_buffer = task1_end + timedelta(minutes=buffer_minutes)
        return task1_start < task2_end and task2_start < task1_end_with_buffer
    else:
        return task1_start < task2_end and task2_start < task1_end


def detect_conflict(new_task: Dict, existing_tasks: List[Dict],
                    preferences: Dict = None) -> Dict:
    """
    检测新任务时间与已有任务是否冲突（⭐ 新增缓冲时间支持）

    Args:
        new_task: 新任务信息
        existing_tasks: 已有任务列表
        preferences: 用户偏好设置

    Returns:
        冲突信息字典
    """
    conflicts = []

    if new_task.get("start_time") and new_task.get("end_time"):
        new_start = parse_time(new_task["start_time"])
        new_end = parse_time(new_task["end_time"])

        if not new_start or not new_end:
            return {
                "has_conflict": True,
                "conflicts": [{"type": "invalid_time", "message": "时间格式错误"}]
            }
    else:
        return {
            "has_conflict": False,
            "conflicts": [],
            "message": "未指定具体时间，无法检测冲突"
        }

    # ⭐ 获取缓冲时间配置（默认15分钟）
    buffer_minutes = preferences.get("task_buffer_minutes", 15) if preferences else 15

    for task in existing_tasks:
        if task.get("status") == "cancelled":
            continue

        task_start = parse_time(task.get("start_time"))
        task_end = parse_time(task.get("end_time"))

        if task_start and task_end:
            # ⭐ 使用带缓冲时间的冲突检测
            if check_overlap(new_start, new_end, task_start, task_end, buffer_minutes):
                conflict_msg = f"与任务「{task.get('title')}」时间冲突"
                if buffer_minutes > 0:
                    conflict_msg += f"（考虑{buffer_minutes}分钟缓冲时间）"
                
                conflicts.append({
                    "type": "time_overlap",
                    "conflicting_task_id": task.get("id"),
                    "conflicting_task_title": task.get("title"),
                    "conflicting_time": {
                        "start": task.get("start_time"),
                        "end": task.get("end_time")
                    },
                    "buffer_minutes": buffer_minutes,
                    "message": conflict_msg
                })

    if preferences:
        blocked_periods = get_blocked_periods(preferences)
        if is_in_blocked_period(new_start, new_end, blocked_periods):
            conflicts.append({
                "type": "blocked_period",
                "message": f"在免安排时段内（{preferences.get('blocked_time_start', '22:00')}-{preferences.get('blocked_time_end', '08:00')}）"
            })

    if new_task.get("deadline"):
        deadline = parse_time(new_task["deadline"])
        if deadline and new_end > deadline:
            conflicts.append({
                "type": "exceeds_deadline",
                "message": f"任务结束时间超过截止时间 {new_task['deadline']}"
            })

    return {
        "has_conflict": len(conflicts) > 0,
        "conflicts": conflicts,
        "buffer_minutes": buffer_minutes  # ⭐ 返回缓冲时间信息
    }


def generate_time_slots(search_start: datetime, search_end: datetime,
                        step_minutes: int = 30) -> List[datetime]:
    """
    生成候选时间槽列表

    Args:
        search_start: 搜索起始时间
        search_end: 搜索结束时间
        step_minutes: 时间槽间隔（分钟）

    Returns:
        时间槽列表
    """
    slots = []
    current = search_start
    step = timedelta(minutes=step_minutes)

    while current < search_end:
        slots.append(current)
        current += step

    return slots


def is_slot_valid(slot_start: datetime, slot_end: datetime,
                  existing_tasks: List[Dict],
                  blocked_periods: List[Tuple[str, str]],
                  buffer_minutes: int = 15) -> bool:
    """
    检查时间槽是否可用（⭐ 新增缓冲时间支持）

    Args:
        slot_start: 时间槽开始时间
        slot_end: 时间槽结束时间
        existing_tasks: 已有任务列表
        blocked_periods: 免安排时段列表
        buffer_minutes: 缓冲时间（分钟）

    Returns:
        是否可用
    """
    # 检查免安排时段
    if is_in_blocked_period(slot_start, slot_end, blocked_periods):
        return False

    # 检查与现有任务的冲突（⭐ 使用缓冲时间）
    for task in existing_tasks:
        if task.get("status") == "cancelled":
            continue

        task_start = parse_time(task.get("start_time"))
        task_end = parse_time(task.get("end_time"))

        if task_start and task_end:
            if check_overlap(slot_start, slot_end, task_start, task_end, buffer_minutes):
                return False

    return True


def _is_slot_conflict_free(slot_tuple, existing_tasks, buffer_minutes):
    """P1: 检查时间槽是否无冲突（辅助拆分建议）"""
    start_dt, end_dt = slot_tuple
    blocked_periods = get_blocked_periods({})
    return is_slot_valid(start_dt, end_dt, existing_tasks, blocked_periods, buffer_minutes)


def _generate_split_suggestions_from_valid_slots(valid_slots_objects, total_duration, existing_tasks, preferences, buffer_minutes):
    """
    P1: 从有效时间槽生成拆分建议
    
    当无法找到连续时间段时，尝试将任务拆分成多个小段
    """
    if not valid_slots_objects:
        return []
    
    # 尝试将任务拆分成2-3段
    split_options = [
        total_duration // 2,  # 分成2段
        total_duration // 3,  # 分成3段
    ]
    
    for segment_duration in split_options:
        if segment_duration < 15:  # 每段至少15分钟
            continue
        
        segments = []
        remaining_duration = total_duration
        last_end_time = None
        
        for slot in valid_slots_objects:
            if remaining_duration <= 0:
                break
            
            start_dt, end_dt = slot
            slot_duration = int((end_dt - start_dt).total_seconds() / 60)
            
            # 取可用时长和所需时长的最小值
            use_duration = min(segment_duration, remaining_duration, slot_duration)
            use_end = start_dt + timedelta(minutes=use_duration)
            
            # 检查是否有效
            if _is_slot_conflict_free((start_dt, use_end), existing_tasks, buffer_minutes):
                # 检查与前一段的时间间隔（至少30分钟）
                if last_end_time and (start_dt - last_end_time).total_seconds() < 1800:
                    continue
                
                # 生成原因
                hour = start_dt.hour + start_dt.minute / 60
                reason = _generate_segment_reason(hour, use_duration)
                
                segments.append({
                    "segment": len(segments) + 1,
                    "date": start_dt.date().isoformat(),  # 日期标注
                    "start_time": start_dt.isoformat(),
                    "end_time": use_end.isoformat(),
                    "duration": use_duration,
                    "reason": reason
                })
                
                last_end_time = use_end
                remaining_duration -= use_duration
        
        # 如果成功拆分且覆盖大部分时长
        if segments and remaining_duration <= segment_duration:
            return segments
    
    # 无法拆分，返回空列表
    return []


def _generate_segment_reason(hour, duration):
    """P1: 生成时间段原因"""
    if 9 <= hour <= 11.5:
        return "上午高效时段"
    elif 14 <= hour <= 16:
        return "下午黄金时段"
    elif 16 <= hour <= 18.5:
        return "傍晚时段"
    elif 7 <= hour <= 9:
        return "早晨时段"
    else:
        return "可用时段"


def schedule_task_cp(new_task: Dict, existing_tasks: List[Dict],
                     preferences: Dict = None, current_date: datetime = None) -> Dict:
    """
    【约束规划算法】使用 python-constraint 库进行智能排程
    
    Args:
        current_date: 统一参考时间，避免多处datetime.now()跨天漂移

    算法思路：
    1. 定义决策变量：任务的开始时间（从候选时间槽中选择）
    2. 定义约束条件：
       - 不与现有任务时间重叠
       - 不在免安排时段内
       - 不超过截止时间
       - 满足任务时长要求
    3. 定义目标函数（软约束）：
       - 优先级高的任务尽量早安排
       - 尽量靠近用户偏好的工作时间
    4. 使用回溯搜索找到最优解

    优势：
    - 全局最优：不是贪心地找第一个可用时间，而是综合所有约束找到最优解
    - 灵活扩展：可以轻松添加新约束（如会议必须在上午、运动必须在下午等）
    - 多任务协同：可以同时优化多个任务的排程

    Args:
        new_task: 新任务信息，包含 title, duration, deadline, priority等
        existing_tasks: 已有任务列表
        preferences: 用户偏好设置

    Returns:
        排程结果，包含建议的 start_time 和 end_time
    """
    if preferences is None:
        preferences = {}

    # ⭐ 新增：应用上下文感知调整
    user_id = new_task.get("user_id", 1)
    if user_id:
        try:
            from app.services.context_aware_scheduler import apply_context_to_scheduling
            new_task = apply_context_to_scheduling(new_task, user_id)

            # 如果上下文提供了缓冲时间，更新preferences
            if "buffer_minutes" in new_task:
                preferences["task_buffer_minutes"] = new_task["buffer_minutes"]
                print(f"🧠 使用上下文感知的缓冲时间: {new_task['buffer_minutes']}分钟")
        except Exception as e:
            print(f"⚠️ 应用上下文感知失败: {e}，使用默认配置")

    # ==================== 1. 提取任务信息 ====================
    title = new_task.get("title", "未命名任务")
    duration_minutes = new_task.get("duration")
    deadline_str = new_task.get("deadline")
    priority = new_task.get("priority", "medium")

    # 验证必要参数
    if not duration_minutes:
        return {
            "success": False,
            "message": "缺少任务时长信息",
            "suggestion": "请提供任务的预估时长（分钟）",
            "algorithm": "constraint_programming"
        }

    # ==================== 2. 确定搜索范围 ====================
    now = current_date if current_date else datetime.now()

    # 搜索起点：如果是工作时间（9-18点），从现在开始；否则从明天9点开始
    if 9 <= now.hour < 18:
        search_start = now.replace(minute=0, second=0, microsecond=0)
    else:
        tomorrow = now + timedelta(days=1)
        search_start = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)

    # 搜索终点：有截止时间则用截止时间，否则搜索可配置天数（默认3天）
    if deadline_str:
        deadline = parse_time(deadline_str)
        if not deadline:
            return {
                "success": False,
                "message": "截止时间格式错误",
                "suggestion": "请使用ISO格式，如：2026-04-20T18:00:00",
                "algorithm": "constraint_programming"
            }
        search_end = deadline - timedelta(minutes=duration_minutes)

        if search_end < search_start:
            return {
                "success": False,
                "message": "剩余时间不足以完成任务",
                "remaining_minutes": max(0, int((deadline - now).total_seconds() / 60)),
                "required_minutes": duration_minutes,
                "suggestion": f"需要{duration_minutes}分钟，但距离截止时间仅剩{max(0, int((deadline - now).total_seconds() / 60))}分钟",
                "algorithm": "constraint_programming"
            }
    else:
        # 智能默认截止引导：当天18:00，若已过则明天18:00（仅缩小搜索范围，不写入DB）
        # P2: 搜索范围可配置化，默认3天
        search_horizon = preferences.get('scheduling_horizon', 3)
        today_1800 = now.replace(hour=18, minute=0, second=0, microsecond=0)
        if now < today_1800:
            default_deadline = today_1800
        else:
            default_deadline = today_1800 + timedelta(days=search_horizon)  # P2: 使用可配置的天数
        search_end = default_deadline - timedelta(minutes=duration_minutes)
        deadline = default_deadline

    # ==================== 3. 生成候选时间槽 ====================
    time_slots = generate_time_slots(search_start, search_end, step_minutes=30)

    print(f"\n🔍 开始约束规划排程...")
    print(f"   任务: {title}")
    print(f"   时长: {duration_minutes}分钟")
    print(f"   优先级: {priority}")
    print(f"   搜索范围: {search_start.strftime('%m-%d %H:%M')} ~ {search_end.strftime('%m-%d %H:%M')}")
    print(f"   候选时间槽数量: {len(time_slots)}")

    # ==================== 4. 过滤有效时间槽 ====================
    blocked_periods = get_blocked_periods(preferences)
    active_tasks = [t for t in existing_tasks if t.get("status") != "cancelled"]

    # ⭐ 获取用户配置的缓冲时间
    buffer_minutes = preferences.get("task_buffer_minutes", 15) if preferences else 15

    valid_slots = []
    valid_slots_objects = []  # P1: 同时保存完整的(start, end)元组
    for slot_start in time_slots:
        slot_end = slot_start + timedelta(minutes=duration_minutes)

        if slot_end > search_end:
            break

        if is_slot_valid(slot_start, slot_end, active_tasks, blocked_periods, buffer_minutes):
            valid_slots.append(slot_start)
            valid_slots_objects.append((slot_start, slot_end))  # P1: 保存完整元组

    print(f"   有效时间槽数量: {len(valid_slots)} (缓冲时间: {buffer_minutes}分钟)")

    if not valid_slots:
        # P1: 增加尽力而为回退策略（拆分任务建议）
        split_suggestions = _generate_split_suggestions_from_valid_slots(
            valid_slots_objects, duration_minutes, existing_tasks, preferences, buffer_minutes
        )
        
        return {
            "success": False,
            "message": "无法找到合适的时间段",
            "reason": "所有可用时间段都与已有任务冲突或在免安排时段内",
            "can_complete_continuously": False,  # P0新增：无法连续完成
            "split_suggestions": split_suggestions,  # P1新增：拆分建议
            "suggestions": [
                "尝试调整任务的截止时间",
                "减少任务时长",
                "修改免安排时段设置",
                "取消或重新安排一些已有任务",
                "今日空闲时段较碎片化，建议拆分任务或调整时长"
            ],
            "algorithm": "constraint_programming"
        }

    # ==================== 5. 使用约束规划求解 ====================
    problem = Problem()

    # 定义决策变量：任务的开始时间（从有效时间槽中选择）
    problem.addVariable("start_time", valid_slots)

    # 定义约束：结束时间不能超过截止时间
    def deadline_constraint(start):
        end = start + timedelta(minutes=duration_minutes)
        return end <= deadline

    problem.addConstraint(deadline_constraint, ["start_time"])

    # 获取所有可行解
    solutions = problem.getSolutions()

    if not solutions:
        return {
            "success": False,
            "message": "约束冲突，无可行解",
            "reason": "任务约束条件过于严格，无法满足所有要求",
            "can_complete_continuously": False,  # P0新增：无法连续完成
            "suggestions": [
                "放宽截止时间",
                "减少任务时长",
                "调整免安排时段",
                "降低优先级要求",
                "今日空闲时段较碎片化，建议拆分任务或调整时长"
            ],
            "algorithm": "constraint_programming"
        }

    # ==================== 6. 评估并选择最优解 ====================
    def score_solution(solution):
        """评估解的质量（分数越高越好）"""
        start = solution["start_time"]
        end = start + timedelta(minutes=duration_minutes)
        score = 0

        # 因素1：优先级越高，越早安排得分越高
        priority_weights = {"high": 3, "medium": 2, "low": 1}
        priority_weight = priority_weights.get(priority, 2)

        # 时间越早得分越高（相对搜索起点）
        time_from_start = (start - search_start).total_seconds() / 3600  # 小时
        max_time_range = (search_end - search_start).total_seconds() / 3600
        earliness_score = (1 - time_from_start / max_time_range) * priority_weight * 100
        score += earliness_score

        # 因素2：尽量安排在工作时间中心（14:00左右）
        hour_of_day = start.hour + start.minute / 60
        work_center = 14  # 下午2点
        distance_from_center = abs(hour_of_day - work_center)
        work_time_score = max(0, (6 - distance_from_center)) * 5
        score += work_time_score

        # 因素3：避免太晚安排（18:00后扣分）
        if start.hour >= 18:
            lateness_penalty = (start.hour - 18) * 20
            score -= lateness_penalty

        # 因素4：避免太早安排（9:00前扣分）
        if start.hour < 9:
            earliness_penalty = (9 - start.hour) * 20
            score -= earliness_penalty

        return score

    # 对所有解评分并排序
    scored_solutions = [(sol, score_solution(sol)) for sol in solutions]
    scored_solutions.sort(key=lambda x: x[1], reverse=True)

    # 选择最优解
    best_solution = scored_solutions[0][0]
    best_score = scored_solutions[0][1]

    best_start = best_solution["start_time"]
    best_end = best_start + timedelta(minutes=duration_minutes)

    print(f"   ✅ 找到最优解: {best_start.strftime('%m-%d %H:%M')} - {best_end.strftime('%H:%M')}")
    print(f"   评分: {best_score:.2f}")
    print(f"   可行解总数: {len(solutions)}")

    # ==================== 7. 生成备选方案 ====================
    alternative_slots = []
    for i in range(1, min(4, len(scored_solutions))):
        alt_sol = scored_solutions[i][0]
        alt_start = alt_sol["start_time"]
        alt_end = alt_start + timedelta(minutes=duration_minutes)

        alternative_slots.append({
            "start_time": format_time(alt_start),
            "end_time": format_time(alt_end),
            "score": scored_solutions[i][1]
        })

    # ==================== 8. 返回结果 ====================
    result = {
        "success": True,
        "algorithm": "constraint_programming",
        "scheduled_time": {
            "start_time": format_time(best_start),
            "end_time": format_time(best_end)
        },
        "alternative_slots": alternative_slots,
        "can_complete_continuously": True,  # P0新增：可以连续完成
        "message": f"已为任务「{title}」找到最优时间（评分: {best_score:.2f}）",
        "task_info": {
            "title": title,
            "duration_minutes": duration_minutes,
            "priority": priority,
            "deadline": deadline_str
        },
        "search_stats": {
            "total_slots": len(time_slots),
            "valid_slots": len(valid_slots),
            "feasible_solutions": len(solutions),
            "best_score": best_score
        }
    }

    return result


# 保持向后兼容，让 schedule_task 指向约束规划算法
schedule_task = schedule_task_cp


def schedule_multiple_tasks_cp(tasks: List[Dict], existing_tasks: List[Dict],
                               preferences: Dict = None) -> List[Dict]:
    """
    【约束规划算法】同时优化多个任务的排程

    这是约束规划的核心优势：可以同时为多个任务寻找最优时间安排，
    确保它们之间不冲突，并且整体排程质量最高。

    Args:
        tasks: 待排程的任务列表
        existing_tasks: 已有任务列表（已固定的任务）
        preferences: 用户偏好设置

    Returns:
        优化后的任务列表
    """
    if preferences is None:
        preferences = {}

    if not tasks:
        return []

    # ==================== 1. 准备工作 ====================
    now = datetime.now()
    search_start = now.replace(minute=0, second=0, microsecond=0)
    search_end = now + timedelta(days=7)
    blocked_periods = get_blocked_periods(preferences)
    active_existing_tasks = [t for t in existing_tasks if t.get("status") != "cancelled"]

    # 按优先级排序任务（高优先级先安排）
    priority_order = {"high": 0, "medium": 1, "low": 2}
    sorted_tasks = sorted(
        tasks,
        key=lambda t: (
            priority_order.get(t.get("priority", "medium"), 1),
            t.get("deadline", "9999-12-31")
        )
    )

    print(f"\n🔍 开始多任务约束规划排程...")
    print(f"   待排程任务数: {len(sorted_tasks)}")

    # ==================== 2. 为每个任务生成候选时间槽 ====================
    task_domains = {}
    task_duration_map = {}
    
    # ⭐ 获取用户配置的缓冲时间
    buffer_minutes = preferences.get("task_buffer_minutes", 15) if preferences else 15

    for idx, task in enumerate(sorted_tasks):
        task_id = f"task_{idx}"
        duration = task.get("duration", 60)
        deadline_str = task.get("deadline")

        task_duration_map[task_id] = duration

        # 确定搜索范围
        task_start = search_start
        if deadline_str:
            deadline = parse_time(deadline_str)
            if deadline:
                task_end = deadline - timedelta(minutes=duration)
            else:
                task_end = search_end
        else:
            task_end = search_end

        # 生成时间槽
        slots = generate_time_slots(task_start, task_end, step_minutes=30)

        # 过滤有效时间槽
        valid_slots = []
        for slot_start in slots:
            slot_end = slot_start + timedelta(minutes=duration)

            if slot_end > task_end:
                break

            if is_slot_valid(slot_start, slot_end, active_existing_tasks, blocked_periods, buffer_minutes):
                valid_slots.append(slot_start)

        task_domains[task_id] = valid_slots
        print(f"   任务 {idx+1}「{task.get('title', '未命名')}」: {len(valid_slots)} 个有效时间槽 (缓冲: {buffer_minutes}分钟)")

    # ==================== 3. 构建约束规划问题 ====================
    problem = Problem()

    # 添加变量
    for task_id, domain in task_domains.items():
        if not domain:
            return [{
                **sorted_tasks[idx],
                "scheduling_status": "failed",
                "failure_reason": "没有可用的时间槽",
                "algorithm": "constraint_programming"
            } for idx in range(len(sorted_tasks))]

        problem.addVariable(task_id, domain)

    # 添加约束：任意两个任务不能时间重叠
    for i in range(len(sorted_tasks)):
        for j in range(i + 1, len(sorted_tasks)):
            task_i_id = f"task_{i}"
            task_j_id = f"task_{j}"
            duration_i = task_duration_map[task_i_id]
            duration_j = task_duration_map[task_j_id]

            def no_overlap(start_i, start_j, dur_i=duration_i, dur_j=duration_j):
                end_i = start_i + timedelta(minutes=dur_i)
                end_j = start_j + timedelta(minutes=dur_j)
                return not (start_i < end_j and start_j < end_i)

            problem.addConstraint(no_overlap, [task_i_id, task_j_id])

    # ==================== 4. 求解 ====================
    print(f"   正在求解约束问题...")
    solutions = problem.getSolutions()

    if not solutions:
        print(f"   ❌ 无可行解")
        return [{
            **task,
            "scheduling_status": "failed",
            "failure_reason": "无法找到满足所有约束的时间安排",
            "suggestions": [
                "尝试调整某些任务的截止时间",
                "减少任务时长",
                "修改免安排时段设置"
            ],
            "algorithm": "constraint_programming"
        } for task in sorted_tasks]

    print(f"   ✅ 找到 {len(solutions)} 个可行解")

    # ==================== 5. 评估并选择最优解 ====================
    def score_multi_task_solution(solution):
        """评估多任务解的质量"""
        score = 0
        work_center = 14  # 下午2点

        for idx, task in enumerate(sorted_tasks):
            task_id = f"task_{idx}"
            start = solution[task_id]
            duration = task_duration_map[task_id]
            end = start + timedelta(minutes=duration)

            # 因素1：越早安排越好
            time_from_start = (start - search_start).total_seconds() / 3600
            max_time_range = (search_end - search_start).total_seconds() / 3600
            earliness_score = (1 - time_from_start / max_time_range) * 50
            score += earliness_score

            # 因素2：靠近工作时间中心
            hour_of_day = start.hour + start.minute / 60
            distance_from_center = abs(hour_of_day - work_center)
            work_time_score = max(0, (6 - distance_from_center)) * 3
            score += work_time_score

            # 因素3：高优先级任务获得额外加分
            priority_weights = {"high": 2, "medium": 1, "low": 0.5}
            priority_bonus = priority_weights.get(task.get("priority", "medium"), 1) * 20
            score += priority_bonus

        return score

    # 评分并排序
    scored_solutions = [(sol, score_multi_task_solution(sol)) for sol in solutions]
    scored_solutions.sort(key=lambda x: x[1], reverse=True)

    best_solution = scored_solutions[0][0]
    best_score = scored_solutions[0][1]

    print(f"   最优解评分: {best_score:.2f}")

    # ==================== 6. 构建返回结果 ====================
    scheduled_tasks = []
    for idx, task in enumerate(sorted_tasks):
        task_id = f"task_{idx}"
        start = best_solution[task_id]
        duration = task_duration_map[task_id]
        end = start + timedelta(minutes=duration)

        scheduled_task = task.copy()
        scheduled_task["start_time"] = format_time(start)
        scheduled_task["end_time"] = format_time(end)
        scheduled_task["scheduling_status"] = "scheduled"
        scheduled_task["algorithm"] = "constraint_programming"
        scheduled_tasks.append(scheduled_task)

    return scheduled_tasks


def optimize_schedule(tasks: List[Dict], preferences: Dict = None) -> List[Dict]:
    """
    优化多个任务的排程（约束规划版本）

    Args:
        tasks: 待排程的任务列表
        preferences: 用户偏好设置

    Returns:
        优化后的任务列表
    """
    if preferences is None:
        preferences = {}

    return schedule_multiple_tasks_cp(tasks, [], preferences)


# 在 scheduler_service.py 末尾添加定时任务相关代码

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import json

# 全局调度器实例
scheduler = BackgroundScheduler()


def check_deadline_reminders(user_id: int = 1, hours_before: int = 6) -> None:
    """
    检查任务到期提醒，自动标记超时任务
    
    超时判定逻辑：
    1. 优先检查 deadline 字段（如果有）
    2. 如果没有 deadline，则检查 end_time 字段
    3. 两个时间都没有的任务不会被标记超时
    """
    from app.models.task_model import get_all_tasks, update_task
    from app.services.cache_service import redis_cache

    try:
        print(f" [{datetime.now()}] 检查任务到期提醒...")

        all_tasks = get_all_tasks()
        now = datetime.now()
        overdue_count = 0
        affected_user_ids = set()

        for task in all_tasks:
            # 跳过已完成、已取消或已超时的任务
            if task.status in ["done", "cancelled", "overdue"]:
                continue
            
            # 确定检查的时间字段（优先deadline，其次end_time）
            check_time = None
            time_type = ""
            
            if task.deadline:
                check_time = task.deadline
                time_type = "截止时间"
            elif task.end_time:
                check_time = task.end_time
                time_type = "结束时间"
            
            # 如果两个时间都没有，跳过
            if not check_time:
                continue
            
            deadline_dt = parse_time(check_time)
            if not deadline_dt:
                continue
            
            # 如果已过期，自动标记为 overdue
            if deadline_dt < now:
                update_task(task.id, task.user_id, status="overdue")
                overdue_count += 1
                affected_user_ids.add(task.user_id)
                print(f"⚠️  任务已超时: {task.title} ({time_type}: {check_time})")
            
            # 如果即将到期（24小时内），发送提醒
            elif (deadline_dt - now).total_seconds() <= 24 * 3600:
                hours_left = (deadline_dt - now).total_seconds() / 3600
                print(f" 任务即将到期: {task.title} (剩余 {hours_left:.1f} 小时)")

        detect_recurring_conflicts()

        # ✅ 修复：清除受影响用户的任务缓存，确保前端获取最新状态
        if overdue_count > 0:
            print(f"✅ 本次共标记 {overdue_count} 个任务为超时状态")
            for affected_user_id in affected_user_ids:
                redis_cache.clear_pattern(f"tasks:{affected_user_id}:*")
                print(f"✅ 已清除用户 {affected_user_id} 的任务缓存")

    except Exception as e:
        print(f"检查到期提醒失败: {e}")


def detect_recurring_conflicts():
    """
    检测是否有任务频繁冲突
    """
    from app.models.task_model import get_all_tasks

    try:
        all_tasks = get_all_tasks()

        task_patterns = {}

        for task in all_tasks:
            if task.status == "cancelled":
                continue

            pattern = task.title[:4]

            if pattern not in task_patterns:
                task_patterns[pattern] = []

            task_patterns[pattern].append(task)

        for pattern, tasks in task_patterns.items():
            if len(tasks) >= 3:
                conflict_count = 0
                for i in range(len(tasks)):
                    for j in range(i + 1, len(tasks)):
                        if tasks[i].start_time and tasks[j].start_time:
                            start1 = parse_time(tasks[i].start_time)
                            end1 = parse_time(tasks[i].end_time)
                            start2 = parse_time(tasks[j].start_time)
                            end2 = parse_time(tasks[j].end_time)

                            if start1 and end1 and start2 and end2:
                                if check_overlap(start1, end1, start2, end2):
                                    conflict_count += 1

                if conflict_count >= 2:
                    print(f"💡 检测到任务 '{pattern}*' 频繁冲突，建议设为重复任务")

    except Exception as e:
        print(f"检测重复冲突失败: {e}")


def generate_daily_summary():
    """
    每天早上8点生成日程摘要并通过 WebSocket 推送
    """
    import asyncio
    from app.models.task_model import get_all_tasks, get_tasks_by_deadline
    from app.services.notification_service import generate_daily_summary as gen_summary
    from app.services.websocket_service import push_daily_summary

    try:
        print(f"📅 [{datetime.now()}] 生成每日日程摘要...")

        # 生成摘要
        summary = gen_summary(user_id=1)

        if summary.get('success'):
            print(summary['summary'])

            # ✅ 新增：记录生成时间和内容日期
            print(f"✅ 摘要生成成功，日期: {summary.get('date')}")

            # 通过 WebSocket 推送（异步）
            try:
                asyncio.get_event_loop().create_task(
                    push_daily_summary(summary, user_id=1)
                )
            except Exception as ws_error:
                print(f"⚠️ WebSocket 推送失败: {ws_error}")
        else:
            print(f"️ 生成摘要失败: {summary.get('message')}")

    except Exception as e:
        print(f"生成日程摘要失败: {e}")
        import traceback
        traceback.print_exc()


def delete_old_notifications(days: int = 7):
    """
    清理过期通知（保留最近N天）
    """
    from app.models.notification_model import delete_old_notifications as delete_notifs

    try:
        print(f"🧹 [{datetime.now()}] 开始清理{days}天前的旧通知...")

        deleted_count = delete_notifs(days)

        if deleted_count > 0:
            print(f"✅ 已清理 {deleted_count} 条过期通知")
        else:
            print(f"ℹ️  没有需要清理的通知")

    except Exception as e:
        print(f"❌ 清理通知失败: {e}")
        import traceback
        traceback.print_exc()


# def start_scheduler():
#     """
#     启动定时任务调度器
#     """
#     global scheduler
#
#     if scheduler.running:
#         print("⚠️  调度器已在运行")
#         return
#
#     scheduler.add_job(
#         check_deadline_reminders,
#         trigger=CronTrigger(hour=0, minute=0),
#         id='check_deadlines',
#         name='每日凌晨检查任务超时',
#         replace_existing=True
#     )
#
#     scheduler.add_job(
#         generate_daily_summary,
#         trigger=CronTrigger(hour=8, minute=0),
#         id='daily_summary',
#         name='每日日程摘要',
#         replace_existing=True
#     )
#
#     scheduler.start()
#     print("✅ 定时任务调度器已启动")
#     print("   - 每天凌晨0点检查任务超时")
#     print("   - 每天早上8点生成日程摘要")
#
#
# def stop_scheduler():
#     """
#     停止定时任务调度器
#     """
#     global scheduler
#
#     if scheduler.running:
#         scheduler.shutdown()
#         print("⏹️  定时任务调度器已停止")


def remember_user_preference(task_title: str, adjustment_type: str, 
                            old_value, new_value, user_id: int = 1,
                            context: dict = None) -> bool:
    """记录用户的调整习惯，用于长期记忆（⭐ 已优化：增加Redis缓存）"""
    try:
        from app.models.task_model import get_user_preferences, update_user_preferences
        from app.services.cache_service import redis_cache
        import json
        
        # 获取当前用户偏好
        preferences = get_user_preferences(user_id)
        if not preferences:
            print(f"⚠️ 用户 {user_id} 偏好不存在，无法记录习惯")
            return False
        
        # 解析已存储的习惯
        habits = preferences.remembered_habits
        if isinstance(habits, str):
            try:
                habits = json.loads(habits)
            except json.JSONDecodeError:
                habits = {}
        
        if not isinstance(habits, dict):
            habits = {}
        
        # 从任务标题提取关键词
        keywords = extract_task_keywords(task_title)
        
        for keyword in keywords:
            # 跳过特殊键
            if keyword.startswith("_"):
                continue
            
            # 初始化关键词记录
            if keyword not in habits:
                habits[keyword] = {
                    "count": 0,
                    "adjustments": [],
                    "learned": False,
                    "confidence": 0.5,
                    "first_seen": datetime.now().isoformat()
                }
            
            habit = habits[keyword]
            habit["count"] += 1
            
            # 记录调整历史
            adjustment_record = {
                "type": adjustment_type,
                "old_value": old_value,
                "new_value": new_value,
                "timestamp": datetime.now().isoformat(),
                "context": context or {}
            }
            
            if "adjustments" not in habit:
                habit["adjustments"] = []
            
            habit["adjustments"].append(adjustment_record)
            
            # 保持最近 50 条记录（避免数据过大）
            if len(habit["adjustments"]) > 50:
                habit["adjustments"] = habit["adjustments"][-50:]
            
            # 检查是否达到学习阈值
            threshold = get_learning_threshold(adjustment_type)
            recent_adjustments = [
                a for a in habit["adjustments"] 
                if a["type"] == adjustment_type
            ]
            
            # ⭐ Phase 1 修复：每个调整类型独立判断是否已学习
            preference_key = f"preferred_{adjustment_type}"
            already_learned_this_type = preference_key in habit
            
            if len(recent_adjustments) >= threshold and not already_learned_this_type:
                # 统计最常见的调整值
                values = [a["new_value"] for a in recent_adjustments]
                value_counts = {}
                for v in values:
                    value_counts[v] = value_counts.get(v, 0) + 1
                
                most_common = max(value_counts, key=value_counts.get)
                confidence = value_counts[most_common] / len(values)
                
                # 只有当置信度超过 60% 才认为学习到
                if confidence >= 0.6:
                    habit[f"preferred_{adjustment_type}"] = most_common
                    # ⭐ Phase 1 修复：不再设置全局 learned 标志，每个偏好独立学习
                    # habit["learned"] = True  # 已移除
                    habit["learned_at"] = datetime.now().isoformat()
                    habit["confidence"] = confidence
                    
                    print(f"✅ 已学习习惯: [{keyword}] 的 {adjustment_type} 偏好为 '{most_common}' (置信度: {confidence:.2f})")
                else:
                    print(f"⚠️ [{keyword}] 的 {adjustment_type} 调整不够一致，继续观察")
            
            # 更新最后使用时间
            habit["last_used"] = datetime.now().isoformat()
        
        # 清理过期习惯
        clean_old_habits(habits)
        
        # 保存到数据库
        update_user_preferences(user_id, remembered_habits=json.dumps(habits, ensure_ascii=False))
        
        # ⭐ 更新Redis缓存（清除旧缓存，下次读取时会重新加载）
        redis_key = f"habits:user:{user_id}"
        redis_cache.delete(redis_key)
        print(f"💾 已更新用户习惯并清除Redis缓存: user_id={user_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ 记录用户习惯失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_learning_threshold(adjustment_type: str) -> int:
    """根据不同调整类型返回学习阈值"""
    thresholds = {
        "priority": 2,
        "duration": 3,
        "time_slot": 4,
        "description_template": 3,
        "default": 3
    }
    return thresholds.get(adjustment_type, thresholds["default"])


def clean_old_habits(habits: dict, max_records: int = 50, expire_days: int = 90):
    """清理过期和冗余的习惯记录（遗忘机制）"""
    now = datetime.now()
    expired_keywords = []
    
    for keyword, data in habits.items():
        adjustments = data.get("adjustments", [])
        
        if len(adjustments) > max_records:
            data["adjustments"] = adjustments[-max_records:]
        
        last_used_str = data.get("last_used")
        if last_used_str:
            try:
                last_used = datetime.fromisoformat(last_used_str)
                days_since_used = (now - last_used).days
                
                if days_since_used > expire_days:
                    if data.get("learned"):
                        data["learned"] = False
                        data["expired_at"] = now.isoformat()
                        print(f"⚠️ 习惯已过期: {keyword} ({days_since_used}天未使用)")
                    expired_keywords.append(keyword)
                
                decay_factor = max(0.5, 1.0 - (days_since_used / 365))
                data["confidence"] = data.get("confidence", 0.5) * decay_factor
                
            except:
                pass
    
    for keyword in expired_keywords:
        if habits[keyword].get("confidence", 0) < 0.2:
            del habits[keyword]
            print(f"🗑️ 已删除过期习惯: {keyword}")


def get_custom_keywords(user_id: int = 1) -> dict:
    """
    获取用户自定义关键词映射
    
    Returns:
        {
            "王者": "娱乐",
            "LeetCode": "学习"
        }
    """
    try:
        from app.models.task_model import get_user_preferences
        import json
        
        preferences = get_user_preferences(user_id)
        if not preferences or not preferences.remembered_habits:
            return {}
        
        habits = preferences.remembered_habits
        if isinstance(habits, str):
            habits = json.loads(habits)
        
        # 返回 _custom_keywords，如果不存在则返回空字典
        return habits.get("_custom_keywords", {})
    except Exception as e:
        print(f"⚠️ 获取自定义关键词失败: {e}")
        return {}


def extract_task_keywords(task_title: str) -> list:
    """从任务标题中提取关键词（增强版：利用已有的学习习惯缓存）"""
    categories = {
        "运动": ["运动", "健身", "跑步", "游泳", "瑜伽", "锻炼", "篮球", "足球", "羽毛球", "乒乓球", "骑行", "爬山"],
        "学习": ["学习", "作业", "复习", "考试", "课程", "读书", "阅读", "论文", "研究", "编程", "代码", "算法", "英语",
                 "单词"],
        "工作": ["工作", "会议", "报告", "项目", "邮件", "文档", "演示", "客户", "需求", "评审", "迭代", "上线",
                 "部署"],
        "生活": ["购物", "做饭", "打扫", "洗衣", "约会", "聚会", "电影", "旅行", "医院", "体检", "理发", "缴费"],
        "创作": ["写作", "设计", "绘画", "音乐", "视频", "剪辑", "摄影", "博客", "内容"],
        "社交": ["聊天", "电话", "拜访", "活动", "社团", "志愿"],
        "健康": ["冥想", "休息", "睡眠", "按摩", "理疗", "复查", "吃药"]
    }

    custom_keywords = get_custom_keywords()

    keywords = []
    title_lower = task_title.lower()

    # ⭐ 第一步：精确匹配分类关键词
    for category, words in categories.items():
        for word in words:
            if word in title_lower:
                keywords.append(category)
                break

    # ⭐ 第二步：匹配自定义关键词
    for custom_word, category in custom_keywords.items():
        if custom_word.lower() in title_lower:
            keywords.append(category)
            break

    # ⭐ 第三步：⭐ 优先从已学习的习惯中匹配（包含语义别名）
    learned_habits = _get_learned_habit_keywords_with_aliases()
    for habit_keyword, aliases in learned_habits.items():
        # 3.1 精确匹配关键词本身
        if habit_keyword in title_lower or title_lower in habit_keyword:
            keywords.append(habit_keyword)
            print(f"🧠 匹配到学习习惯: '{habit_keyword}' (精确匹配)")
            break

        # ⭐ 3.2 匹配语义别名（来自 LLM 或用户行为）
        if any(alias in title_lower for alias in aliases):
            keywords.append(habit_keyword)
            matched_alias = next(alias for alias in aliases if alias in title_lower)
            print(f"🧠 匹配到学习习惯: '{habit_keyword}' (通过别名 '{matched_alias}')")
            break

        # 3.3 模糊匹配
        if _fuzzy_keyword_match(title_lower, habit_keyword):
            keywords.append(habit_keyword)
            print(f"🧠 匹配到学习习惯: '{habit_keyword}' (模糊匹配)")
            break

    # ⭐ 第四步：如果还是没有，提取前2-4个字符作为关键词
    if not keywords:
        words = task_title.replace(" ", "")
        if len(words) >= 2:
            keywords.append(words[:min(4, len(words))])
        else:
            keywords.append("其他")

    return list(set(keywords))


# 在 def _get_learned_habit_keywords_with_aliases(user_id: int = 1) -> dict: 这行之前


def add_custom_keyword(keyword: str, category: str, user_id: int = 1) -> bool:
    """
    添加自定义关键词映射

    Args:
        keyword: 自定义关键词（如 "王者"、"LeetCode"）
        category: 类别（如 "娱乐"、"学习"、"运动"）
        user_id: 用户ID

    Returns:
        是否成功
    """
    try:
        from app.models.task_model import get_user_preferences, update_user_preferences
        import json

        # 获取用户偏好
        preferences = get_user_preferences(user_id)
        if not preferences:
            print(f"⚠️ 用户 {user_id} 偏好不存在")
            return False

        # 解析习惯数据
        habits = preferences.remembered_habits
        if isinstance(habits, str):
            try:
                habits = json.loads(habits)
            except json.JSONDecodeError:
                habits = {}

        if not isinstance(habits, dict):
            habits = {}

        # 初始化 _custom_keywords
        if "_custom_keywords" not in habits:
            habits["_custom_keywords"] = {}

        # 添加或更新关键词映射
        old_category = habits["_custom_keywords"].get(keyword)
        habits["_custom_keywords"][keyword] = category

        # 保存到数据库
        update_user_preferences(user_id, remembered_habits=json.dumps(habits, ensure_ascii=False))

        # 清除 Redis 缓存
        try:
            from app.services.cache_service import redis_cache
            redis_cache.delete(f"habits:user:{user_id}")
        except:
            pass

        if old_category:
            print(f"✅ 已更新自定义关键词: '{keyword}' ({old_category} → {category})")
        else:
            print(f"✅ 已添加自定义关键词: '{keyword}' -> '{category}'")

        return True

    except Exception as e:
        print(f"❌ 添加自定义关键词失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def _get_learned_habit_keywords_with_aliases(user_id: int = 1) -> dict:
    """
    获取用户已学习的习惯关键词及其语义别名

    Returns:
        {
            "晨跑": ["早起跑步", "晨间运动"],
            "学习": ["看书", "复习"]
        }
    """
    try:
        from app.models.task_model import get_user_preferences
        import json

        preferences = get_user_preferences(user_id)
        if not preferences or not preferences.remembered_habits:
            return {}

        habits = preferences.remembered_habits
        if isinstance(habits, str):
            habits = json.loads(habits)

        result = {}
        for keyword, data in habits.items():
            if not keyword.startswith("_") and data.get("learned", False):
                # 提取语义别名（如果有）
                aliases = data.get("semantic_aliases", [])
                result[keyword] = aliases

        return result
    except Exception as e:
        print(f"⚠️ 获取学习习惯失败: {e}")
        return {}


def add_semantic_alias(keyword: str, alias: str, user_id: int = 1) -> bool:
    """
    添加语义别名到学习习惯（可由 LLM 或用户行为触发）

    Args:
        keyword: 标准关键词（如 "晨跑"）
        alias: 语义别名（如 "早起跑步"）
        user_id: 用户ID

    Returns:
        是否成功
    """
    try:
        from app.models.task_model import get_user_preferences, update_user_preferences
        import json

        preferences = get_user_preferences(user_id)
        if not preferences:
            return False

        habits = preferences.remembered_habits
        if isinstance(habits, str):
            habits = json.loads(habits)

        if keyword not in habits:
            print(f"⚠️ 关键词 '{keyword}' 不存在，无法添加别名")
            return False

        # 初始化 semantic_aliases 列表
        if "semantic_aliases" not in habits[keyword]:
            habits[keyword]["semantic_aliases"] = []

        # 添加别名（避免重复）
        if alias not in habits[keyword]["semantic_aliases"]:
            habits[keyword]["semantic_aliases"].append(alias)
            update_user_preferences(user_id, remembered_habits=json.dumps(habits, ensure_ascii=False))
            print(f"✅ 已添加语义别名: '{keyword}' <- '{alias}'")

            # 清除 Redis 缓存
            from app.services.cache_service import redis_cache
            redis_cache.delete(f"habits:user:{user_id}")

        return True
    except Exception as e:
        print(f"❌ 添加语义别名失败: {e}")
        return False


def _fuzzy_keyword_match(title: str, keyword: str, threshold: float = 0.6) -> bool:
    """
    模糊关键词匹配：基于字符重叠度

    Args:
        title: 任务标题
        keyword: 习惯关键词
        threshold: 相似度阈值（0-1）

    Returns:
        是否匹配
    """
    if not title or not keyword:
        return False

    # 1. 如果关键词很短（<=2字），要求严格匹配
    if len(keyword) <= 2:
        return keyword in title

    # 2. 计算字符级别的 Jaccard 相似度
    title_chars = set(title)
    keyword_chars = set(keyword)

    if not keyword_chars:
        return False

    intersection = title_chars & keyword_chars
    union = title_chars | keyword_chars

    similarity = len(intersection) / len(union) if union else 0

    # 3. 额外检查：是否有连续子串匹配
    has_substring = any(
        keyword[i:i + 2] in title
        for i in range(len(keyword) - 1)
    )

    # 4. 综合判断：相似度高 或 有子串匹配
    return similarity >= threshold or has_substring

def apply_learned_habits(task_info: dict, user_id: int = 1) -> dict:
    """应用已学习的用户习惯到任务"""
    try:
        from app.models.task_model import get_user_preferences
        import json
        
        # 获取用户偏好
        preferences = get_user_preferences(user_id)
        if not preferences:
            return task_info
        
        # 解析习惯数据
        habits = preferences.remembered_habits
        if isinstance(habits, str):
            try:
                habits = json.loads(habits)
            except json.JSONDecodeError:
                return task_info
        
        if not isinstance(habits, dict):
            return task_info
        
        # 从任务标题提取关键词
        task_title = task_info.get("title", "")
        if not task_title:
            return task_info
        
        keywords = extract_task_keywords(task_title)
        
        applied_habits = []
        
        for keyword in keywords:
            if keyword.startswith("_"):
                continue
            
            habit = habits.get(keyword)
            if not habit:
                continue
            
            # ⭐ Phase 1 修复：只要有任何 preferred_ 字段就认为有学习习惯
            has_any_preference = any(k.startswith("preferred_") for k in habit.keys())
            if not has_any_preference:
                continue
            
            # 应用优先级偏好
            if "preferred_priority" in habit:
                confidence = habit.get("confidence", 0.5)
                old_priority = task_info.get("priority") or "medium"
                
                # ⭐ 优化：如果置信度高（>80%），即使用户指定了优先级也覆盖
                # 或者用户未指定优先级时直接应用
                if confidence >= 0.8 or not task_info.get("priority"):
                    task_info["priority"] = habit["preferred_priority"]
                    applied_habits.append(f"优先级: {old_priority} → {habit['preferred_priority']}")
                    print(f"🧠 应用习惯: [{keyword}] 优先使用 {habit['preferred_priority']} 优先级 (置信度: {confidence:.2f})")
            
            # 应用时长偏好
            if "preferred_duration" in habit:
                old_duration = task_info.get("duration")
                suggested_duration = habit["preferred_duration"]
                
                # 如果用户没有指定时长，或者当前时长与习惯差异较大
                if not old_duration or abs(old_duration - suggested_duration) > 30:
                    task_info["duration"] = suggested_duration
                    if old_duration:
                        applied_habits.append(f"时长: {old_duration}分钟 → {suggested_duration}分钟")
                    else:
                        applied_habits.append(f"时长: 设置为 {suggested_duration}分钟")
                    print(f"🧠 应用习惯: [{keyword}] 通常持续 {suggested_duration} 分钟")
            
            # 应用时间段偏好
            if "preferred_time_slot" in habit and not task_info.get("start_time"):
                time_slot = habit["preferred_time_slot"]
                applied_habits.append(f"时间段: {time_slot}")
                print(f"🧠 应用习惯: [{keyword}] 通常安排在 {time_slot}")
                # 注意：这里只是提示，实际排程由 scheduler 处理
            
            # 应用描述模板
            if "preferred_description_template" in habit and not task_info.get("description"):
                template = habit["preferred_description_template"]
                task_info["description"] = template.format(title=task_title)
                applied_habits.append("描述: 使用模板")
                print(f"🧠 应用习惯: [{keyword}] 使用描述模板")
        
        if applied_habits:
            task_info["applied_habits"] = applied_habits
            print(f"✨ 共应用 {len(applied_habits)} 个习惯到任务 '{task_title}'")
        
        return task_info
        
    except Exception as e:
        print(f"❌ 应用用户习惯失败: {e}")
        import traceback
        traceback.print_exc()
        return task_info


def get_learned_habits_summary(user_id: int = 1) -> dict:
    """获取已学习习惯的摘要信息（用于前端展示，⭐ 已优化：增加Redis缓存）"""
    import json
    from app.models.task_model import get_user_preferences
    from app.services.cache_service import redis_cache
    
    # ⭐ 先尝试从 Redis 获取
    redis_key = f"habits:user:{user_id}"
    cached_habits = redis_cache.get(redis_key)
    if cached_habits:
        print(f"✅ Redis缓存命中：用户习惯 user_id={user_id}")
        return cached_habits
    
    try:
        preferences = get_user_preferences(user_id)
        habits = json.loads(preferences.remembered_habits) if isinstance(preferences.remembered_habits, str) else preferences.remembered_habits
        
        learned_habits = []
        
        for keyword, data in habits.items():
            if keyword.startswith("_"):
                continue
            
            # ⭐ Phase 1 修复：只要有任何 preferred_ 字段就认为有学习习惯
            has_any_preference = any(k.startswith("preferred_") for k in data.keys())
            if not has_any_preference:
                continue
            
            habit_info = {
                "keyword": keyword,
                "preferences": {},
                "confidence": data.get("confidence", 0.5),
                "count": data.get("count", 0),
                "last_used": data.get("last_used"),
                "learned_at": data.get("learned_at")
            }
            
            for key, value in data.items():
                if key.startswith("preferred_"):
                    pref_type = key.replace("preferred_", "")
                    habit_info["preferences"][pref_type] = value
            
            learned_habits.append(habit_info)
        
        learned_habits.sort(key=lambda x: x["confidence"], reverse=True)
        
        total_habits = len([k for k in habits.keys() if not k.startswith("_")])
        active_habits = len(learned_habits)
        
        result = {
            "success": True,
            "summary": {
                "total_categories": total_habits,
                "active_habits": active_habits,
                "learned_habits": learned_habits
            }
        }
        
        # ⭐ 写入 Redis 缓存（TTL: 10分钟）
        redis_cache.set(redis_key, result, ttl=600)
        print(f"💾 已将用户习惯写入Redis缓存: user_id={user_id}, 习惯数={active_habits}")
        
        return result
        
    except Exception as e:
        print(f"获取习惯摘要失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "summary": {
                "total_categories": 0,
                "active_habits": 0,
                "learned_habits": []
            }
        }


def delete_learned_habit(keyword: str, user_id: int = 1) -> bool:
    """删除指定的已学习习惯（⭐ 已优化：清除Redis缓存）"""
    try:
        from app.models.task_model import get_user_preferences, update_user_preferences
        from app.services.cache_service import redis_cache
        import json
        
        preferences = get_user_preferences(user_id)
        habits = json.loads(preferences.remembered_habits) if isinstance(preferences.remembered_habits, str) else preferences.remembered_habits
        
        if keyword in habits:
            del habits[keyword]
            update_user_preferences(user_id, remembered_habits=json.dumps(habits, ensure_ascii=False))
            
            # ⭐ 清除Redis缓存
            redis_key = f"habits:user:{user_id}"
            redis_cache.delete(redis_key)
            
            print(f"🗑️ 已删除习惯: {keyword}，并清除Redis缓存")
            return True
        return False
    except Exception as e:
        print(f"删除习惯失败: {e}")
        return False


def reset_all_habits(user_id: int = 1) -> bool:
    """重置所有学习习惯（⭐ 已优化：清除Redis缓存）"""
    try:
        from app.models.task_model import update_user_preferences
        from app.services.cache_service import redis_cache
        
        update_user_preferences(user_id, remembered_habits="{}")
        
        # ⭐ 清除Redis缓存
        redis_key = f"habits:user:{user_id}"
        redis_cache.delete(redis_key)
        
        print("🔄 已重置所有学习习惯，并清除Redis缓存")
        return True
    except Exception as e:
        print(f"重置习惯失败: {e}")
        return False


def analyze_free_time(user_id: int, time_range: str = "tomorrow", activity: str = "rest") -> dict:
    """
    分析用户在指定时间范围内的空闲时间
    
    Args:
        user_id: 用户ID
        time_range: 时间范围 (today, tomorrow, day_after_tomorrow, this_weekend, this_week, next_week)
        activity: 活动类型 (rest, exercise, meeting, study, etc.)
    
    Returns:
        空闲时间分析结果
    """
    from datetime import timedelta
    
    now = datetime.now()
    
    # 计算时间范围
    if time_range == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        day_label = "今天"
    elif time_range == "tomorrow":
        start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        day_label = "明天"
    elif time_range == "day_after_tomorrow":
        start = (now + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        day_label = "后天"
    elif time_range == "this_weekend":
        days_until_saturday = (5 - now.weekday()) % 7
        if days_until_saturday == 0:
            days_until_saturday = 7
        start = (now + timedelta(days=days_until_saturday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=2)  # 周六和周日
        day_label = "本周末"
    elif time_range == "this_week":
        days_since_monday = now.weekday()
        start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        day_label = "本周"
    elif time_range == "next_week":
        days_until_next_monday = (7 - now.weekday()) % 7
        if days_until_next_monday == 0:
            days_until_next_monday = 7
        start = (now + timedelta(days=days_until_next_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        day_label = "下周"
    else:
        start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        day_label = "明天"
    
    # 获取用户任务
    from app.models.task_model import get_all_tasks
    tasks = get_all_tasks(user_id)
    
    # ⭐ 修复：过滤该时间范围内的任务（解析时间字符串）
    day_tasks = []
    for t in tasks:
        if t.start_time and t.status != "cancelled":
            try:
                task_start = datetime.fromisoformat(t.start_time) if isinstance(t.start_time, str) else t.start_time
                if start <= task_start < end:
                    day_tasks.append(t)
            except (ValueError, TypeError):
                continue
    
    # 计算总时长
    total_task_minutes = sum(t.duration or 0 for t in day_tasks)

    # 可用时间（假设每天 9:00-22:00 为可用时间，共13小时）
    work_start = start.replace(hour=9, minute=0)
    work_end = start.replace(hour=22, minute=0)
    available_minutes = (work_end - work_start).total_seconds() / 60
    
    # 空闲时间
    free_minutes = max(0, available_minutes - total_task_minutes)
    free_hours = free_minutes / 60
    
    # 根据活动类型给出建议时长
    activity_durations = {
        "rest": 60,
        "exercise": 90,
        "meeting": 60,
        "study": 120,
        "movie": 150,
        "shopping": 120,
        "other": 60
    }
    suggested_duration = activity_durations.get(activity, 60)
    
    # 判断是否有足够时间
    has_enough_time = free_minutes >= suggested_duration
    
    # 获取任务列表（用于显示）
    task_list = []
    for t in day_tasks[:10]:
        task_list.append({
            "title": t.title,
            "start_time": t.start_time if isinstance(t.start_time, str) else (t.start_time.isoformat() if t.start_time else None),
            "end_time": t.end_time if isinstance(t.end_time, str) else (t.end_time.isoformat() if t.end_time else None),
            "duration": t.duration,
            "priority": t.priority
        })
    
    return {
        "time_range": time_range,
        "day_label": day_label,
        "date": start.strftime('%Y-%m-%d'),
        "available_minutes": available_minutes,
        "total_task_minutes": total_task_minutes,
        "free_minutes": free_minutes,
        "free_hours": free_hours,
        "task_count": len(day_tasks),
        "has_enough_time": has_enough_time,
        "suggested_duration": suggested_duration,
        "activity": activity,
        "tasks": task_list
    }


def stop_scheduler():
    """
    停止定时任务调度器
    """
    global scheduler

    if scheduler.running:
        scheduler.shutdown()
        print("⏹️  定时任务调度器已停止")


# ✅ 新增：每5分钟检查即将到期的任务并推送提醒
def check_upcoming_deadlines_and_notify():
    """
    检查即将到期的任务并通过WebSocket推送提醒（每5分钟执行）

    通知分级策略：
    - 紧急（urgent）：1小时内到期 → WebSocket弹窗 + 通知中心
    - 普通（normal）：24小时内到期 → 仅通知中心
    - 信息（info）：超过24小时 → 不推送，仅在查询时显示
    """
    from app.models.task_model import get_all_tasks
    from app.services.notification_service import check_deadline_reminders
    from app.services.websocket_service import push_deadline_reminder
    import asyncio

    try:
        print(f"\n🔍 [{datetime.now()}] 检查即将到期的任务...")

        # 检查所有用户的任务
        all_users_tasks = get_all_tasks(status="pending")

        # 按用户分组
        user_tasks = {}
        for task in all_users_tasks:
            if task.user_id not in user_tasks:
                user_tasks[task.user_id] = []
            user_tasks[task.user_id].append(task)

        notified_count = 0

        # 对每个用户进行检查和推送
        for user_id, tasks in user_tasks.items():
            reminders = check_deadline_reminders(user_id, hours_before=24)

            for reminder in reminders:
                notification_type = reminder.get("notification_type", "info")

                # ✅ 只推送紧急和普通通知
                if notification_type in ["urgent", "normal"]:
                    try:
                        # 异步推送
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(push_deadline_reminder(reminder, user_id))
                        loop.close()

                        notified_count += 1
                        print(
                            f"  🔔 已推送{'紧急' if notification_type == 'urgent' else '普通'}提醒: {reminder['title']}")
                    except Exception as e:
                        print(f"  ⚠️ 推送失败: {e}")

        if notified_count > 0:
            print(f"✅ 本次共推送 {notified_count} 条提醒")
        else:
            print(f"ℹ️  无需推送的提醒")

    except Exception as e:
        print(f"❌ 检查即将到期任务失败: {e}")


# ✅ 新增：每小时检测任务冲突
def hourly_conflict_check():
    """
    每小时检测任务冲突并推送通知
    """
    from app.models.task_model import get_all_tasks
    from app.services.notification_service import check_and_notify_conflicts
    from app.services.websocket_service import push_conflict_notification
    import asyncio

    try:
        print(f"\n⚠️  [{datetime.now()}] 执行每小时冲突检测...")

        # 获取所有用户
        all_tasks = get_all_tasks(status="pending")
        user_ids = set(task.user_id for task in all_tasks)

        conflict_count = 0

        for user_id in user_ids:
            result = check_and_notify_conflicts(user_id)

            if result.get("conflict_count", 0) > 0:
                conflict_count += result["conflict_count"]

                # 推送冲突通知
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(push_conflict_notification(result, user_id))
                    loop.close()

                    print(f"  ⚠️  用户 {user_id} 发现 {result['conflict_count']} 个冲突")
                except Exception as e:
                    print(f"  ⚠️ 推送冲突通知失败: {e}")

        if conflict_count > 0:
            print(f"✅ 本次共发现 {conflict_count} 个冲突")
        else:
            print(f"ℹ️  未发现冲突")

    except Exception as e:
        print(f"❌ 冲突检测失败: {e}")


def start_scheduler():
    """
    启动定时任务调度器
    """
    global scheduler

    if scheduler.running:
        print("⚠️  调度器已在运行")
        return

    # ✅ 原有任务：每天凌晨0点检查任务超时
    scheduler.add_job(
        check_deadline_reminders,
        trigger=CronTrigger(hour=0, minute=0),
        id='check_deadlines',
        name='每日凌晨检查任务超时',
        replace_existing=True
    )

    # ✅ 原有任务：每天早上8点生成日程摘要
    scheduler.add_job(
        generate_daily_summary,
        trigger=CronTrigger(hour=8, minute=0),
        id='daily_summary',
        name='每日日程摘要',
        replace_existing=True
    )

    # ✅ 新增：每5分钟检查即将到期的任务并推送提醒
    scheduler.add_job(
        check_upcoming_deadlines_and_notify,
        trigger=IntervalTrigger(minutes=5),
        id='check_upcoming_deadlines',
        name='每5分钟检查即将到期任务',
        replace_existing=True
    )

    # ✅ 新增：每小时检测任务冲突
    scheduler.add_job(
        hourly_conflict_check,
        trigger=CronTrigger(minute=0),
        id='hourly_conflict_check',
        name='每小时检测任务冲突',
        replace_existing=True
    )

    # ✅ 新增：每天凌晨2点清理7天前的旧通知
    scheduler.add_job(
        delete_old_notifications,
        trigger=CronTrigger(hour=2, minute=0),
        id='cleanup_old_notifications',
        name='每日清理过期通知',
        replace_existing=True
    )

    scheduler.start()
    print("✅ 定时任务调度器已启动")
    print("   - 每天凌晨0点检查任务超时")
    print("   - 每天早上8点生成日程摘要")
    print("   - 每5分钟检查即将到期任务并推送提醒")
    print("   - 每小时检测任务冲突")
    print("   - 每天凌晨2点清理7天前的旧通知")




# ... existing code ...
