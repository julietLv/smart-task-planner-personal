"""
周报建议生成器 - LLM + 降级策略
"""
from typing import Dict, Any


async def generate_suggestions(stats: Dict[str, Any], habits: Dict[str, Any]) -> str:
    """
    生成个性化建议（含降级策略）

    Args:
        stats: 统计数据
        habits: 习惯数据

    Returns:
        Markdown 格式的建议文本
    """
    try:
        # 正常流程：调用 LLM
        from app.services.llm_service import get_deepseek_client

        client = get_deepseek_client()

        prompt = f"""你是用户的私人助手，请根据以下数据生成个性化建议：

【核心数据】
- 完成率：{stats.get('completed_rate', 0) * 100:.1f}%
- 超时率：{stats.get('overtime_rate', 0) * 100:.1f}%
- 总任务数：{stats.get('total', 0)}个
- 已超时：{stats.get('overdue', 0)}个

【习惯追踪】
{habits}

请生成3-5条具体可执行的建议，要求：
1. 每条建议不超过60字
2. 使用emoji增加可读性
3. 针对数据中的问题给出具体解决方案
4. 语气亲切鼓励

格式示例：
1. ⏰ 建议预留15%缓冲时间，避免时间偏差
2. 📝 高优先级任务优先安排在高效率时段
3. 💪 早起任务完成率较低，建议设置更早闹钟
"""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300,
            timeout=15
        )

        suggestions = response.choices[0].message.content.strip()
        print(f"✅ LLM 建议生成成功")
        return suggestions

    except Exception as e:
        print(f"⚠️ LLM 建议生成失败: {e}")

        # 降级策略：使用规则建议
        return generate_rule_based_suggestions(stats, habits)


def generate_rule_based_suggestions(stats: Dict[str, Any], habits: Dict[str, Any]) -> str:
    """
    规则建议（降级方案）
    """
    suggestions = []

    overtime_rate = stats.get('overtime_rate', 0)
    completed_rate = stats.get('completed_rate', 0)
    time_deviation = stats.get('time_deviation_rate', 0)

    # 超时率建议
    if overtime_rate > 0.6:
        suggestions.append("⚠️ **紧急**：超时率过高，建议下周减少30%任务量，优先处理积压任务")
    elif overtime_rate > 0.4:
        suggestions.append("📊 **注意**：超时率偏高，建议合理分配时间，避免任务堆积")

    # 完成率建议
    if completed_rate < 0.3:
        suggestions.append("💪 **改进**：完成率较低，建议聚焦高优先级任务，推迟低优先级任务")

    # 时间偏差建议
    if time_deviation > 0.15:
        suggestions.append("⏰ **时间管理**：实际用时超出计划，建议为每个任务预留15%缓冲时间")

    # 习惯建议
    habit_completion = habits.get('habit_completion', {})
    if habit_completion:
        for habit, data in habit_completion.items():
            if data.get('rate', 1) < 0.6:
                habit_name = {'exercise': '运动', 'reading': '阅读', 'early_rise': '早起', 'study': '学习'}.get(habit,
                                                                                                                habit)
                suggestions.append(f" **{habit_name}**：完成率仅{data['rate'] * 100:.0f}%，建议制定更具体的执行计划")

    # 默认建议
    if not suggestions:
        suggestions.append("✅ **本周表现良好**，继续保持当前节奏！")
        suggestions.append("💡 可以尝试增加一些挑战性的任务，提升效率")

    # 格式化输出
    result = "### 个性化建议\n\n"
    for idx, suggestion in enumerate(suggestions, 1):
        result += f"{idx}. {suggestion}\n\n"

    return result
