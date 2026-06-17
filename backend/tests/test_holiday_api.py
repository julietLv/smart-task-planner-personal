"""backend/test_holiday_api.py - 测试节假日API"""
import requests

print("=" * 60)
print("测试：节假日 API")
print("=" * 60)

base_url = "http://localhost:8080/api"

# 测试 1: 获取 2026年5月的节假日
print("\n【测试 1】获取 2026年5月的节假日...")
response = requests.get(f"{base_url}/holidays/month", params={"year": 2026, "month": 5})

if response.status_code == 200:
    data = response.json()
    print(f"✅ 成功！共 {data['count']} 个节假日")
    for h in data['holidays']:
        print(f"   - {h['date']}: {h['name']} ({'法定' if h['is_legal_holiday'] else '周末'})")
else:
    print(f"❌ 失败: {response.text}")

# 测试 2: 检查特定日期
print("\n【测试 2】检查 2026-05-02 是否为节假日...")
response = requests.get(f"{base_url}/holidays/check", params={"check_date": "2026-05-02"})

if response.status_code == 200:
    data = response.json()
    print(f"✅ 日期: {data['date']}")
    print(f"   是否节假日: {data['is_holiday']}")
    print(f"   节日名称: {data['holiday_name']}")
    print(f"   是否法定: {data['is_legal_holiday']}")
else:
    print(f"❌ 失败: {response.text}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
