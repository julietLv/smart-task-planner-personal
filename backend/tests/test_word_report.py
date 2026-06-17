"""
测试 Word 报告生成器
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.report_word_generator import create_word_report
from datetime import datetime


def test_word_generation():
    """测试生成 Word 报告"""
    
    # 模拟报告数据
    report_data = {
        'title': '📊 本周工作周报',
        'warning_message': '完成率 75.0%，超时率 25.0%。',
        'start_date': '2026年05月18日',
        'end_date': '2026年05月24日',
        'generate_time': '2026年05月22日 15:30',
        'user_nickname': '彦祖',
        'assistant_nickname': '花花',
        'stats': {
            'total': 20,
            'completed': 15,
            'overdue': 5,
            'in_progress': 0,
            'completed_rate': 0.75,
            'overtime_rate': 0.25,
            'total_hours': 40.5,
            'daily_avg': 2.9,
            'priority_distribution': {'high': 5, 'medium': 10, 'low': 5},
            'type_distribution': {'work': 12, 'exercise': 5, 'reading': 3}
        },
        'charts': {
            'status_pie': '',  # 这里应该是 Base64 图片，测试时留空
            'daily_bar': ''
        },
        'daily_data': [
            {'date': '2026-05-18', 'day': '周一', 'completed': 3, 'total': 4},
            {'date': '2026-05-19', 'day': '周二', 'completed': 2, 'total': 3},
            {'date': '2026-05-20', 'day': '周三', 'completed': 4, 'total': 4},
            {'date': '2026-05-21', 'day': '周四', 'completed': 3, 'total': 5},
            {'date': '2026-05-22', 'day': '周五', 'completed': 2, 'total': 3},
            {'date': '2026-05-23', 'day': '周六', 'completed': 1, 'total': 1},
            {'date': '2026-05-24', 'day': '周日', 'completed': 0, 'total': 0},
        ],
        'habits': {
            'habit_completion': {
                'exercise': {'completed': 4, 'total': 5, 'rate': 0.8},
                'reading': {'completed': 2, 'total': 5, 'rate': 0.4},
                'early_rise': {'completed': 5, 'total': 7, 'rate': 0.71}
            },
            'consistency_score': 0.75
        },
        'llm_suggestions': '''1. ⏰ 建议预留15%缓冲时间，避免时间偏差
2. 📝 高优先级任务优先安排在高效率时段
3. 💪 早起任务完成率较低，建议设置更早闹钟''',
        'highlights': ['完成了 15 个任务', '早起任务完成率良好'],
        'issues': ['超时率 25.0% 偏高'],
        'improvements': ['合理分配时间，避免任务堆积'],
        'next_report_date': '2026年05月29日'
    }
    
    print("🧪 开始测试 Word 报告生成...")
    
    try:
        # 生成 Word 文档
        word_content = create_word_report(report_data)
        
        # 保存到文件
        output_path = "test_weekly_report.docx"
        with open(output_path, 'wb') as f:
            f.write(word_content)
        
        print(f"✅ Word 报告生成成功!")
        print(f"📄 文件大小: {len(word_content)} bytes")
        print(f"💾 已保存到: {output_path}")
        print("\n请打开生成的文件检查格式是否正确")
        
        return True
        
    except Exception as e:
        print(f"❌ Word 报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_word_generation()
    sys.exit(0 if success else 1)
