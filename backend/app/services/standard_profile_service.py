"""
标准作息模板服务
负责加载和管理人群标准配置（Layer 2）
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import time


class StandardProfileService:
    """标准作息模板服务"""
    
    _instance = None
    _profiles_cache = {}
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.config = self._load_config()
        self.profiles = self.config.get("standard_profiles", {})
        self.objective_constraints = self.config.get("objective_constraints", {})
        self.personalization_rules = self.config.get("personalization_rules", {})
        self.global_settings = self.config.get("global_settings", {})
        
        self._initialized = True
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = Path(__file__).parent.parent.parent / "config" / "standard_profiles.yaml"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 加载标准模板配置失败: {e}")
            return {}
    
    def get_profile(self, user_type: str) -> Optional[Dict[str, Any]]:
        """
        获取指定人群的标准模板
        
        Args:
            user_type: 用户类型 (student/worker/elderly)
        
        Returns:
            标准模板字典，如果不存在则返回None
        """
        if user_type not in self.profiles:
            print(f"⚠️ 未找到用户类型 '{user_type}' 的模板，使用默认模板")
            return self.profiles.get("worker")  # 默认使用工作者模板
        
        return self.profiles[user_type]
    
    def get_all_profile_types(self) -> list:
        """获取所有可用的用户类型"""
        return list(self.profiles.keys())
    
    def get_objective_constraints(self) -> Dict[str, Any]:
        """获取客观约束配置"""
        return self.objective_constraints
    
    def get_personalization_rules(self) -> Dict[str, Any]:
        """获取个性化调整规则"""
        return self.personalization_rules
    
    def check_objective_constraint(self, constraint_type: str, sub_type: str = None) -> Any:
        """
        检查客观约束
        
        Args:
            constraint_type: 约束类型 (time_limits/weather_impact/holiday_rules)
            sub_type: 子类型 (如 rain/snow/spring_festival)
        
        Returns:
            约束值，如果不存在则返回None
        """
        constraints = self.objective_constraints.get(constraint_type, {})
        
        if sub_type:
            return constraints.get(sub_type)
        else:
            return constraints
    
    def validate_personalization(self, param_name: str, value: Any) -> tuple:
        """
        验证个性化参数是否在允许范围内
        
        Args:
            param_name: 参数名称
            value: 参数值
        
        Returns:
            (is_valid: bool, message: str, corrected_value: Any)
        """
        rules = self.personalization_rules
        
        # 1. 验证工作时长
        if param_name in ["workday_hours", "weekend_hours"]:
            min_hours = rules["capacity_adjustment"]["min_workday_hours"]
            max_hours = rules["capacity_adjustment"]["max_workday_hours"]
            
            if value < min_hours:
                return (False, f"工作时长不能少于{min_hours}小时", min_hours)
            elif value > max_hours:
                return (False, f"工作时长不能超过{max_hours}小时", max_hours)
            else:
                return (True, "参数有效", value)
        
        # 2. 验证时间段偏移
        elif param_name == "time_slot_shift":
            max_early = rules["time_slot_deviation"]["max_early_shift"]
            max_late = rules["time_slot_deviation"]["max_late_shift"]
            
            if value < -max_early:
                return (False, f"最多只能提前{max_early}小时", -max_early)
            elif value > max_late:
                return (False, f"最多只能推迟{max_late}小时", max_late)
            else:
                return (True, "参数有效", value)
        
        # 3. 验证任务能耗系数
        elif param_name == "energy_cost_coefficient":
            adjustment_range = rules["task_energy_cost"]["adjustment_range"]
            
            if abs(value - 1.0) > adjustment_range:
                corrected = max(1.0 - adjustment_range, min(1.0 + adjustment_range, value))
                return (False, f"系数调整范围为±{adjustment_range}", corrected)
            else:
                return (True, "参数有效", value)
        
        return (True, "未知参数，跳过验证", value)
    
    def get_default_weights(self) -> Dict[str, float]:
        """获取默认评分权重"""
        return self.global_settings.get("default_weights", {})
    
    def get_cache_ttl(self, cache_type: str) -> int:
        """
        获取缓存TTL
        
        Args:
            cache_type: 缓存类型 (standard_profile/user_profile/objective_constraints)
        
        Returns:
            TTL秒数，None表示永久缓存
        """
        cache_config = self.global_settings.get("cache_ttl", {})
        return cache_config.get(cache_type)
    
    def format_schedule_for_display(self, user_type: str) -> str:
        """
        格式化作息时间为可读文本
        
        Args:
            user_type: 用户类型
        
        Returns:
            格式化的作息描述
        """
        profile = self.get_profile(user_type)
        if not profile:
            return "未知用户类型"
        
        schedule = profile["typical_schedule"]
        capacity = profile["capacity"]
        
        # 根据不同用户类型选择正确的容量字段
        if user_type == "student":
            capacity_hours = capacity.get("workday_study_hours", "N/A")
            capacity_label = "工作日学习时长"
        elif user_type == "worker":
            capacity_hours = capacity.get("workday_work_hours", "N/A")
            capacity_label = "工作日工作时长"
        elif user_type == "elderly":
            capacity_hours = capacity.get("daily_active_hours", "N/A")
            capacity_label = "每日活动时长"
        else:
            capacity_hours = "N/A"
            capacity_label = "容量"
        
        lines = [
            f"📅 {profile['name']}标准作息",
            f"   起床: {schedule['wake_up']}",
            f"   睡觉: {schedule['sleep']}",
            f"   高效时段: {', '.join(schedule['productive_hours'])}",
            f"   {capacity_label}: {capacity_hours}小时",
        ]
        
        if user_type == "elderly" and "rest_periods" in schedule:
            lines.append(f"   休息时段: {', '.join(schedule['rest_periods'])}")
        
        return "\n".join(lines)


# 全局实例
standard_profile_service = StandardProfileService()
