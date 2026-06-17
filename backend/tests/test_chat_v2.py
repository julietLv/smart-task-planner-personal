"""
测试 chat_router_v2 - 重构版聊天接口

测试所有已迁移的意图
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8080"
API_ENDPOINT = f"{BASE_URL}/api/chat/v2/send"


def test_chat(message: str, user_id: int = 1) -> dict:
    """发送测试消息"""
    payload = {
        "message": message,
        "user_id": user_id
    }
    
    print(f"\n{'='*70}")
    print(f"📨 测试: {message}")
    print(f"{'='*70}")
    
    try:
        # ⭐ 增加超时时间到 60 秒
        response = requests.post(API_ENDPOINT, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 状态码: {response.status_code}")
            print(f"🎯 意图: {result.get('intent', 'N/A')}")
            print(f"✨ 成功: {result.get('success', False)}")
            print(f"\n💬 AI回复:\n{result.get('reply', '无回复')}")
            
            # 如果有结构化数据，显示关键信息
            if result.get('data'):
                print(f"\n📊 结构化数据:")
                # 只显示前 500 字符，避免输出过长
                data_str = json.dumps(result['data'], ensure_ascii=False, indent=2)
                print(data_str[:500])
                if len(data_str) > 500:
                    print("... (数据过长，已截断)")
            
            return result
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"响应: {response.text}")
            return None
    
    except requests.exceptions.Timeout:
        print(f"⏰ 请求超时（60秒）")
        return None
    except requests.exceptions.ConnectionError:
        print(f"🔌 连接失败，请确保后端服务正在运行")
        return None
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def run_all_tests():
    """运行所有测试用例"""
    print("\n" + "=" * 70)
    print("🚀 开始测试 Chat Router V2 (ActionExecutor 架构)")
    print("=" * 70)

    test_cases = [
        # 测试 1: 查询今日任务
        {
            "name": "查询今日任务",
            "message": "今天我有什么任务",
            "expected_intent": "query_today_tasks"
        },
        
        # 测试 2: 分析工作负载
        {
            "name": "分析本周工作负载",
            "message": "分析本周工作负载",
            "expected_intent": "analyze_workload"
        },
        
        # 测试 3: 查询空闲时间
        {
            "name": "查询明天空闲时间",
            "message": "明天有空吗",
            "expected_intent": "query_free_time"
        },
        
        # 测试 4: 生成工作报告
        {
            "name": "生成本周报告",
            "message": "生成本周工作报告",
            "expected_intent": "generate_report"
        },
        
        # 测试 5: 日常聊天
        {
            "name": "日常聊天",
            "message": "你好",
            "expected_intent": "chat"
        },
        
        # ⭐ 测试 6: 添加任务（多轮对话）
        {
            "name": "添加任务 - 第一轮：提交信息",
            "message": "明天下午3点开会，预计1小时",
            "expected_intent": "chat",  # 第一轮返回 chat，等待确认
            "is_multi_turn": True,
            "next_message": "确认"  # 第二轮消息
        },
        
        # ⭐ 测试 7: 修改任务
        {
            "name": "修改任务优先级",
            "message": "把开会的优先级改为高",
            "expected_intent": "modify_task"
        },
        
        # ⭐ 测试 8: 删除任务
        {
            "name": "删除任务",
            "message": "删除开会任务",
            "expected_intent": "delete_task"
        },
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n{'#'*70}")
        print(f"测试 {i}/{len(test_cases)}: {test_case['name']}")
        print(f"{'#'*70}")
        
        result = test_chat(test_case['message'])
        
        if result:
            success = result.get('success', False)
            intent_match = result.get('intent') == test_case['expected_intent']
            
            test_result = {
                "name": test_case['name'],
                "message": test_case['message'],
                "success": success,
                "intent_match": intent_match,
                "actual_intent": result.get('intent'),
                "expected_intent": test_case['expected_intent']
            }
            
            results.append(test_result)
            
            if success and intent_match:
                print(f"\n✅ 测试通过")
                
                # ⭐ 如果是多轮对话，执行第二轮
                if test_case.get('is_multi_turn') and test_case.get('next_message'):
                    print(f"\n🔄 执行第二轮对话: '{test_case['next_message']}'")
                    second_result = test_chat(test_case['next_message'])
                    
                    if second_result and second_result.get('success'):
                        print(f"✅ 多轮对话测试完全通过！")
                        print(f"   最终意图: {second_result.get('intent')}")
                    else:
                        print(f"⚠️ 第二轮对话失败")
            else:
                print(f"\n⚠️ 测试部分通过")
                if not success:
                    print(f"   - 执行失败")
                if not intent_match:
                    print(f"   - 意图不匹配: 期望={test_case['expected_intent']}, 实际={result.get('intent')}")
        else:
            results.append({
                "name": test_case['name'],
                "success": False,
                "error": "请求失败"
            })
            print(f"\n❌ 测试失败")

    # 打印测试总结
    print_summary(results)


def print_summary(results: list):
    """打印测试总结"""
    print(f"\n\n{'=' * 70}")
    print("📊 测试总结")
    print(f"{'=' * 70}")

    total = len(results)
    passed = sum(1 for r in results if r.get('success') and r.get('intent_match'))
    partial = sum(1 for r in results if r.get('success') and not r.get('intent_match'))
    failed = sum(1 for r in results if not r.get('success'))

    print(f"\n总测试数: {total}")
    print(f"✅ 完全通过: {passed}")
    print(f"⚠️  部分通过: {partial}")
    print(f"❌ 失败: {failed}")
    print(f"\n通过率: {(passed / total * 100):.1f}%")

    print(f"\n详细结果:")
    for i, result in enumerate(results, 1):
        status = "✅" if result.get('success') and result.get('intent_match') else \
            "⚠️ " if result.get('success') else "❌"
        print(f"  {i}. {status} {result['name']}")
        if result.get('actual_intent'):
            print(f"     意图: {result['actual_intent']}")

    print(f"\n{'=' * 70}\n")


if __name__ == "__main__":
    print("⏳ 请确保后端服务正在运行 (http://localhost:8080)")
    input("按 Enter 键开始测试...")

    run_all_tests()
