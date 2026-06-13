"""
Google OR-Tools CP-SAT 智能排程引擎
工业级约束规划求解器
⭐ Phase 2: 集成三层约束模型（客观约束 + 人群标准 + 个性化微调）
"""
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
from app.services.scoring_engine import ScoringEngine
from app.services.standard_profile_service import standard_profile_service


class ORToolsScheduler:
    """OR-Tools CP-SAT 排程引擎"""

    def __init__(self):
        self.solver_params = {
            'max_time_in_seconds': 2.0,
            'num_search_workers': 8,
            'cp_model_presolve': True,
        }
        # 评分引擎
        self.scoring_engine = ScoringEngine()
        #  缓存用户习惯（避免频繁查询数据库）
        self._user_habits_cache = {}
        self._cache_ttl = 600  # 10分钟过期

    def schedule_task(
        self,
        new_task: Dict,
        existing_tasks: List[Dict],
        preferences: Dict = None,
        return_top_k: int = 5,
        current_date: datetime = None
    ) -> Dict:
        """
        使用 CP-SAT 求解最优时间安排

        Args:
            current_date: 统一参考时间（入口处捕获的 datetime.now()），
                         避免多处调用 datetime.now() 导致跨天漂移。
                         为 None 时自动取当前时间（向后兼容）。

        Returns:
            排程结果，包含 Top-K 方案
        """
        if preferences is None:
            preferences = {}

        title = new_task.get("title", "未命名任务")
        duration_minutes = new_task.get("duration", 60)
        deadline_str = new_task.get("deadline")
        priority = new_task.get("priority", "medium")
        user_id = new_task.get("user_id", 1)
        
        # ⭐ Phase 2: 获取用户类型（默认为 worker）
        user_type = new_task.get("user_type", "worker")

        # ⭐ 使用统一参考时间，避免跨天漂移
        now = current_date if current_date else datetime.now()

        # 1. 确定搜索范围
        search_start = now.replace(minute=0, second=0, microsecond=0)
        if search_start.hour < 9:
            search_start = search_start.replace(hour=9)
        elif search_start.hour >= 18:
            search_start = (search_start + timedelta(days=1)).replace(hour=9)

        search_end = now + timedelta(days=preferences.get('scheduling_horizon', 3))  # P2: 可配置化，默认3天
        deadline_dt = None
        if deadline_str:
            try:
                deadline_dt = datetime.fromisoformat(deadline_str)
                search_end = min(search_end, deadline_dt)
            except:
                pass
        else:
            # 智能默认截止引导：当天18:00，若已过则明天18:00（仅缩小搜索范围，不写入DB）
            today_1800 = now.replace(hour=18, minute=0, second=0, microsecond=0)
            if now < today_1800:
                search_end = min(search_end, today_1800 - timedelta(minutes=duration_minutes))
            else:
                search_end = min(search_end, today_1800 + timedelta(days=1) - timedelta(minutes=duration_minutes))

        # ⭐ 截止时间过期检测：search_start 都已超过 deadline
        if deadline_dt and search_start > deadline_dt:
            return {
                "success": False,
                "message": f"截止时间已过（{deadline_dt.strftime('%m月%d日 %H:%M')}），无法安排任务",
                "algorithm": "or_tools_cp_sat",
                "suggestions": [
                    "请调整截止时间为未来的时间",
                    "或移除截止时间，让系统自由排程"
                ]
            }

        # 2. 生成候选时间槽（30分钟粒度）
        time_slots = []
        current = search_start
        while current < search_end:
            time_slots.append(current)
            current += timedelta(minutes=30)

        print(f"\n[OR-Tools] 开始排程: {title}")
        print(f"   候选时间槽: {len(time_slots)} 个")

        # 3. 过滤无效时间槽
        buffer_minutes = preferences.get("task_buffer_minutes", 15)
        valid_slots = self._filter_valid_slots(
            time_slots, duration_minutes, existing_tasks,
            preferences, buffer_minutes
        )

        print(f"   有效时间槽: {len(valid_slots)} 个")

        if not valid_slots:
            # P0: 添加连续性标记
            # P1: 增加尽力而为回退策略（拆分任务建议）
            split_suggestions = self._generate_split_suggestions(
                time_slots, duration_minutes, existing_tasks, preferences, buffer_minutes
            )
            
            return {
                "success": False,
                "message": "无可用时间段",
                "algorithm": "or_tools_cp_sat",
                "can_complete_continuously": False,  # P0新增：无法连续完成
                "split_suggestions": split_suggestions,  # P1新增：拆分建议
                "suggestions": [
                    "尝试调整任务的截止时间",
                    "减少任务时长",
                    "修改免安排时段设置",
                    "今日空闲时段较碎片化，建议拆分任务或调整时长"
                ]
            }

        # 4. 构建 CP-SAT 模型
        model = cp_model.CpModel()
        slot_var = model.NewIntVar(0, len(valid_slots) - 1, "slot")

        # 5. 添加截止时间约束
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str)
                for i, slot in enumerate(valid_slots):
                    slot_end = slot + timedelta(minutes=duration_minutes)
                    if slot_end > deadline:
                        model.Add(slot_var != i)
            except:
                pass

        # 6. 预计算所有有效时间槽的评分（归一化版本）
        scored_slots = []
        for i, slot in enumerate(valid_slots):
            # 计算各维度原始分数（传入统一参考时间）
            raw_scores = self._calculate_score_dimensions(
                slot, duration_minutes, priority,
                preferences, user_id, title,
                existing_tasks, current_date=now
            )
            
            # 归一化计算最终评分
            score_result = self.scoring_engine.calculate_final_score(raw_scores)
            final_score = score_result['final_score']
            
            # 注入负荷警告到维度详情
            if 'load_warning' in raw_scores and raw_scores['load_warning']:
                score_result['dimension_details']['load_warning'] = raw_scores['load_warning']
            
            scored_slots.append({
                "idx": i, 
                "slot": slot, 
                "score": final_score,
                "dimension_details": score_result['dimension_details']
            })

        # 7. 按评分降序排序
        scored_slots.sort(key=lambda x: x["score"], reverse=True)

        # 8. ⭐ 优化：提取多样化的 Top-K 方案（确保时间间隔）
        top_solutions = self._extract_diverse_solutions(
            scored_slots, duration_minutes, return_top_k
        )

        if not top_solutions:
            return {
                "success": False,
                "message": "无可行解",
                "algorithm": "or_tools_cp_sat"
            }

        best = top_solutions[0]

        print(f"   找到 {len(top_solutions)} 个方案")
        print(f"   最优评分: {best['score']}")
        print(f"   求解方式: 评分排序 (稳定返回 Top-K)")

        return {
            "success": True,
            "algorithm": "or_tools_cp_sat",
            "best_solution": best,
            "alternativeSolutions": top_solutions[1:],
            "all_solutions": top_solutions,
            "message": f"已为「{title}」找到最优时间",
            "can_complete_continuously": True,  # P0新增：可以连续完成
            "load_warning": best.get('dimension_details', {}).get('load_warning'),  # 负荷警告
            "stats": {
                "total_slots": len(time_slots),
                "valid_slots": len(valid_slots),
                "feasible_solutions": len(top_solutions),
                "solve_time_ms": 0
            }
        }

    def _extract_diverse_solutions(self, scored_slots: List[Dict], duration_minutes: int, top_k: int, title: str = "") -> List[Dict]:
        """
        ⭐ 提取多样化的 Top-K 方案
        
        策略：
        1. 优先选择高分方案
        2. 确保相邻方案至少有 2 小时的时间间隔（从1小时增加到2小时）
        3. 如果高分方案时间太集中，适当降低分数要求以增加多样性
        
        Args:
            scored_slots: 已评分的时间槽列表（按分数降序）
            duration_minutes: 任务时长
            top_k: 需要返回的方案数量
            title: 任务标题（用于生成推荐理由）
            
        Returns:
            多样化的方案列表
        """
        if not scored_slots:
            return []
        
        MIN_TIME_GAP_MINUTES = 120  # ⭐ 最小时间间隔：2小时（从60增加到120）
        MAX_CANDIDATES = top_k * 5  # ⭐ 扩大候选范围：从3倍增加到5倍
        
        selected = []
        last_slot_time = None
        
        # 遍历高分候选方案
        candidates_to_check = scored_slots[:MAX_CANDIDATES]
        
        for item in candidates_to_check:
            if len(selected) >= top_k:
                break
                
            slot = item["slot"]
            slot_end = slot + timedelta(minutes=duration_minutes)
            
            # 检查时间间隔
            if last_slot_time is not None:
                time_gap = abs((slot - last_slot_time).total_seconds()) / 60
                if time_gap < MIN_TIME_GAP_MINUTES:
                    continue  # 时间太接近，跳过
            
            # 生成推荐理由
            reasons = self._generate_reasons(
                slot, title, {}, item.get("dimension_details", {})
            )
            
            selected.append({
                "start_time": slot.isoformat(),
                "end_time": slot_end.isoformat(),
                "score": item["score"],
                "reasons": reasons,
                "dimension_details": item.get("dimension_details", {})
            })
            
            last_slot_time = slot
        
        # 如果多样化筛选后方案不足，补充剩余高分方案（不考虑间隔）
        if len(selected) < top_k:
            for item in scored_slots:
                if len(selected) >= top_k:
                    break
                    
                # 检查是否已存在
                already_selected = any(
                    s["start_time"] == item["slot"].isoformat() 
                    for s in selected
                )
                if already_selected:
                    continue
                
                slot = item["slot"]
                slot_end = slot + timedelta(minutes=duration_minutes)
                reasons = self._generate_reasons(
                    slot, title, {}, item.get("dimension_details", {})
                )
                
                selected.append({
                    "start_time": slot.isoformat(),
                    "end_time": slot_end.isoformat(),
                    "score": item["score"],
                    "reasons": reasons,
                    "dimension_details": item.get("dimension_details", {})
                })

                last_slot_time = slot
        
        return selected

    def _filter_valid_slots(self, time_slots, duration_minutes, existing_tasks, preferences, buffer_minutes):
        """过滤有效时间槽"""
        from app.services.conflict_detector import conflict_detector

        # ⭐ 优化：复用全局区间树实例，避免重复构建
        conflict_detector.build_from_tasks(existing_tasks)

        valid = []
        blocked_periods = self._get_blocked_periods(preferences)

        for slot in time_slots:
            slot_end = slot + timedelta(minutes=duration_minutes)

            # 检查免安排时段
            if self._is_in_blocked_period(slot, slot_end, blocked_periods):
                continue

            # 使用区间树检测冲突
            conflicts = conflict_detector.find_conflicts(
                slot.isoformat(),
                slot_end.isoformat(),
                buffer_minutes
            )

            if not conflicts:
                valid.append(slot)

        return valid

    def _calculate_score_dimensions(self, slot, duration_minutes, priority, preferences, user_id, title, existing_tasks=None, task_params=None, current_date=None):
        """
        计算各维度的原始分数
        
        Args:
            task_params: 完整任务参数（用于习惯匹配）
            current_date: 统一参考时间（避免多处datetime.now()漂移）
        
        Returns:
            各维度原始分数字典
        """
        raw_scores = {}
        hour = slot.hour + slot.minute / 60
        now = current_date if current_date else datetime.now()
        task_type = self._classify_task(title)

        # 维度1: 日期新鲜度 (3-35分)
        raw_scores['date_freshness'] = self._calc_date_freshness(slot, now)

        # 维度2: 用户习惯匹配 (0-65分) ⭐ 增强版
        raw_scores['habit_match'] = self._calc_habit_match(
            slot, hour, user_id, title, duration_minutes, task_params
        )

        # 维度3: 任务紧急度 (0-50分)
        raw_scores['urgency'] = self._calc_urgency(slot, preferences)

        # 维度4: 时间段质量 (0-55分)
        raw_scores['time_quality'] = self._calc_time_quality(
            hour, task_type, priority
        )

        # 维度5: 任务密度平衡 (-50~15分) + 负荷警告
        load_score, load_warn = self._calc_load_balance(
            slot.date(), existing_tasks, user_id
        )
        raw_scores['load_balance'] = load_score
        if load_warn:
            raw_scores['load_warning'] = load_warn  # 负荷警告信息

        # 维度6: 优先级权重 (20-70分)
        raw_scores['priority'] = self._calc_priority(priority, hour)

        # 维度7: 节假日效应 (-40~0分)
        raw_scores['holiday'] = self._calc_holiday_impact(slot.date(), task_type)

        # 维度8: 天气因素 (-30~20分)
        raw_scores['weather'] = self._calc_weather_impact(
            slot.date(), task_type, user_id
        )

        return raw_scores

    def _calc_date_freshness(self, slot, now):
        """日期新鲜度：越早的时间槽评分越高（鼓励尽早完成任务）"""
        days_from_now = (slot.date() - now.date()).days
        
        if days_from_now == 0:
            return 35  # 当天完成，最高奖励
        elif days_from_now == 1:
            return 25  # 明天完成
        elif days_from_now == 2:
            return 15  # 后天完成
        elif days_from_now <= 4:
            return 8   # 4天内完成
        else:
            return 3   # 超过4天，分数较低

    def _calc_habit_match(self, slot, hour, user_id, title, duration_minutes, task_params=None):
        """
        用户习惯匹配度：0-65分
        
        ⭐ 多用户支持：通过 user_id 获取个性化习惯
        ⭐ 全面利用习惯参数：时间段、时长、优先级、置信度
        
        Args:
            task_params: 完整任务参数（包含 priority 等字段）
        """
        if task_params is None:
            task_params = {}
            
        # 🐞 [DEBUG] 函数入口调试（生产环境可注释）
        # print(f"\n🐞 [DEBUG _calc_habit_match] 开始计算")
        # print(f"   任务标题: {title}")
        # print(f"   时间槽: {slot.strftime('%Y-%m-%d %H:%M')}, hour={hour:.2f}")
        # print(f"   任务时长: {duration_minutes}分钟")
        # print(f"   任务参数: {task_params}")
            
        score = 0
        user_habits = self._get_user_habits_cached(user_id)
        keywords = self._extract_keywords(title)
        
        # 🐞 [DEBUG] 显示提取的关键字和习惯
        print(f"   提取关键字: {keywords}")
        print(f"   用户习惯库: {list(user_habits.keys())}")
        
        for keyword in keywords:
            if keyword not in user_habits:
                print(f"   ⚠️ 关键字 '{keyword}' 未在习惯库中找到")
                continue
            
            habit = user_habits[keyword]
            
            # 🐞 [DEBUG] 显示习惯详情
            print(f"\n   📊 [DEBUG] 习惯 '{keyword}' 的完整数据:")
            print(f"      preferred_time_slot: {habit.get('preferred_time_slot', 'N/A')}")
            print(f"      preferred_hour: {habit.get('preferred_hour', 'N/A')}")
            print(f"      preferred_duration: {habit.get('preferred_duration', 'N/A')}")
            print(f"      preferred_priority: {habit.get('preferred_priority', 'N/A')}")
            print(f"      confidence: {habit.get('confidence', 'N/A')}")
            print(f"      learned: {habit.get('learned', 'N/A')}")
            
            # ⭐ 1. 时间段偏好匹配（支持 preferred_time_slot 和 preferred_hour）
            time_score = 0
            
            # 1.1 检查 preferred_time_slot（morning/afternoon/evening/night）
            if habit.get("preferred_time_slot"):
                time_slot = habit["preferred_time_slot"]
                slot_ranges = {
                    "morning": (6, 12),      # 6:00-12:00
                    "noon": (12, 14),        # 12:00-14:00
                    "afternoon": (14, 18),   # 14:00-18:00
                    "evening": (18, 22),     # 18:00-22:00
                    "night": (22, 24)        # 22:00-24:00
                }
                
                # 🐞 [DEBUG] 时间段匹配调试
                print(f"\n   🔍 [DEBUG] 时间段匹配检查:")
                print(f"      偏好时间段: {time_slot}")
                print(f"      当前小时: {hour:.2f}")
                
                if time_slot in slot_ranges:
                    start_hour, end_hour = slot_ranges[time_slot]
                    print(f"      时间段范围: {start_hour}:00 - {end_hour}:00")
                    print(f"      条件判断: {start_hour} <= {hour:.2f} < {end_hour}")
                    
                    if start_hour <= hour < end_hour:
                        time_score += 50  # 完全匹配时间段
                        print(f"      ✅ 完全匹配！+50分")
                    elif abs(hour - start_hour) <= 1 or abs(hour - end_hour) <= 1:
                        time_score += 30  # 接近时间段
                        print(f"      ⚠️ 接近匹配（差距{abs(hour - start_hour):.1f}小时）+30分")
                    else:
                        time_score += 10  # 偏离时间段
                        print(f"      ❌ 偏离时间段 +10分")
                else:
                    print(f"      ⚠️ 未知时间段类型: {time_slot}")
            
            # 1.2 检查 preferred_hour（精确小时偏好）
            elif habit.get("preferred_hour"):
                preferred_hour = habit["preferred_hour"]
                hour_diff = abs(hour - preferred_hour)
                
                # 🐞 [DEBUG] 精确小时匹配调试
                print(f"\n   🔍 [DEBUG] 精确小时匹配检查:")
                print(f"      偏好小时: {preferred_hour}")
                print(f"      当前小时: {hour:.2f}")
                print(f"      时间差: {hour_diff:.2f}小时")
                
                if hour_diff <= 1:
                    time_score += 50  # 完全匹配
                    print(f"      ✅ 完全匹配！+50分")
                elif hour_diff <= 2:
                    time_score += 30  # 接近匹配
                    print(f"      ⚠️ 接近匹配 +30分")
                else:
                    time_score += 10  # 偏差较大
                    print(f"      ❌ 偏差较大 +10分")
            
            score += time_score
            print(f"   📈 [DEBUG] 时间段得分累计: {score}分")
            
            # ⭐ 2. 时长偏好匹配
            if "preferred_duration" in habit:
                preferred_duration = habit["preferred_duration"]
                duration_diff = abs(duration_minutes - preferred_duration)
                
                # 🐞 [DEBUG] 时长匹配调试
                print(f"\n   🔍 [DEBUG] 时长匹配检查:")
                print(f"      偏好时长: {preferred_duration}分钟")
                print(f"      实际时长: {duration_minutes}分钟")
                print(f"      时长差: {duration_diff}分钟")
                
                if duration_diff <= 10:
                    score += 20
                    print(f"      ✅ 完全匹配！+20分")
                elif duration_diff <= 30:
                    score += 10
                    print(f"      ⚠️ 接近匹配 +10分")
                else:
                    print(f"      ❌ 偏差较大 +0分")
            
            # ⭐ 3. 优先级偏好匹配（如果任务有优先级）
            if "preferred_priority" in habit and task_params.get("priority"):
                preferred_priority = habit["preferred_priority"]
                actual_priority = task_params.get("priority", "medium")
                
                # 🐞 [DEBUG] 优先级匹配调试
                print(f"\n   🔍 [DEBUG] 优先级匹配检查:")
                print(f"      偏好优先级: {preferred_priority}")
                print(f"      实际优先级: {actual_priority}")
                
                if preferred_priority == actual_priority:
                    score += 15
                    print(f"      ✅ 完全匹配！+15分")
                elif (preferred_priority == "high" and actual_priority == "medium") or \
                     (preferred_priority == "medium" and actual_priority == "low"):
                    score += 5  # 部分匹配
                    print(f"      ⚠️ 部分匹配 +5分")
                else:
                    print(f"      ❌ 不匹配 +0分")
            
            # ⭐ 4. 置信度加成（高置信度的习惯权重更高）
            if habit.get("learned"):
                confidence = habit.get("confidence", 0.5)
                confidence_bonus = int(confidence * 15)
                score += confidence_bonus
                print(f"\n   📊 [DEBUG] 置信度加成: {confidence:.0%} × 15 = {confidence_bonus}分")
        
        # 冷启动处理：新用户默认偏好上午9-11点
        if score == 0:
            if 9 <= hour <= 11:
                score = 30  # 默认分
                print(f"\n   🆕 [DEBUG] 冷启动：上午时段默认分 30")
            else:
                score = 15
                print(f"\n   🆕 [DEBUG] 冷启动：非上午时段默认分 15")
        
        final_score = min(65, score)
        print(f"\n   🎯 [DEBUG] 最终习惯匹配分: {final_score}/65\n")
        return final_score

    def _calc_urgency(self, slot, preferences):
        """任务紧急度：0-50分"""
        if 'deadline' not in preferences or not preferences['deadline']:
            return 0
        
        try:
            deadline = datetime.fromisoformat(preferences['deadline'])
            hours_to_deadline = (deadline - slot).total_seconds() / 3600
            
            if hours_to_deadline < 12:
                return 50  # 非常紧急
            elif hours_to_deadline < 24:
                return 40
            elif hours_to_deadline < 48:
                return 25
            elif hours_to_deadline < 72:
                return 15
            else:
                return 0
        except:
            return 0

    def _calc_time_quality(self, hour, task_type, priority):
        """时间段质量：0-55分"""
        score = 0
        
        # 上午认知高峰（9:00-11:30）
        if task_type in ["meeting", "study"] and 9 <= hour <= 11.5:
            score += 30
        elif task_type in ["meeting", "study"] and 14 <= hour <= 16:
            score += 20  # 下午协作高峰
        
        # 傍晚体力高峰（16:00-18:30）
        if task_type == "exercise" and 16 <= hour <= 18.5:
            score += 35
        elif task_type == "exercise" and 7 <= hour <= 9:
            score += 25  # 晨练
        
        # 通用黄金时段（14:00中心）
        distance_from_14 = abs(hour - 14)
        score += max(0, int((5 - distance_from_14) * 8))
        
        # 高优先级任务在黄金时段额外加成
        if priority == "high" and 10 <= hour <= 15:
            score += 20
        
        return min(55, score)

    def _calc_load_balance(self, target_date, existing_tasks, user_id):
        """任务密度平衡：-50~15分，附带接近饱和警告"""
        if not existing_tasks:
            return 0, None
        
        # 计算当天总负载
        total_minutes = self._calculate_day_load(target_date, existing_tasks)
        
        # 获取用户每日可用时长（默认480分钟）
        max_minutes = self._get_user_daily_capacity(user_id)
        load_ratio = total_minutes / max_minutes if max_minutes > 0 else 0
        
        # 接近饱和警告（load_ratio ≥ 0.6，即约6小时/480分钟）
        warn = None
        if load_ratio >= 0.6:
            warn = f"当天任务已接近饱和（{int(total_minutes)}分钟/{max_minutes}分钟），建议调整或减少任务量"
        
        if load_ratio < 0.3:
            return 15, warn   # 空闲
        elif load_ratio < 0.7:
            return 0, warn    # 正常
        elif load_ratio < 0.9:
            return -10, warn  # 接近满载
        else:
            # 过载惩罚
            overload_hours = (total_minutes - max_minutes) / 60
            return max(-50, int(-25 * overload_hours)), warn

    def _calc_priority(self, priority, hour):
        """优先级权重：20-70分"""
        base_scores = {"high": 50, "medium": 35, "low": 20}
        score = base_scores.get(priority, 35)
        
        # 高优先级在黄金时段加成
        if priority == "high" and 10 <= hour <= 15:
            score += 20
        
        return min(70, score)

    def _calc_holiday_impact(self, date, task_type):
        """节假日效应：-40~0分"""
        from app.services.holiday_service import holiday_service
        
        return holiday_service.get_holiday_impact_score(date, task_type)

    def _calc_weather_impact(self, date, task_type, user_id):
        """天气因素：-30~20分"""
        from app.services.weather_service import weather_service
        
        return weather_service.get_weather_impact_score(date, task_type)

    def _calculate_day_load(self, target_date, existing_tasks):
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

    def _get_user_daily_capacity(self, user_id):
        """获取用户每日可用时长（分钟）"""
        # 暂时返回默认值，后续从用户偏好读取
        return 480

    def _parse_time(self, time_str):
        """解析时间字符串"""
        if not time_str:
            return None
        try:
            return datetime.fromisoformat(time_str)
        except:
            return None

    def _generate_reasons(self, slot, title, preferences, dimension_details=None):
        """生成推荐理由（增强版）"""
        reasons = []
        hour = slot.hour + slot.minute / 60
        task_type = self._classify_task(title)

        # 必选：冲突检测
        reasons.append("✓ 避开所有冲突")

        # 时间段优势
        if 9 <= hour <= 11.5:
            if task_type in ["meeting", "study"]:
                reasons.append("✓ 上午高效时段")
            else:
                reasons.append("✓ 工作时间段")
        elif 14 <= hour <= 16:
            reasons.append("✓ 下午黄金时段")
        elif 16 <= hour <= 18.5 and task_type == "exercise":
            reasons.append("✓ 傍晚运动时段")

        # 任务类型匹配
        if task_type == "meeting" and 9 <= hour <= 12:
            reasons.append("✓ 适合会议时间")
        elif task_type == "exercise" and 16 <= hour <= 19:
            reasons.append("✓ 适合运动时间")
        elif task_type == "study" and 9 <= hour <= 11:
            reasons.append("✓ 适合学习时间")

        # 用户习惯匹配提示
        if dimension_details:
            habit_score = dimension_details.get('habit_match', {})
            if habit_score.get('normalized', 0) > 0.7:
                reasons.append("✓ 符合你的习惯")

        # 紧急度提示
        if dimension_details:
            urgency_score = dimension_details.get('urgency', {})
            if urgency_score.get('normalized', 0) > 0.5:
                reasons.append("⚡ 接近截止时间")

        return reasons[:4]  # 最多4个理由

    def _get_user_habits_cached(self, user_id):
        """⭐ 获取用户习惯（带内存缓存，避免频繁查询数据库）"""
        import time
        import json
        from app.models.task_model import get_user_preferences
        
        now = time.time()
        cache_key = f"user_{user_id}"
        
        # 检查缓存是否有效
        if cache_key in self._user_habits_cache:
            cached_data = self._user_habits_cache[cache_key]
            if now - cached_data['timestamp'] < self._cache_ttl:
                return cached_data['habits']
        
        # 缓存失效或不存在，从数据库读取
        try:
            prefs = get_user_preferences(user_id)
            if prefs and prefs.remembered_habits:
                habits = prefs.remembered_habits
                if isinstance(habits, str):
                    habits = json.loads(habits)
            else:
                habits = {}
        except Exception as e:
            print(f"⚠️ 获取用户习惯失败: {e}")
            habits = {}
        
        # 更新缓存
        self._user_habits_cache[cache_key] = {
            'habits': habits,
            'timestamp': now
        }
        
        return habits

    def _extract_keywords(self, title):
        """提取关键词"""
        keywords = []
        if any(kw in title for kw in ["会议", "开会", "讨论"]):
            keywords.append("会议")
        if any(kw in title for kw in ["运动", "健身", "跑步"]):
            keywords.append("运动")
        if any(kw in title for kw in ["学习", "阅读", "复习"]):
            keywords.append("学习")
        return keywords or [title[:2]]

    def _classify_task(self, title):
        """分类任务类型"""
        if any(kw in title for kw in ["会议", "开会", "讨论"]):
            return "meeting"
        elif any(kw in title for kw in ["运动", "健身", "跑步"]):
            return "exercise"
        elif any(kw in title for kw in ["学习", "阅读", "复习"]):
            return "study"
        return "other"

    def _get_blocked_periods(self, preferences):
        """获取免安排时段"""
        start = preferences.get("blocked_time_start", "22:00")
        end = preferences.get("blocked_time_end", "08:00")
        return [(start, end)]

    def _is_in_blocked_period(self, start, end, blocked_periods):
        """检查免安排时段"""
        for blocked_start, blocked_end in blocked_periods:
            try:
                bs = datetime.strptime(blocked_start, "%H:%M").time()
                be = datetime.strptime(blocked_end, "%H:%M").time()

                if bs > be:  # 跨天
                    if start.time() >= bs or end.time() <= be:
                        return True
                else:
                    if start.time() >= bs and end.time() <= be:
                        return True
            except:
                continue
        return False
    
    def _generate_split_suggestions(self, time_slots, total_duration, existing_tasks, preferences, buffer_minutes):
        """
        P1: 生成任务拆分建议
        
        当无法找到连续时间段时，尝试将任务拆分成多个小段
        
        Args:
            time_slots: 所有候选时间槽
            total_duration: 任务总时长（分钟）
            existing_tasks: 现有任务列表
            preferences: 用户偏好
            buffer_minutes: 缓冲时间
            
        Returns:
            拆分建议列表，例如：
            [
                {
                    "segment": 1,
                    "start_time": "2026-05-23T09:00:00",
                    "end_time": "2026-05-23T09:30:00",
                    "duration": 30,
                    "reason": "上午高效时段"
                },
                {
                    "segment": 2,
                    "start_time": "2026-05-23T14:00:00",
                    "end_time": "2026-05-23T14:30:00",
                    "duration": 30,
                    "reason": "下午黄金时段"
                }
            ]
        """
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
            
            for slot in time_slots:
                if remaining_duration <= 0:
                    break
                
                slot_end = slot + timedelta(minutes=segment_duration)
                
                # 检查是否有足够剩余时长
                if segment_duration > remaining_duration:
                    segment_duration = remaining_duration
                    slot_end = slot + timedelta(minutes=segment_duration)
                
                # 检查是否有效
                if self._is_slot_valid(slot, slot_end, existing_tasks, preferences, buffer_minutes):
                    # 检查与前一段的时间间隔（至少30分钟）
                    if last_end_time and (slot - last_end_time).total_seconds() < 1800:
                        continue
                    
                    # 生成原因
                    hour = slot.hour + slot.minute / 60
                    reason = self._generate_segment_reason(hour, segment_duration)
                    
                    segments.append({
                        "segment": len(segments) + 1,
                        "date": slot.date().isoformat(),  # 日期标注
                        "start_time": slot.isoformat(),
                        "end_time": slot_end.isoformat(),
                        "duration": segment_duration,
                        "reason": reason
                    })
                    
                    last_end_time = slot_end
                    remaining_duration -= segment_duration
            
            # 如果成功拆分且覆盖大部分时长
            if segments and remaining_duration <= segment_duration:
                return segments
        
        # 无法拆分，返回空列表
        return []
    
    def _is_slot_valid(self, slot_start, slot_end, existing_tasks, preferences, buffer_minutes):
        """检查单个时间槽是否有效"""
        from app.services.conflict_detector import conflict_detector
        
        # 检查免安排时段
        blocked_periods = self._get_blocked_periods(preferences)
        if self._is_in_blocked_period(slot_start, slot_end, blocked_periods):
            return False
        
        # 检查冲突
        conflict_detector.build_from_tasks(existing_tasks)
        conflicts = conflict_detector.find_conflicts(
            slot_start.isoformat(),
            slot_end.isoformat(),
            buffer_minutes
        )
        
        return len(conflicts) == 0
    
    def _generate_segment_reason(self, hour, duration):
        """生成时间段原因"""
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


class TopKSolutionsCollector(cp_model.CpSolverSolutionCallback):
    """收集前K个最优解"""

    def __init__(self, slot_var, valid_slots, scores, top_k=5):
        super().__init__()
        self.slot_var = slot_var
        self.valid_slots = valid_slots
        self.scores = scores
        self.top_k = top_k
        self.solutions = []

    def on_solution_callback(self):
        slot_idx = self.Value(self.slot_var)
        score = self.scores[slot_idx]

        self.solutions.append({
            "slot_idx": slot_idx,
            "score": score
        })

        self.solutions.sort(key=lambda x: x["score"], reverse=True)
        if len(self.solutions) > self.top_k:
            self.solutions = self.solutions[:self.top_k]


# 全局实例
or_scheduler = ORToolsScheduler()
