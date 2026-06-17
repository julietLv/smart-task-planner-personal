import requests

print("=" * 50)
print("测试：获取用户当前城市")
print("=" * 50)

try:
    # 获取用户城市
    response = requests.get(
        "http://localhost:8080/api/weather/city",
        params={"user_id": 1}
    )

    print(f"\n状态码: {response.status_code}")
    print(f"响应数据: {response.json()}")

    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"\n✅ 当前城市: {data['city']}")
        else:
            print("\n❌ 获取城市失败")
    else:
        print(f"\n❌ 请求失败: {response.text}")

except requests.exceptions.ConnectionError:
    print("\n❌ 连接失败：请确保后端服务器正在运行（python main.py）")
except Exception as e:
    print(f"\n❌ 错误: {str(e)}")
