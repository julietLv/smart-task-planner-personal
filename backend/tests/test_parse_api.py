"""直接测试 /api/tasks/parse 接口"""
import requests
import json

url = "http://localhost:8080/api/tasks/parse"
data = {"text": "跑步"}

print("=" * 70)
print("测试 /api/tasks/parse 接口")
print("=" * 70)
print(f"\n请求 URL: {url}")
print(f"请求数据: {data}")
print("\n发送请求...")

try:
    response = requests.post(url, json=data, timeout=10)
    
    print(f"\n状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")
    print(f"\n响应内容:")
    
    if response.status_code == 200:
        result = response.json()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(response.text)
        
except requests.exceptions.ConnectionError:
    print("❌ 连接失败：请确保后端服务正在运行 (http://localhost:8080)")
except requests.exceptions.Timeout:
    print("❌ 请求超时")
except Exception as e:
    print(f"❌ 异常: {e}")
    import traceback
    traceback.print_exc()
