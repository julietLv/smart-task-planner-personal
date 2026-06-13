"""测试DeepSeek API解析功能"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.llm_service import parse_task
import json


def test_parse():
    """测试自然语言解析"""
    print("\n" + "=" * 60)
    print("🧪 测试 DeepSeek API 解析功能")
    print("=" * 60)

    test_cases = [
        "明天下午2点写报告",
        "周三前完成数学作业，预计2小时，优先级高",
        "本周五之前写完项目报告，大概需要3小时，很重要",
        "阅读《Python编程》这本书"
    ]

    for i, test_input in enumerate(test_cases, 1):
        print(f"\n{'─' * 60}")
        print(f"测试 {i}: {test_input}")
        print(f"{'─' * 60}")

        result = parse_task(test_input)

        print(f"✅ 解析结果:")
        print(f"   标题: {result['title']}")
        print(f"   截止时间: {result.get('deadline', '未指定')}")
        print(f"   时长: {result.get('duration', '未指定')} 分钟")
        print(f"   优先级: {result.get('priority', 'medium')}")

        if 'error' in result:
            print(f"   ⚠️ 错误: {result['error']}")

    print("\n" + "=" * 60)
    print("✅ 所有测试完成!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        test_parse()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
