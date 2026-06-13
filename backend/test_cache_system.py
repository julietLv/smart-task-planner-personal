"""backend/test_cache_system.py - 完整缓存系统测试脚本"""
import requests
import time
import json
from datetime import datetime


class CacheSystemTester:
    """缓存系统完整测试器"""
    
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.results = {
            "tests_passed": 0,
            "tests_failed": 0,
            "performance_data": [],
            "start_time": None
        }

    def log(self, message, level="INFO"):
        """打印日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def test_api_response(self):
        """测试1：API响应基础功能"""
        self.log("=" * 70)
        self.log("测试1：API响应基础功能", "TEST")
        self.log("=" * 70)

        try:
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/holidays/month",  # ✅ 去掉 /api 前缀
                params={"year": 2026, "month": 3}
            )
            elapsed = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ API响应成功", "PASS")
                self.log(f"   状态码: {response.status_code}")
                self.log(f"   响应时间: {elapsed:.2f}ms")
                self.log(f"   节日数量: {data['count']}")
                self.log(f"   数据示例: {data['holidays'][0] if data['holidays'] else '无'}")

                self.results["tests_passed"] += 1
                self.results["performance_data"].append({
                    "test": "API首次请求",
                    "time_ms": elapsed
                })
                return True
            else:
                self.log(f"❌ API响应失败: {response.status_code}", "FAIL")
                self.results["tests_failed"] += 1
                return False

        except Exception as e:
            self.log(f"❌ 请求异常: {str(e)}", "ERROR")
            self.results["tests_failed"] += 1
            return False

    def test_weekend_marking(self):
        """测试2：周末标记完整性"""
        self.log("\n" + "=" * 70)
        self.log("测试2：周末标记完整性", "TEST")
        self.log("=" * 70)

        try:
            # 测试3月（应该有9个周末）
            response = requests.get(
                f"{self.base_url}/holidays/month",  # ✅ 去掉 /api 前缀
                params={"year": 2026, "month": 3}
            )

            if response.status_code != 200:
                self.log("❌ API请求失败", "FAIL")
                self.results["tests_failed"] += 1
                return False

            data = response.json()
            holidays = data["holidays"]

            # 统计周末数量
            weekends = [h for h in holidays if h["name"] == "周末"]
            legal_holidays = [h for h in holidays if h["is_legal_holiday"]]

            self.log(f"✅ 3月数据分析:", "PASS")
            self.log(f"   总标记数: {len(holidays)}")
            self.log(f"   周末数量: {len(weekends)} (预期: 9)")
            self.log(f"   法定节假日: {len(legal_holidays)}")

            # 验证周末日期是否正确
            expected_weekends = [
                "2026-03-01", "2026-03-07", "2026-03-08",
                "2026-03-14", "2026-03-15", "2026-03-21",
                "2026-03-22", "2026-03-28", "2026-03-29"
            ]

            actual_weekend_dates = [h["date"] for h in weekends]
            missing = set(expected_weekends) - set(actual_weekend_dates)
            extra = set(actual_weekend_dates) - set(expected_weekends)

            if not missing and not extra:
                self.log(f"   ✅ 周末日期完全正确", "PASS")
                self.results["tests_passed"] += 1
                return True
            else:
                if missing:
                    self.log(f"   ❌ 缺失的周末: {missing}", "FAIL")
                if extra:
                    self.log(f"   ❌ 多余的周末: {extra}", "FAIL")
                self.results["tests_failed"] += 1
                return False

        except Exception as e:
            self.log(f"❌ 测试异常: {str(e)}", "ERROR")
            self.results["tests_failed"] += 1
            return False

    def test_cross_month_view(self):
        """测试3：跨月视图支持"""
        self.log("\n" + "=" * 70)
        self.log("测试3：跨月视图支持", "TEST")
        self.log("=" * 70)

        try:
            # 测试3月底到4月初的周视图
            march_response = requests.get(
                f"{self.base_url}/holidays/month",  # ✅ 去掉 /api 前缀
                params={"year": 2026, "month": 3}
            )
            april_response = requests.get(
                f"{self.base_url}/holidays/month",  # ✅ 去掉 /api 前缀
                params={"year": 2026, "month": 4}
            )

            if march_response.status_code == 200 and april_response.status_code == 200:
                march_data = march_response.json()
                april_data = april_response.json()

                # 检查3月最后几天
                march_end = [h for h in march_data["holidays"] if h["date"] >= "2026-03-28"]
                # 检查4月开始几天
                april_start = [h for h in april_data["holidays"] if h["date"] <= "2026-04-05"]

                self.log(f"✅ 跨月数据可用:", "PASS")
                self.log(f"   3月最后几天标记: {len(march_end)}")
                self.log(f"   4月开始几天标记: {len(april_start)}")

                self.results["tests_passed"] += 1
                return True
            else:
                self.log("❌ 跨月数据获取失败", "FAIL")
                self.results["tests_failed"] += 1
                return False

        except Exception as e:
            self.log(f"❌ 测试异常: {str(e)}", "ERROR")
            self.results["tests_failed"] += 1
            return False

    def test_performance_consistency(self):
        """测试4：性能一致性测试"""
        self.log("\n" + "=" * 70)
        self.log("测试4：性能一致性测试（连续10次请求）", "TEST")
        self.log("=" * 70)

        try:
            times = []
            for i in range(10):
                start_time = time.time()
                response = requests.get(
                    f"{self.base_url}/holidays/month",  # ✅ 去掉 /api 前缀
                    params={"year": 2026, "month": 5}
                )
                elapsed = (time.time() - start_time) * 1000
                times.append(elapsed)

                if response.status_code != 200:
                    self.log(f"❌ 第{i+1}次请求失败", "FAIL")
                    self.results["tests_failed"] += 1
                    return False

            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)

            self.log(f"✅ 性能测试结果:", "PASS")
            self.log(f"   平均响应时间: {avg_time:.2f}ms")
            self.log(f"   最快响应: {min_time:.2f}ms")
            self.log(f"   最慢响应: {max_time:.2f}ms")
            self.log(f"   稳定性: {(max_time - min_time):.2f}ms 波动")

            # 判断性能是否达标
            if avg_time < 500:
                self.log(f"   ✅ 性能优秀 (<500ms)", "PASS")
            elif avg_time < 1000:
                self.log(f"   ⚠️ 性能一般 (500-1000ms)", "WARN")
            else:
                self.log(f"   ❌ 性能较差 (>1000ms)", "FAIL")

            self.results["tests_passed"] += 1
            self.results["performance_data"].append({
                "test": "性能一致性",
                "avg_ms": avg_time,
                "min_ms": min_time,
                "max_ms": max_time
            })
            return True

        except Exception as e:
            self.log(f"❌ 测试异常: {str(e)}", "ERROR")
            self.results["tests_failed"] += 1
            return False

    def test_error_handling(self):
        """测试5：错误处理"""
        self.log("\n" + "=" * 70)
        self.log("测试5：错误处理", "TEST")
        self.log("=" * 70)

        error_tests = [
            {"params": {"year": 2026, "month": 13}, "desc": "无效月份(13)"},
            {"params": {"year": 2026, "month": 0}, "desc": "无效月份(0)"},
            {"params": {"year": -1, "month": 1}, "desc": "无效年份(-1)"},
        ]

        passed = 0
        for test in error_tests:
            try:
                response = requests.get(
                    f"{self.base_url}/holidays/month",  # ✅ 去掉 /api 前缀
                    params=test["params"]
                )

                # 应该返回400错误
                if response.status_code == 400:
                    self.log(f"   ✅ {test['desc']}: 正确返回400错误", "PASS")
                    passed += 1
                else:
                    self.log(f"   ❌ {test['desc']}: 返回{response.status_code}（预期400）", "FAIL")

            except Exception as e:
                self.log(f"   ❌ {test['desc']}: 请求异常", "ERROR")

        if passed == len(error_tests):
            self.log(f"✅ 错误处理测试全部通过 ({passed}/{len(error_tests)})", "PASS")
            self.results["tests_passed"] += 1
            return True
        else:
            self.log(f"❌ 错误处理测试部分失败 ({passed}/{len(error_tests)})", "FAIL")
            self.results["tests_failed"] += 1
            return False

    def test_data_structure(self):
        """测试6：数据结构验证"""
        self.log("\n" + "=" * 70)
        self.log("测试6：数据结构验证", "TEST")
        self.log("=" * 70)

        try:
            response = requests.get(
                f"{self.base_url}/holidays/month",  # ✅ 去掉 /api 前缀
                params={"year": 2026, "month": 1}
            )

            if response.status_code != 200:
                self.log("❌ API请求失败", "FAIL")
                self.results["tests_failed"] += 1
                return False

            data = response.json()

            # 验证必需字段
            required_fields = ["success", "year", "month", "count", "holidays"]
            missing_fields = [f for f in required_fields if f not in data]

            if missing_fields:
                self.log(f"❌ 缺少字段: {missing_fields}", "FAIL")
                self.results["tests_failed"] += 1
                return False

            # 验证节假日数据结构
            if data["holidays"]:
                holiday = data["holidays"][0]
                holiday_fields = ["date", "name", "is_legal_holiday"]
                missing_holiday_fields = [f for f in holiday_fields if f not in holiday]

                if missing_holiday_fields:
                    self.log(f"❌ 节假日数据缺少字段: {missing_holiday_fields}", "FAIL")
                    self.results["tests_failed"] += 1
                    return False

                # 验证数据类型
                if not isinstance(holiday["is_legal_holiday"], bool):
                    self.log(f"❌ is_legal_holiday 应该是布尔值", "FAIL")
                    self.results["tests_failed"] += 1
                    return False

            self.log(f"✅ 数据结构验证通过", "PASS")
            self.log(f"   顶层字段: {', '.join(required_fields)}")
            self.log(f"   节假日字段: {', '.join(holiday_fields)}")
            self.log(f"   数据类型: 正确")

            self.results["tests_passed"] += 1
            return True

        except Exception as e:
            self.log(f"❌ 测试异常: {str(e)}", "ERROR")
            self.results["tests_failed"] += 1
            return False

    def generate_report(self):
        """生成测试报告"""
        self.log("\n" + "=" * 70)
        self.log("📊 测试报告", "REPORT")
        self.log("=" * 70)

        total_tests = self.results["tests_passed"] + self.results["tests_failed"]
        pass_rate = (self.results["tests_passed"] / total_tests * 100) if total_tests > 0 else 0

        self.log(f"\n测试结果汇总:")
        self.log(f"  ✅ 通过: {self.results['tests_passed']}")
        self.log(f"  ❌ 失败: {self.results['tests_failed']}")
        self.log(f"  📈 通过率: {pass_rate:.1f}%")

        if self.results["performance_data"]:
            self.log(f"\n性能数据:")
            for perf in self.results["performance_data"]:
                self.log(f"  {perf['test']}:")
                if 'avg_ms' in perf:
                    self.log(f"    平均: {perf['avg_ms']:.2f}ms")
                    self.log(f"    范围: {perf['min_ms']:.2f}ms - {perf['max_ms']:.2f}ms")
                else:
                    self.log(f"    耗时: {perf['time_ms']:.2f}ms")

        # 给出建议
        self.log(f"\n💡 优化建议:")
        if pass_rate == 100:
            self.log("  ✅ 所有测试通过，系统运行正常")
        else:
            self.log(f"  ⚠️ 有 {self.results['tests_failed']} 个测试失败，需要修复")

        # 性能建议
        avg_perf = sum(p.get('avg_ms', p.get('time_ms', 0)) for p in self.results["performance_data"]) / len(self.results["performance_data"]) if self.results["performance_data"] else 0

        if avg_perf < 100:
            self.log("  ✅ 性能优秀，前端缓存足够")
        elif avg_perf < 300:
            self.log("  ⚠️ 性能良好，可以考虑添加前端缓存优化")
        else:
            self.log("  ❌ 性能一般，建议启用Redis缓存")

        self.log("\n" + "=" * 70)

    def run_all_tests(self):
        """运行所有测试"""
        self.log("🚀 开始缓存系统完整测试", "START")
        self.log(f"目标服务器: {self.base_url}")
        self.log(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        self.results["start_time"] = datetime.now()

        # 执行所有测试
        tests = [
            self.test_api_response,
            self.test_weekend_marking,
            self.test_cross_month_view,
            self.test_performance_consistency,
            self.test_error_handling,
            self.test_data_structure
        ]

        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.log(f"❌ 测试执行异常: {str(e)}", "ERROR")
                self.results["tests_failed"] += 1

        # 生成报告
        self.generate_report()

        return self.results["tests_failed"] == 0


if __name__ == "__main__":
    tester = CacheSystemTester(base_url="http://localhost:8080")
    success = tester.run_all_tests()

    if success:
        print("\n🎉 所有测试通过！")
        exit(0)
    else:
        print("\n⚠️ 部分测试失败，请检查日志")
        exit(1)
