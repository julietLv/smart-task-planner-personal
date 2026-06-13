"""score_visualizer.py - 评分明细可视化工具

用途：将排程引擎的评分明细转换为前端友好的格式
"""
from typing import Dict, List


class ScoreVisualizer:
    """评分明细可视化器"""

    # 维度中文名称映射
    DIMENSION_NAMES = {
        "habit_match": "用户习惯匹配度",
        "date_freshness": "日期新鲜度",
        "urgency": "任务紧急度",
        "time_quality": "时间段质量",
        "load_balance": "任务密度平衡",
        "priority": "优先级权重",
        "holiday": "节假日效应",
        "weather": "天气因素"
    }

    # 维度图标
    DIMENSION_ICONS = {
        "habit_match": "🧠",
        "date_freshness": "📅",
        "urgency": "⚡",
        "time_quality": "⏰",
        "load_balance": "⚖️",
        "priority": "🎯",
        "holiday": "🎊",
        "weather": "🌤️"
    }

    @staticmethod
    def format_dimension_details(dimension_details: Dict) -> List[Dict]:
        """
        格式化维度明细为前端友好格式

        Args:
            dimension_details: 评分引擎返回的维度明细

        Returns:
            格式化后的列表
        """
        formatted = []

        for dim_name, details in dimension_details.items():
            if dim_name not in ScoreVisualizer.DIMENSION_NAMES:
                continue

            raw_score = details["raw"]
            normalized = details["normalized"]
            weighted = details["weighted"]
            weight = details["weight"]

            # 计算百分比条
            percentage = int(normalized * 100)

            # 确定颜色
            if normalized >= 0.7:
                color = "green"
            elif normalized >= 0.4:
                color = "yellow"
            else:
                color = "red"

            formatted.append({
                "dimension": dim_name,
                "name": ScoreVisualizer.DIMENSION_NAMES[dim_name],
                "icon": ScoreVisualizer.DIMENSION_ICONS[dim_name],
                "raw_score": round(raw_score, 2),
                "normalized": round(normalized, 4),
                "weight": round(weight, 4),
                "weighted_score": round(weighted, 4),
                "percentage": percentage,
                "color": color,
                "description": ScoreVisualizer._get_dimension_description(dim_name, raw_score)
            })

        # 按加权分数排序
        formatted.sort(key=lambda x: x["weighted_score"], reverse=True)

        return formatted

    @staticmethod
    def _get_dimension_description(dim_name: str, raw_score: float) -> str:
        """生成维度的文字描述"""

        descriptions = {
            "habit_match": [
                (50, "完全符合你的历史习惯"),
                (30, "较为符合你的习惯"),
                (15, "与你的习惯有一定偏差"),
                (0, "不符合你的习惯")
            ],
            "date_freshness": [
                (30, "今天完成，非常及时"),
                (20, "明天完成，比较及时"),
                (10, "近期完成"),
                (0, "安排得较晚")
            ],
            "urgency": [
                (40, "非常紧急，接近截止时间"),
                (25, "比较紧急"),
                (10, "有一定紧迫性"),
                (0, "时间充裕")
            ],
            "time_quality": [
                (45, "黄金时段，效率最高"),
                (30, "较好的时间段"),
                (15, "一般时间段"),
                (0, "非理想时段")
            ],
            "load_balance": [
                (10, "当天负载较轻"),
                (0, "负载适中"),
                (-10, "当天较忙"),
                (-30, "当天过载")
            ],
            "priority": [
                (60, "高优先级任务，优先安排"),
                (40, "中等优先级"),
                (20, "低优先级任务")
            ],
            "holiday": [
                (0, "工作日，无影响"),
                (-10, "周末，略有影响"),
                (-30, "节假日，不太适合")
            ],
            "weather": [
                (15, "天气良好，适合安排"),
                (0, "天气一般"),
                (-20, "天气不佳，有影响")
            ]
        }

        if dim_name not in descriptions:
            return ""

        for threshold, desc in descriptions[dim_name]:
            if raw_score >= threshold:
                return desc

        return ""

    @staticmethod
    def generate_explanation(solution: Dict) -> str:
        """
        生成排程方案的文字解释

        Args:
            solution: 排程方案（包含 score 和 dimension_details）

        Returns:
            解释文本
        """
        if "dimension_details" not in solution:
            return "评分明细不可用"

        dimensions = ScoreVisualizer.format_dimension_details(solution["dimension_details"])

        # 找出贡献最大的3个维度
        top_dimensions = dimensions[:3]

        explanation_parts = []

        for dim in top_dimensions:
            icon = dim["icon"]
            name = dim["name"]
            desc = dim["description"]

            if desc:
                explanation_parts.append(f"{icon} {name}: {desc}")

        if not explanation_parts:
            return "这是一个均衡的排程方案"

        return "；".join(explanation_parts)

    @staticmethod
    def compare_solutions(solution_a: Dict, solution_b: Dict) -> Dict:
        """
        对比两个方案的评分差异

        Args:
            solution_a: 方案A
            solution_b: 方案B

        Returns:
            对比结果
        """
        if "dimension_details" not in solution_a or "dimension_details" not in solution_b:
            return {"error": "缺少评分明细"}

        dims_a = solution_a["dimension_details"]
        dims_b = solution_b["dimension_details"]

        comparison = []

        for dim_name in dims_a.keys():
            if dim_name not in dims_b:
                continue

            score_a = dims_a[dim_name]["weighted"]
            score_b = dims_b[dim_name]["weighted"]
            diff = score_a - score_b

            comparison.append({
                "dimension": dim_name,
                "name": ScoreVisualizer.DIMENSION_NAMES.get(dim_name, dim_name),
                "score_a": round(score_a, 4),
                "score_b": round(score_b, 4),
                "difference": round(diff, 4),
                "better": "A" if diff > 0 else ("B" if diff < 0 else "相同")
            })

        return {
            "score_a": solution_a["score"],
            "score_b": solution_b["score"],
            "score_diff": round(solution_a["score"] - solution_b["score"], 2),
            "dimension_comparison": comparison
        }


# 使用示例
if __name__ == "__main__":
    # 测试数据
    sample_solution = {
        "score": 75.5,
        "dimension_details": {
            "habit_match": {
                "raw": 50,
                "normalized": 0.77,
                "weighted": 0.23,
                "weight": 0.30
            },
            "date_freshness": {
                "raw": 35,
                "normalized": 1.0,
                "weighted": 0.20,
                "weight": 0.20
            },
            "urgency": {
                "raw": 40,
                "normalized": 0.8,
                "weighted": 0.12,
                "weight": 0.15
            }
        }
    }

    visualizer = ScoreVisualizer()

    # 格式化维度明细
    formatted = visualizer.format_dimension_details(sample_solution["dimension_details"])

    print("格式化后的维度明细:")
    for dim in formatted:
        print(f"  {dim['icon']} {dim['name']}: {dim['percentage']}% ({dim['description']})")

    # 生成解释
    explanation = visualizer.generate_explanation(sample_solution)
    print(f"\n方案解释: {explanation}")
