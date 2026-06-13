"""
三层约束评分系统
⭐ Phase 2: 实现客观约束 + 人群标准 + 个性化微调的评分机制
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from app.services.standard_profile_service import standard_profile_service


class ThreeLayerScoringSystem:
    """三层约束评分系统"""
    
    def __init__(self):
        self.profile_service = standard_profile_service
    
    def calculate_constrained_score(
        self, 
        slot: datetime, 
        task: Dict[str, Any], 
        user_id: int,
        user_type: str = "worker",
        existing_tasks: list = None,
        preferences: Dict = None
    ) -> Dict[str, Any]:
        """
        计算带三层约束的综合评分
        
        Args:
            slot: 候选时间槽
            task: 任务信息
            user_id: 用户ID
            user_type: 用户类型 (student/worker/elderly)
            existing_tasks: 现有任务列表
            preferences: 用户偏好
        
        Returns:
            {
                "final_score": 最终评分,
                "breakdown": {
                    "objective_penalty": 客观约束惩罚,
                    "standard_score": 人群标准分,
                    "personal_adjustment": 个性化调整分
                },
                "violations": []  # 违反的约束列表
            }
        """
        if preferences is None:
            preferences = {}
        if existing_tasks is None:
            existing_tasks = []
        
        # ===== Layer 1: 客观约束检查（硬性过滤）=====
        objective_result = self._check_objective_constraints(slot, task, user_type)
        
        if objective_result["blocked"]:
            # 违反客观约束，直接拒绝
            return {
                "final_score": -float('inf'),
                "breakdown": {
                    "objective_penalty": -float('inf'),
                    "standard_score": 0,
                    "personal_adjustment": 0
                },
                "violations": objective_result["violations"]
            }
        
        objective_penalty = objective_result["penalty"]
        
        # ===== Layer 2: 人群标准评分（基准分）=====
        standard_profile = self.profile_service.get_profile(user_type)
        standard_score = self._calculate_standard_score(
            slot, task, standard_profile, existing_tasks
        )
        
        # ===== Layer 3: 个性化微调（调整分）=====
        user_habits = self._get_user_habits(user_id)
        personal_adjustment = self._calculate_personal_adjustment(
            slot, task, standard_profile, user_habits
        )
        
        # ===== 综合评分 =====
        final_score = standard_score + personal_adjustment + objective_penalty
        
        # 确保分数在合理范围内
        final_score = max(0, min(100, final_score))
        
        return {
            "final_score": round(final_score, 2),
            "breakdown": {
                "objective_penalty": round(objective_penalty, 2),
                "standard_score": round(standard_score, 2),
                "personal_adjustment": round(personal_adjustment, 2)
            },
            "violations": objective_result["violations"]
        }
    
    def _check_objective_constraints(
        self, 
        slot: datetime, 
        task: Dict[str, Any],
        user_type: str
    ) -> Dict[str, Any]:
        """
        Layer 1: 检查客观约束
        
        Returns:
            {
                "blocked": bool,  # 是否被阻止
                "penalty": float,  # 惩罚分
                "violations": list  # 违反的约束列表
            }
        """
        penalty = 0
        violations = []
        blocked = False
        
        task_type = task.get("type", self._classify_task(task.get("title", "")))
        
        # 1.1 天气约束
        weather_penalty = self._check_weather_constraint(slot, task_type)
        if weather_penalty < -40:
            blocked = True
            violations.append(f"天气恶劣：不适合{task_type}")
        penalty += weather_penalty
        
        # 1.2 睡眠时间约束
        sleep_penalty = self._check_sleep_time_constraint(slot, user_type)
        if sleep_penalty < -45:
            blocked = True
            violations.append("睡眠时间不宜安排任务")
        penalty += sleep_penalty
        
        # 1.3 节假日约束
        holiday_penalty = self._check_holiday_constraint(slot, task_type)
        penalty += holiday_penalty
        if holiday_penalty < -35:
            violations.append("节假日不宜安排此类型任务")
        
        # 1.4 连续工作时长约束
        continuous_work_penalty = self._check_continuous_work_constraint(
            slot, task, user_type
        )
        penalty += continuous_work_penalty
        
        return {
            "blocked": blocked,
            "penalty": penalty,
            "violations": violations
        }
    
    def _check_weather_constraint(self, slot: datetime, task_type: str) -> float:
        """检查天气约束"""
        # TODO: 集成真实的天气API
        # 当前使用模拟数据
        weather_rules = self.profile_service.check_objective_constraint("weather_impact")
        
        if not weather_rules:
            return 0
        
        # 示例：假设检测到下雨
        # 实际应该调用 weather_service
        if task_type in ["exercise", "outdoor"]:
            # 下雨天户外运动
            rain_impact = weather_rules.get("rain", {})
            return rain_impact.get("outdoor_activity", 0)
        
        return 0
    
    def _check_sleep_time_constraint(self, slot: datetime, user_type: str) -> float:
        """检查睡眠时间约束"""
        profile = self.profile_service.get_profile(user_type)
        if not profile:
            return 0
        
        sleep_time_str = profile["typical_schedule"]["sleep"]
        wake_time_str = profile["typical_schedule"]["wake_up"]
        
        sleep_hour = int(sleep_time_str.split(":")[0])
        wake_hour = int(wake_time_str.split(":")[0])
        
        current_hour = slot.hour
        
        # 判断是否在睡眠时间内
        if sleep_hour > wake_hour:  # 跨天睡眠（如23:00-07:00）
            if current_hour >= sleep_hour or current_hour < wake_hour:
                return -50  # 严重惩罚
        else:  # 同天睡眠（如22:00-06:00）
            if sleep_hour <= current_hour < wake_hour:
                return -50
        
        return 0
    
    def _check_holiday_constraint(self, slot: datetime, task_type: str) -> float:
        """检查节假日约束"""
        from app.services.holiday_service import holiday_service
        
        # 获取节假日名称
        holiday_name = holiday_service.get_holiday_name(slot.date())
        if not holiday_name:
            return 0  # 工作日，无影响
        
        # 将节假日名称映射到配置中的类型
        holiday_rules = self.profile_service.check_objective_constraint("holiday_rules")
        
        # 判断是法定节假日还是周末
        is_legal_holiday = holiday_name != "周末"
        
        if is_legal_holiday:
            # 检查具体节假日类型（如春节、国庆等）
            for holiday_type in ["spring_festival", "national_day", "labor_day", 
                               "mid_autumn", "qingming", "dragon_boat"]:
                if holiday_type.replace("_", "") in holiday_name.lower():
                    rule = holiday_rules.get(holiday_type, {})
                    return rule.get(task_type, -15)  # 默认-15分
            
            # 其他法定节假日
            return -30  # 默认法定节假日惩罚
        else:
            # 周末
            weekend_rule = holiday_rules.get("weekend", {})
            return weekend_rule.get(task_type, -5)
    
    def _check_continuous_work_constraint(
        self, 
        slot: datetime, 
        task: Dict,
        user_type: str
    ) -> float:
        """检查连续工作时长约束"""
        time_limits = self.profile_service.check_objective_constraint("time_limits")
        max_continuous = time_limits.get("max_continuous_work", 4)
        
        task_duration_hours = task.get("duration", 60) / 60
        
        if task_duration_hours > max_continuous:
            # 超过最大连续工作时长
            excess_hours = task_duration_hours - max_continuous
            return -10 * excess_hours  # 每小时超额-10分
        
        return 0
    
    def _calculate_standard_score(
        self,
        slot: datetime,
        task: Dict[str, Any],
        standard_profile: Dict,
        existing_tasks: list
    ) -> float:
        """
        Layer 2: 计算人群标准评分
        
        基于标准作息模板的基准评分
        """
        score = 0
        hour = slot.hour + slot.minute / 60
        task_type = task.get("type", self._classify_task(task.get("title", "")))
        
        # 2.1 时间段匹配度（相对于标准作息）
        productive_hours = standard_profile["typical_schedule"]["productive_hours"]
        if self._is_in_productive_hours(hour, productive_hours):
            score += 30  # 在高效时段，加分
        else:
            score -= 10  # 在非高效时段，减分
        
        # 2.2 容量检查
        capacity = standard_profile["capacity"]
        daily_load = self._calculate_daily_load(slot.date(), existing_tasks)
        
        if "workday_work_hours" in capacity:
            max_capacity = capacity["workday_work_hours"] * 60
        elif "workday_study_hours" in capacity:
            max_capacity = capacity["workday_study_hours"] * 60
        else:
            max_capacity = capacity.get("daily_active_hours", 8) * 60
        
        if daily_load > max_capacity:
            overload_ratio = (daily_load - max_capacity) / max_capacity
            score -= int(overload_ratio * 50)  # 超载惩罚
        
        # 2.3 任务分布合理性
        distribution_preference = standard_profile["preferences"].get("task_distribution", "balanced")
        distribution_score = self._evaluate_task_distribution(
            slot.date(), hour, distribution_preference, existing_tasks
        )
        score += distribution_score
        
        # 2.4 休息间隔检查
        min_break = capacity.get("min_break_between_tasks", 0.25) * 60  # 转换为分钟
        if self._has_sufficient_break(slot, min_break, existing_tasks):
            score += 5  # 有足够休息，加分
        else:
            score -= 10  # 休息不足，减分
        
        return score
    
    def _calculate_personal_adjustment(
        self,
        slot: datetime,
        task: Dict[str, Any],
        standard_profile: Dict,
        user_habits: Dict
    ) -> float:
        """
        Layer 3: 计算个性化调整分
        
        基于用户习惯对标准评分的微调
        ⭐ 核心原则：符合偏好加分，偏离偏好减分
        ⭐ 重要：时间段偏离是主导因素，会抑制其他维度的加分
        """
        adjustment = 0
        hour = slot.hour + slot.minute / 60
        task_type = task.get("type", self._classify_task(task.get("title", "")))
        
        # ==================== 3.1 时间段偏好匹配（主导因素）====================
        time_slot_score = 0
        if "preferred_time_slot" in user_habits:
            personal_slot = user_habits["preferred_time_slot"]
            
            # 检查当前时间是否在个人偏好时段内
            if self._is_in_preferred_slot(hour, personal_slot):
                time_slot_score = 15  # ✅ 符合个人偏好，加分
            else:
                # ❌ 不在偏好时段，计算偏离程度并扣分
                deviation_hours = self._calculate_deviation_from_preference(hour, personal_slot)
                
                # 偏离越小扣分越少，偏离越大扣分越多
                if deviation_hours <= 2:
                    time_slot_score = -5   # 轻微偏离
                elif deviation_hours <= 4:
                    time_slot_score = -10  # 中度偏离
                else:
                    time_slot_score = -15  # 严重偏离
        
        # ==================== 3.2 时长偏好匹配 ====================
        duration_score = 0
        if "preferred_duration" in user_habits:
            preferred_duration = user_habits["preferred_duration"]
            actual_duration = task.get("duration", 60)
            duration_diff = abs(actual_duration - preferred_duration)
            
            if duration_diff <= 10:
                duration_score = 10  # 时长完全匹配
            elif duration_diff <= 30:
                duration_score = 5   # 时长接近
            else:
                duration_score = -5   # 时长不匹配
        
        # ==================== 3.3 优先级偏好 ====================
        priority_score = 0
        if "preferred_priority" in user_habits:
            preferred_priority = user_habits["preferred_priority"]
            actual_priority = task.get("priority", "medium")
            
            if preferred_priority == actual_priority:
                priority_score = 8  # 优先级匹配
            else:
                priority_score = -3  # 优先级不匹配
        
        # ==================== ⭐ 关键：时间段偏离抑制其他维度 ====================
        # 如果时间段严重偏离（<= -10），则其他维度得分减半
        if time_slot_score <= -10:
            # 严重偏离：其他维度只保留50%
            adjustment = time_slot_score + int(duration_score * 0.5) + int(priority_score * 0.5)
        elif time_slot_score < 0:
            # 轻微/中度偏离：其他维度保留75%
            adjustment = time_slot_score + int(duration_score * 0.75) + int(priority_score * 0.75)
        else:
            # 时间段符合：正常累加
            adjustment = time_slot_score + duration_score + priority_score
        
        return adjustment
    
    # ==================== 辅助方法 ====================
    
    def _is_in_productive_hours(self, hour: float, productive_hours: list) -> bool:
        """检查是否在高效时段内"""
        for time_range in productive_hours:
            start_str, end_str = time_range.split("-")
            start_hour = int(start_str.split(":")[0]) + int(start_str.split(":")[1]) / 60
            end_hour = int(end_str.split(":")[0]) + int(end_str.split(":")[1]) / 60
            
            if start_hour <= hour < end_hour:
                return True
        return False
    
    def _calculate_daily_load(self, target_date: datetime.date, existing_tasks: list) -> float:
        """计算某天的总任务负载（分钟）"""
        total_minutes = 0
        for task in existing_tasks:
            if task.get("status") in ["cancelled", "done", "overdue"]:
                continue
            
            task_start = self._parse_time(task.get("start_time"))
            task_end = self._parse_time(task.get("end_time"))
            
            if task_start and task_end and task_start.date() == target_date:
                duration = (task_end - task_start).total_seconds() / 60
                total_minutes += duration
        
        return total_minutes
    
    def _evaluate_task_distribution(
        self, 
        date: datetime.date, 
        hour: float, 
        preference: str,
        existing_tasks: list
    ) -> float:
        """评估任务分布合理性"""
        # 简化实现：根据偏好给予基础分
        if preference == "front_loaded" and hour < 12:
            return 10  # 上午安排重要任务
        elif preference == "spread_out":
            # 检查当天已有任务数量
            day_tasks = [t for t in existing_tasks 
                        if self._parse_time(t.get("start_time")).date() == date]
            if len(day_tasks) < 3:
                return 5  # 任务较少，分散安排
        elif preference == "balanced":
            return 5  # 均匀分布
        
        return 0
    
    def _has_sufficient_break(
        self, 
        slot: datetime, 
        min_break_minutes: float,
        existing_tasks: list
    ) -> bool:
        """检查是否有足够的休息间隔"""
        for task in existing_tasks:
            if task.get("status") in ["cancelled", "done"]:
                continue
            
            task_end = self._parse_time(task.get("end_time"))
            if task_end:
                gap_minutes = (slot - task_end).total_seconds() / 60
                if 0 < gap_minutes < min_break_minutes:
                    return False  # 休息不足
        
        return True
    
    def _calculate_deviation_from_preference(self, hour: float, preferred_slot: str) -> float:
        """计算当前时间偏离个人偏好的小时数"""
        slot_ranges = {
            "morning": (6, 12),
            "noon": (12, 14),
            "afternoon": (14, 18),
            "evening": (18, 22),
            "night": (22, 24)
        }
        
        if preferred_slot not in slot_ranges:
            return 12  # 默认最大偏离
        
        start, end = slot_ranges[preferred_slot]
        center = (start + end) / 2  # 偏好时段的中心点
        
        # 计算距离中心点的小时数
        deviation = abs(hour - center)
        
        # 如果超过半天，取反方向的最小值（处理跨天情况）
        if deviation > 12:
            deviation = 24 - deviation
        
        return deviation
    
    def _is_in_preferred_slot(self, hour: float, preferred_slot: str) -> bool:
        """检查是否在偏好的时间段内"""
        slot_ranges = {
            "morning": (6, 12),
            "noon": (12, 14),
            "afternoon": (14, 18),
            "evening": (18, 22),
            "night": (22, 24)
        }
        
        if preferred_slot not in slot_ranges:
            return False
        
        start, end = slot_ranges[preferred_slot]
        return start <= hour < end
    
    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串"""
        if not time_str:
            return None
        try:
            return datetime.fromisoformat(time_str)
        except:
            return None
    
    def _classify_task(self, title: str) -> str:
        """分类任务类型"""
        if any(kw in title for kw in ["会议", "开会", "讨论"]):
            return "meeting"
        elif any(kw in title for kw in ["运动", "健身", "跑步"]):
            return "exercise"
        elif any(kw in title for kw in ["学习", "阅读", "复习"]):
            return "study"
        return "other"
    
    def _get_user_habits(self, user_id: int) -> Dict:
        """获取用户习惯（简化版，实际应从数据库读取）"""
        # TODO: 集成真实的用户习惯查询
        return {}


# 全局实例
three_layer_scoring = ThreeLayerScoringSystem()
