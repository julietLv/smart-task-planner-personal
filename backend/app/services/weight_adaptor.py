"""
动态权重调整服务 - 基于用户反馈自动调整评分维度权重

核心功能：
1. 分析用户反馈历史（接受/拒绝/修改）
2. 识别用户对各个评分维度的敏感度
3. 自动调整 scoring_weights.yaml 中的权重配置
4. 支持A/B测试和渐进式调整

设计理念：
- 数据驱动：基于真实反馈数据，而非主观猜测
- 渐进式：权重变化不会太剧烈，避免系统行为突变
- 可解释：每次调整都有明确的理由和数据支撑
"""
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.models.database import get_connection, DATABASE_TYPE


class WeightAdaptor:
    """权重适配器 - 动态调整评分维度权重"""

    def __init__(self):
        self.config_path = Path(__file__).parent.parent.parent / "config" / "scoring_weights.yaml"
        self.min_weight = 0.02  # 最小权重（防止某个维度完全失效）
        self.max_weight = 0.50  # 最大权重（防止某个维度主导）
        self.adjustment_step = 0.05  # 每次调整步长（5%）

    def load_current_weights(self) -> Dict:
        """加载当前权重配置"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def save_weights(self, config: Dict):
        """保存权重配置"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        print(f"✅ 权重配置已更新")

    def analyze_feedback_patterns(self, user_id: int = 1, days: int = 30) -> Dict:
        """
        分析用户反馈模式

        Args:
            user_id: 用户ID
            days: 分析天数

        Returns:
            反馈模式分析结果
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            placeholder = "%s" if DATABASE_TYPE == "mysql" else "?"

            # 计算起始日期
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')

            # 查询反馈统计
            cursor.execute(f"""
                SELECT 
                    action,
                    feedback_type,
                    COUNT(*) as count,
                    AVG(confidence_score) as avg_confidence
                FROM user_feedback 
                WHERE user_id = {placeholder} AND created_at >= {placeholder}
                GROUP BY action, feedback_type
                ORDER BY count DESC
            """, (user_id, start_date))

            rows = cursor.fetchall()
            conn.close()

            # 整理统计数据
            stats = {
                "total_feedback": sum(row["count"] for row in rows),
                "by_action": {},
                "by_type": {},
                "action_type_matrix": {}
            }

            for row in rows:
                action = row["action"]
                feedback_type = row["feedback_type"]
                count = row["count"]

                # 按动作统计
                if action not in stats["by_action"]:
                    stats["by_action"][action] = 0
                stats["by_action"][action] += count

                # 按类型统计
                if feedback_type not in stats["by_type"]:
                    stats["by_type"][feedback_type] = 0
                stats["by_type"][feedback_type] += count

                # 动作-类型矩阵
                if feedback_type not in stats["action_type_matrix"]:
                    stats["action_type_matrix"][feedback_type] = {}
                stats["action_type_matrix"][feedback_type][action] = count

            # 计算接受率
            accepted = stats["by_action"].get("accepted", 0)
            rejected = stats["by_action"].get("rejected", 0)
            modified = stats["by_action"].get("modified", 0)

            total_decisions = accepted + rejected + modified
            acceptance_rate = (accepted / total_decisions) if total_decisions > 0 else 0

            stats["acceptance_rate"] = round(acceptance_rate, 2)
            stats["period_days"] = days

            print(f"📊 反馈分析: 总反馈={stats['total_feedback']}, 接受率={acceptance_rate:.0%}")

            return stats

        except Exception as e:
            print(f"❌ 分析反馈模式失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "total_feedback": 0,
                "acceptance_rate": 0.0,
                "error": str(e)
            }

    def calculate_weight_adjustments(self, feedback_stats: Dict) -> Dict[str, float]:
        """
        根据反馈统计计算权重调整量

        核心逻辑：
        - 如果某类反馈的拒绝率高 → 降低对应维度权重
        - 如果某类反馈的修改率高 → 说明该维度预测不准，需要调整
        - 如果整体接受率低 → 可能需要重新平衡所有权重

        Args:
            feedback_stats: 反馈统计结果

        Returns:
            各维度的权重调整量（正数表示增加，负数表示减少）
        """
        adjustments = {}

        # 映射反馈类型到评分维度
        type_to_dimension = {
            "schedule_recommendation": ["time_quality", "load_balance"],
            "conflict_resolution": ["priority", "urgency"],
            "priority_suggestion": ["priority"],
            "time_slot_preference": ["time_quality"],
            "habit_match_feedback": ["habit_match"]
        }

        matrix = feedback_stats.get("action_type_matrix", {})

        for feedback_type, actions in matrix.items():
            dimensions = type_to_dimension.get(feedback_type, [])

            accepted = actions.get("accepted", 0)
            rejected = actions.get("rejected", 0)
            modified = actions.get("modified", 0)

            total = accepted + rejected + modified
            if total == 0:
                continue

            rejection_rate = rejected / total
            modification_rate = modified / total

            # 如果拒绝率高，降低相关维度权重
            if rejection_rate > 0.4:
                for dim in dimensions:
                    current_adj = adjustments.get(dim, 0)
                    adjustments[dim] = current_adj - self.adjustment_step * rejection_rate

            # 如果修改率高，说明预测不准，需要微调
            if modification_rate > 0.3:
                for dim in dimensions:
                    current_adj = adjustments.get(dim, 0)
                    adjustments[dim] = current_adj - self.adjustment_step * modification_rate * 0.5

            # 如果接受率高，可以适当增加权重（强化学习）
            if accepted / total > 0.8 and total > 5:
                for dim in dimensions:
                    current_adj = adjustments.get(dim, 0)
                    adjustments[dim] = current_adj + self.adjustment_step * 0.3

        print(f"🔧 计算权重调整: {adjustments}")

        return adjustments

    def apply_adjustments(self, adjustments: Dict[str, float], user_id: int = 1) -> Dict:
        """
        应用权重调整

        Args:
            adjustments: 各维度的调整量
            user_id: 用户ID（用于日志）

        Returns:
            调整后的权重配置
        """
        try:
            # 加载当前配置
            config = self.load_current_weights()
            dimensions = config["dimensions"]

            # 记录调整前的权重
            old_weights = {name: dim["weight"] for name, dim in dimensions.items()}

            # 应用调整
            for dim_name, adjustment in adjustments.items():
                if dim_name not in dimensions:
                    print(f"⚠️ 维度 '{dim_name}' 不存在，跳过")
                    continue

                old_weight = dimensions[dim_name]["weight"]
                new_weight = old_weight + adjustment

                # 限制在合理范围内
                new_weight = max(self.min_weight, min(self.max_weight, new_weight))

                dimensions[dim_name]["weight"] = round(new_weight, 3)

                print(f"   {dim_name}: {old_weight:.3f} → {new_weight:.3f} ({adjustment:+.3f})")

            # 归一化：确保总权重 = 1.0
            total_weight = sum(dim["weight"] for dim in dimensions.values() if dim.get("enabled", True))

            if abs(total_weight - 1.0) > 0.01:
                print(f"⚖️ 归一化权重（当前总和: {total_weight:.3f}）")

                # 按比例缩放
                scale_factor = 1.0 / total_weight
                for dim_name in dimensions:
                    if dimensions[dim_name].get("enabled", True):
                        dimensions[dim_name]["weight"] = round(
                            dimensions[dim_name]["weight"] * scale_factor,
                            3
                        )

                # 验证
                new_total = sum(dim["weight"] for dim in dimensions.values() if dim.get("enabled", True))
                print(f"   归一化后总和: {new_total:.3f}")

            # 保存配置
            self.save_weights(config)

            # 记录调整历史（可选：存数据库）
            self._log_adjustment_history(old_weights, adjustments, user_id)

            return config

        except Exception as e:
            print(f"❌ 应用权重调整失败: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _log_adjustment_history(self, old_weights: Dict, adjustments: Dict, user_id: int):
        """记录权重调整历史（简化版：打印日志）"""
        print(f"\n📝 权重调整记录:")
        print(f"   用户ID: {user_id}")
        print(f"   时间: {datetime.now().isoformat()}")
        print(f"   调整详情:")
        for dim_name, adjustment in adjustments.items():
            if abs(adjustment) > 0.001:
                print(f"     - {dim_name}: {adjustment:+.3f}")
        print()

    def auto_adjust_weights(self, user_id: int = 1, days: int = 30, dry_run: bool = False) -> Dict:
        """
        自动调整权重（主入口函数）

        Args:
            user_id: 用户ID
            days: 分析过去多少天的反馈
            dry_run: 是否仅模拟（不实际保存）

        Returns:
            调整结果
        """
        print(f"\n{'=' * 60}")
        print(f"🔄 开始自动权重调整（用户 {user_id}）")
        print(f"{'=' * 60}\n")

        # 1. 分析反馈模式
        print("步骤1: 分析反馈模式...")
        feedback_stats = self.analyze_feedback_patterns(user_id, days)

        if feedback_stats["total_feedback"] < 10:
            print(f"⚠️ 反馈数据不足（{feedback_stats['total_feedback']}条），跳过调整")
            return {
                "success": False,
                "reason": "反馈数据不足",
                "feedback_count": feedback_stats["total_feedback"]
            }

        # 2. 计算调整量
        print("\n步骤2: 计算权重调整量...")
        adjustments = self.calculate_weight_adjustments(feedback_stats)

        if not adjustments:
            print("ℹ️ 无需调整权重")
            return {
                "success": True,
                "reason": "无需调整",
                "current_weights": self.load_current_weights()["dimensions"]
            }

        # 3. 应用调整
        if dry_run:
            print("\n步骤3: [模拟运行] 显示预期调整...")
            config = self.load_current_weights()
            for dim_name, adjustment in adjustments.items():
                if dim_name in config["dimensions"]:
                    old_weight = config["dimensions"][dim_name]["weight"]
                    new_weight = max(self.min_weight, min(self.max_weight, old_weight + adjustment))
                    print(f"   {dim_name}: {old_weight:.3f} → {new_weight:.3f}")

            return {
                "success": True,
                "dry_run": True,
                "adjustments": adjustments,
                "feedback_stats": feedback_stats
            }
        else:
            print("\n步骤3: 应用权重调整...")
            new_config = self.apply_adjustments(adjustments, user_id)

            print(f"\n✅ 权重调整完成！")

            return {
                "success": True,
                "adjustments": adjustments,
                "new_weights": new_config["dimensions"],
                "feedback_stats": feedback_stats
            }


# 全局实例
weight_adaptor = WeightAdaptor()


def auto_adjust_weights_endpoint(user_id: int = 1, days: int = 30, dry_run: bool = False) -> Dict:
    """
    供路由调用的便捷函数

    Args:
        user_id: 用户ID
        days: 分析天数
        dry_run: 是否仅模拟

    Returns:
        调整结果
    """
    return weight_adaptor.auto_adjust_weights(user_id, days, dry_run)
