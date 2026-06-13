"""
周报模板引擎 - Jinja2 + LLM 降级策略
"""
from jinja2 import Template
from typing import Dict, Any
from datetime import datetime

# Markdown 报告模板
MARKDOWN_TEMPLATE = """# {{ title }}

> **{{ warning_message }}**
> 
> **报告周期**：{{ start_date }} 至 {{ end_date }}  
> **生成时间**：{{ generate_time }}  
> **用户**：{{ user_nickname }} | **助手**：{{ assistant_nickname }}

---

## 📊 执行摘要

###  本周亮点
{% for highlight in highlights %}
- {{ highlight }}
{% endfor %}

### ⚠️ 关键问题
{% for issue in issues %}
- {{ issue }}
{% endfor %}

### 💡 改进方向
{% for suggestion in improvements %}
- {{ suggestion }}
{% endfor %}

---

## 一、 工作概览

### 1.1 核心数据

| 指标 | 数值 | 说明 |
|------|------|------|
| **总任务数** | {{ stats.total }} 个 | 本周所有任务 |
| **已完成** | {{ stats.completed }} 个 ({{ (stats.completed_rate * 100) | round(1) }}%) | 成功完成的任务 |
| **进行中** | {{ stats.in_progress }} 个 ({{ (stats.in_progress / stats.total * 100) | round(1) if stats.total > 0 else 0 }}%) | 待完成的任务 |
| **已超时** | {{ stats.overdue }} 个 ({{ (stats.overtime_rate * 100) | round(1) }}%) | 超过截止时间的任务 |
| **总工作时长** | {{ stats.total_hours }} 小时 | 预计总工作时间 |
| **日均任务数** | {{ stats.daily_avg }} 个 | 平均每天任务数 |

### 1.2 任务状态分布

<p align="center">
<img src="{{ charts.status_pie }}" width="400" alt="任务状态分布" />
</p>

---

## 二、 每日完成趋势

### 2.1 趋势图表

<p align="center">
<img src="{{ charts.daily_bar }}" width="450" alt="每日完成趋势" />
</p>

### 2.2 详细数据

| 日期 | 星期 | 完成任务 | 总任务 | 完成率 |
|------|------|---------|--------|--------|
{% for day in daily_data -%}
| {{ day.date }} | {{ day.day }} | {{ day.completed }} | {{ day.total }} | {{ (day.completed / day.total * 100) | round(1) if day.total > 0 else 0 }}% |
{% endfor %}

---

## 三、 任务分析

### 3.1 优先级分布

{% for priority, count in stats.priority_distribution.items() %}
- **{{ {'high': '高优先级', 'medium': '中优先级', 'low': '低优先级'}[priority] }}**: {{ count }} 个
{% endfor %}

### 3.2 任务类型分布

{% for type_name, count in stats.type_distribution.items() %}
- **{{ type_name }}**: {{ count }} 个
{% endfor %}

---

## 四、 习惯追踪

{% if habits.habit_completion %}
### 4.1 习惯完成情况

{% for habit, data in habits.habit_completion.items() %}
- **{{ {'exercise': '运动', 'reading': '阅读', 'early_rise': '早起', 'study': '学习'}[habit] }}**: {{ data.completed }}/{{ data.total }} ({{ (data.rate * 100) | round(0) }}%)
{% endfor %}
{% else %}
### 4.1 习惯完成情况
- 本周暂无习惯任务记录
{% endif %}

### 4.2 一致性评分
- **评分**: {{ (habits.consistency_score * 100) | round(0) }}%
- **说明**: 基于按时完成率计算

---

## 五、 个性化建议

{{ llm_suggestions }}

---

## 六、 下周计划建议

### 6.1 待完成任务
{% if stats.overdue > 0 %}
⚠️ 有 {{ stats.overdue }} 个任务已超时，建议优先处理：
{% endif %}

### 6.2 负载建议
{% if stats.overtime_rate > 0.6 %}
- **负载警告**: 本周超时率 {{ (stats.overtime_rate * 100) | round(0) }}% 过高
- **建议**: 下周任务量减少 30%，聚焦高优先级任务
{% elif stats.overtime_rate > 0.4 %}
- **负载提示**: 本周超时率 {{ (stats.overtime_rate * 100) | round(0) }}%
- **建议**: 合理分配时间，避免任务堆积
{% else %}
- **负载良好**: 本周超时率 {{ (stats.overtime_rate * 100) | round(0) }}%
- **建议**: 继续保持当前节奏
{% endif %}

---

**报告生成**: {{ assistant_nickname }} · 智能助手  
**下次报告**: {{ next_report_date }}
"""


def render_markdown_report(data: Dict[str, Any]) -> str:
    """
    渲染 Markdown 报告

    Args:
        data: 报告数据字典

    Returns:
        Markdown 格式的字符串
    """
    template = Template(MARKDOWN_TEMPLATE)
    return template.render(**data)


def determine_report_tone(stats: Dict[str, Any]) -> Dict[str, str]:
    """
    根据数据自动调整报告语气和标题
    """
    overtime_rate = stats.get('overtime_rate', 0)
    completed_rate = stats.get('completed_rate', 0)

    if overtime_rate > 0.6:
        return {
            "tone": "urgent",
            "title": "⚠️ 本周工作周报（紧急）",
            "warning": f"超时率 {overtime_rate * 100:.0f}% 远超正常水平，需立即调整！",
            "color": "#F44336"
        }
    elif overtime_rate > 0.4:
        return {
            "tone": "warning",
            "title": " 本周工作周报（需关注）",
            "warning": f"超时率达到 {overtime_rate * 100:.0f}%，建议优化时间管理。",
            "color": "#FF9800"
        }
    elif completed_rate > 0.8:
        return {
            "tone": "excellent",
            "title": "🎉 本周工作周报（优秀）",
            "warning": f"完成率高达 {completed_rate * 100:.0f}%，表现优秀！",
            "color": "#4CAF50"
        }
    else:
        return {
            "tone": "normal",
            "title": "📊 本周工作周报",
            "warning": f"完成率 {completed_rate * 100:.0f}%，超时率 {overtime_rate * 100:.0f}%。",
            "color": "#2196F3"
        }
