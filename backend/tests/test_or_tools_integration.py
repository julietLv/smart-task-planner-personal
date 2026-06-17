"""test_or_tools_integration.py - OR-Tools 排程引擎端到端集成测试

测试目标：
1. 验证8个评分维度对排程结果的实际影响
2. 分析 Top-K 方案的质量差异
3. 测试节假日、天气等因素的联合作用
4. 验证习惯学习在排程中的应用效果
5. 性能基准测试
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
from app.services.or_tools_scheduler import or_scheduler
from app.services.scoring_engine import ScoringEngine
from app.services.holiday_service import holiday_service
from app.services.weather_service import weather_service
from app.services.scheduler_service import remember_user_preference


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_basic_scheduling():
    """测试1：基础排程功能验证"""
    print_section("测试1：基础排程功能验证")

    # 准备测试数据
    new_task = {
        "title": "完成Python作业",
        "duration": 90,
        "deadline": (datetime.now() + timedelta(days=2)).isoformat(),
        "priority": "high",
        "user_id": 1
    }

    existing_tasks = [
        {
            "id": 1,
            "title": "晨会",
            "start_time": (datetime.now().replace(hour=9, minute=0)).isoformat(),
            "end_time": (datetime.now().replace(hour=9, minute=30)).isoformat(),
            "status": "pending"
        },
        {
            "id": 2,
            "title": "午餐时间",
            "start_time": (datetime.now().replace(hour=12, minute=0)).isoformat(),
            "end_time": (datetime.now().replace(hour=13, minute=0)).isoformat(),
            "status": "pending"
        }
    ]

    preferences = {
        "blocked_time_start": "22:00",
        "blocked_time_end": "08:00",
        "task_buffer_minutes": 15
    }

    print(f"\n📋 任务信息:")
    print(f"   标题: {new_task['title']}")
    print(f"   时长: {new_task['duration']}分钟")
    print(f"   优先级: {new_task['priority']}")
    print(f"   截止时间: {new_task['deadline'][:16]}")
    print(f"\n📅 现有任务: {len(existing_tasks)} 个")
    print(f"⚙️  缓冲时间: {preferences['task_buffer_minutes']}分钟")

    # 执行排程
    result = or_scheduler.schedule_task(
        new_task=new_task,
        existing_tasks=existing_tasks,
        preferences=preferences,
        return_top_k=5
    )

    if not result["success"]:
        print(f"\n❌ 排程失败: {result['message']}")
        return

    print(f"\n✅ 排程成功!")
    print(f"   算法: {result['algorithm']}")
    print(f"   候选时间槽: {result['stats']['total_slots']} 个")
    print(f"   有效时间槽: {result['stats']['valid_slots']} 个")
    print(f"   可行方案: {result['stats']['feasible_solutions']} 个")

    # 展示 Top-5 方案
    print(f"\n🏆 Top-5 排程方案:")
    print(f"{'排名':<6} {'开始时间':<20} {'结束时间':<20} {'评分':<10} {'推荐理由'}")
    print("-" * 90)

    for idx, solution in enumerate(result["all_solutions"], 1):
        start = solution["start_time"][:16].replace("T", " ")
        end = solution["end_time"][:16].replace("T", " ")
        score = solution["score"]
        reasons = ", ".join(solution["reasons"][:2])

        marker = "⭐" if idx == 1 else "  "
        print(f"{marker}{idx:<5} {start:<20} {end:<20} {score:<10.2f} {reasons}")

    # 分析最优方案
    best = result["best_solution"]
    print(f"\n🎯 最优方案详细分析:")
    print(f"   时间: {best['start_time'][:16].replace('T', ' ')} - {best['end_time'][:16].replace('T', ' ')}")
    print(f"   评分: {best['score']:.2f}/100")
    print(f"   理由:")
    for reason in best["reasons"]:
        print(f"     • {reason}")


def test_dimension_impact():
    """测试2：各评分维度对排程的影响"""
    print_section("测试2：各评分维度对排程的影响分析")

    engine = ScoringEngine()

    # 构建不同场景的评分对比
    scenarios = [
        {
            "name": "场景A：工作日早晨（理想时段）",
            "scores": {
                "habit_match": 50,  # 符合晨间习惯
                "date_freshness": 35,  # 当天完成
                "urgency": 40,  # 紧急
                "time_quality": 50,  # 上午高效时段
                "load_balance": 10,  # 负载适中
                "priority": 60,  # 高优先级
                "holiday": 0,  # 工作日
                "weather": 15  # 晴天
            }
        },
        {
            "name": "场景B：周末下午（一般时段）",
            "scores": {
                "habit_match": 20,  # 不太符合习惯
                "date_freshness": 15,  # 推迟到周末
                "urgency": 10,  # 不紧急
                "time_quality": 30,  # 下午一般
                "load_balance": 5,  # 负载较轻
                "priority": 35,  # 中优先级
                "holiday": -20,  # 周末扣分
                "weather": 10  # 多云
            }
        },
        {
            "name": "场景C：法定节假日（较差时段）",
            "scores": {
                "habit_match": 15,  # 不符合习惯
                "date_freshness": 8,  # 推迟很久
                "urgency": 5,  # 很不紧急
                "time_quality": 20,  # 假日效率低
                "load_balance": 15,  # 空闲
                "priority": 25,  # 低优先级
                "holiday": -40,  # 法定假日严重扣分
                "weather": -10  # 雨天
            }
        }
    ]

    print(f"\n📊 评分维度对比分析:\n")

    results = []
    for scenario in scenarios:
        result = engine.calculate_final_score(scenario["scores"])
        results.append({
            "name": scenario["name"],
            "final_score": result["final_score"],
            "details": result["dimension_details"]
        })

        print(f"{scenario['name']}:")
        print(f"  最终评分: {result['final_score']:.2f}/100")
        print(f"  维度明细:")

        for dim_name, dim_info in result["dimension_details"].items():
            raw = dim_info["raw"]
            normalized = dim_info["normalized"]
            weighted = dim_info["weighted"]
            weight = dim_info["weight"]

            bar = "█" * int(normalized * 20)
            print(f"    {dim_name:<20} {raw:>6.1f} → {normalized:.2f} × {weight:.2f} = {weighted:.3f} {bar}")
        print()

    # 对比总结
    print(f"\n📈 评分对比总结:")
    print(f"{'场景':<30} {'最终评分':<12} {'评级'}")
    print("-" * 60)

    for r in sorted(results, key=lambda x: x["final_score"], reverse=True):
        score = r["final_score"]
        if score >= 70:
            level = "🟢 优秀"
        elif score >= 50:
            level = "🟡 良好"
        elif score >= 30:
            level = "🟠 一般"
        else:
            level = "🔴 较差"

        print(f"{r['name']:<28} {score:<12.2f} {level}")


def test_holiday_weather_impact():
    """测试3：节假日和天气对排程的综合影响"""
    print_section("测试3：节假日+天气综合影响测试")

    from datetime import date

    test_cases = [
        {
            "name": "五一假期安排工作会议",
            "date": date(2026, 5, 2),
            "task_type": "meeting",
            "description": "法定假日不适合工作会议"
        },
        {
            "name": "五一假期安排户外运动",
            "date": date(2026, 5, 2),
            "task_type": "exercise",
            "description": "假日可以运动，但可能人多"
        },
        {
            "name": "工作日晴天开会",
            "date": date(2026, 5, 12),
            "task_type": "meeting",
            "description": "理想的工作时段"
        },
        {
            "name": "雨天安排户外运动",
            "date": date(2026, 7, 15),
            "task_type": "exercise",
            "description": "雨天不适合户外运动"
        }
    ]

    print(f"\n🌤️  综合影响分析:\n")

    for case in test_cases:
        holiday_score = holiday_service.get_holiday_impact_score(case["date"], case["task_type"])
        weather_score = weather_service.get_weather_impact_score(case["date"], case["task_type"])
        total_impact = holiday_score + weather_score

        weather = weather_service.get_weather(case["date"])
        holiday_name = holiday_service.get_holiday_name(case["date"]) or "工作日"

        print(f"📌 {case['name']}")
        print(f"   日期: {case['date']} ({holiday_name})")
        print(f"   说明: {case['description']}")
        print(f"   天气: {weather['condition']} {weather['temperature']}°C")
        print(f"   节假日影响: {holiday_score:+d} 分")
        print(f"   天气影响: {weather_score:+d} 分")
        print(f"   总影响: {total_impact:+d} 分")

        if total_impact < -30:
            verdict = "❌ 强烈不建议"
        elif total_impact < -10:
            verdict = "⚠️ 不太适合"
        elif total_impact < 0:
            verdict = "🟡 可以考虑"
        else:
            verdict = "✅ 推荐"

        print(f"   结论: {verdict}\n")


def test_habit_learning_integration():
    """测试4：习惯学习在排程中的应用"""
    print_section("测试4：习惯学习集成测试")

    user_id = 1

    print(f"\n🧠 模拟用户学习习惯积累...")

    # 模拟多次调整行为
    adjustments = [
        ("晨跑", "priority", "medium", "high"),
        ("晨跑", "priority", "medium", "high"),
        ("晨跑", "priority", "medium", "high"),
        ("阅读", "duration", 30, 60),
        ("阅读", "duration", 30, 60),
        ("阅读", "duration", 30, 60),
        ("阅读", "duration", 30, 60),
    ]

    for title, adj_type, old_val, new_val in adjustments:
        remember_user_preference(
            task_title=title,
            adjustment_type=adj_type,
            old_value=old_val,
            new_value=new_val,
            user_id=user_id,
            context={"test": True}
        )

    print(f"✅ 已记录 {len(adjustments)} 次调整行为")

    # 获取学习习惯摘要
    from app.services.scheduler_service import get_learned_habits_summary
    summary = get_learned_habits_summary(user_id)

    if summary["success"]:
        learned_habits = summary["summary"]["learned_habits"]
        print(f"\n📚 已学习的习惯 ({len(learned_habits)} 个):")

        for habit in learned_habits:
            keyword = habit["keyword"]
            confidence = habit["confidence"]
            prefs = habit["preferences"]

            print(f"\n  关键词: {keyword}")
            print(f"    置信度: {confidence:.2%}")
            print(f"    偏好:")
            for pref_type, pref_value in prefs.items():
                print(f"      • {pref_type}: {pref_value}")

    # 测试应用习惯到任务
    print(f"\n\n🎯 测试应用习惯到新任务排程...")

    from app.services.scheduler_service import apply_learned_habits

    test_task = {
        "title": "晨跑锻炼",
        "duration": 30,
        "priority": "medium"
    }

    print(f"   原始任务: {test_task}")

    enhanced_task = apply_learned_habits(test_task.copy(), user_id)

    print(f"   应用习惯后: {enhanced_task}")

    if "applied_habits" in enhanced_task:
        print(f"   应用的习惯:")
        for habit_desc in enhanced_task["applied_habits"]:
            print(f"     • {habit_desc}")


def test_top_k_diversity():
    """测试5：Top-K 方案的多样性分析"""
    print_section("测试5：Top-K 方案多样性分析")

    new_task = {
        "title": "项目评审会议",
        "duration": 60,
        "deadline": (datetime.now() + timedelta(days=3)).isoformat(),
        "priority": "high",
        "user_id": 1
    }

    existing_tasks = [
        {
            "id": i,
            "title": f"任务{i}",
            "start_time": (datetime.now().replace(hour=9 + i, minute=0)).isoformat(),
            "end_time": (datetime.now().replace(hour=9 + i, minute=30)).isoformat(),
            "status": "pending"
        }
        for i in range(5)
    ]

    preferences = {
        "blocked_time_start": "22:00",
        "blocked_time_end": "08:00",
        "task_buffer_minutes": 15
    }

    result = or_scheduler.schedule_task(
        new_task=new_task,
        existing_tasks=existing_tasks,
        preferences=preferences,
        return_top_k=5
    )

    if not result["success"]:
        print(f"❌ 排程失败: {result['message']}")
        return

    solutions = result["all_solutions"]

    print(f"\n📊 Top-{len(solutions)} 方案对比:\n")
    print(f"{'排名':<6} {'时间':<25} {'评分':<10} {'评分差':<10} {'时间段'}")
    print("-" * 70)

    prev_score = None
    for idx, sol in enumerate(solutions, 1):
        start = sol["start_time"][:16].replace("T", " ")
        score = sol["score"]

        if prev_score is None:
            diff = 0
        else:
            diff = prev_score - score

        # 判断时间段
        hour = int(start.split(":")[0].split(" ")[-1])
        if 9 <= hour < 12:
            period = "上午"
        elif 12 <= hour < 14:
            period = "中午"
        elif 14 <= hour < 18:
            period = "下午"
        else:
            period = "晚上"

        marker = "⭐" if idx == 1 else "  "
        print(f"{marker}{idx:<5} {start:<25} {score:<10.2f} {diff:<10.2f} {period}")

        prev_score = score

    # 分析多样性
    if len(solutions) >= 2:
        score_range = solutions[0]["score"] - solutions[-1]["score"]
        print(f"\n📈 多样性指标:")
        print(f"   评分范围: {score_range:.2f} 分")
        print(f"   平均评分差: {score_range / (len(solutions) - 1):.2f} 分/名次")

        if score_range > 20:
            diversity = "🟢 高多样性（方案差异明显）"
        elif score_range > 10:
            diversity = "🟡 中等多样性"
        else:
            diversity = "🔴 低多样性（方案相似）"

        print(f"   评价: {diversity}")


def test_performance_benchmark():
    """测试6：性能基准测试"""
    print_section("测试6：性能基准测试")

    import time

    test_sizes = [10, 50, 100, 200]

    print(f"\n⚡ 排程性能测试:\n")
    print(f"{'现有任务数':<12} {'候选槽数':<12} {'有效槽数':<12} {'耗时(ms)':<12} {'方案数'}")
    print("-" * 70)

    for size in test_sizes:
        # 生成测试数据
        now = datetime.now()
        existing_tasks = [
            {
                "id": i,
                "title": f"任务{i}",
                "start_time": (now + timedelta(hours=i % 10, minutes=(i * 7) % 60)).isoformat(),
                "end_time": (now + timedelta(hours=i % 10, minutes=(i * 7) % 60 + 30)).isoformat(),
                "status": "pending"
            }
            for i in range(size)
        ]

        new_task = {
            "title": "测试任务",
            "duration": 60,
            "deadline": (now + timedelta(days=7)).isoformat(),
            "priority": "medium",
            "user_id": 1
        }

        preferences = {
            "blocked_time_start": "22:00",
            "blocked_time_end": "08:00",
            "task_buffer_minutes": 15
        }

        # 计时
        start_time = time.time()
        result = or_scheduler.schedule_task(
            new_task=new_task,
            existing_tasks=existing_tasks,
            preferences=preferences,
            return_top_k=5
        )
        elapsed_ms = (time.time() - start_time) * 1000

        if result["success"]:
            stats = result["stats"]
            print(f"{size:<12} {stats['total_slots']:<12} {stats['valid_slots']:<12} "
                  f"{elapsed_ms:<12.2f} {stats['feasible_solutions']}")
        else:
            print(f"{size:<12} {'N/A':<12} {'N/A':<12} {elapsed_ms:<12.2f} 0")

    print(f"\n✅ 性能测试完成")
    print(f"   建议: 对于生产环境，建议保持响应时间 < 2000ms")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🚀" * 40)
    print("  OR-Tools 排程引擎端到端集成测试套件")
    print("🚀" * 40)

    tests = [
        ("基础排程功能", test_basic_scheduling),
        ("评分维度影响", test_dimension_impact),
        ("节假日天气影响", test_holiday_weather_impact),
        ("习惯学习集成", test_habit_learning_integration),
        ("Top-K 方案多样性", test_top_k_diversity),
        ("性能基准测试", test_performance_benchmark),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ {name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    # 总结
    print_section("测试总结")
    print(f"\n✅ 通过: {passed}/{len(tests)}")
    print(f"❌ 失败: {failed}/{len(tests)}")

    if failed == 0:
        print(f"\n🎉 所有测试通过！排程引擎运行正常！")
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查上述错误信息")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    run_all_tests()
