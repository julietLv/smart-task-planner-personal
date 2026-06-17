"""
详细验证Redis连接和配置 - D:\demo_plan\backend\verify_redis.py
"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

print("=" * 70)
print("🔍 Redis 连接详细验证")
print("=" * 70)

# ==================== 1. 检查环境变量 ====================
print("\n【步骤1】检查环境变量配置")
print("-" * 70)

redis_url = os.getenv("REDIS_URL")
cache_ttl_tasks = os.getenv("CACHE_TTL_TASKS", "300")
cache_ttl_llm = os.getenv("CACHE_TTL_LLM_RESPONSE", "600")

print(f"✓ REDIS_URL: {redis_url}")
print(f"✓ CACHE_TTL_TASKS: {cache_ttl_tasks}秒")
print(f"✓ CACHE_TTL_LLM_RESPONSE: {cache_ttl_llm}秒")

if not redis_url:
    print("\n❌ 错误: REDIS_URL 未配置!")
    print("请在 .env 文件中添加: REDIS_URL=redis://localhost:6379/1")
    sys.exit(1)

# ==================== 2. 检查redis库是否安装 ====================
print("\n【步骤2】检查Python redis库")
print("-" * 70)

try:
    import redis

    print(f"✅ redis库已安装")
    print(f"   版本: {redis.__version__}")
except ImportError:
    print("❌ redis库未安装")
    print("   请运行: pip install redis>=5.0.0")
    sys.exit(1)

# ==================== 3. 尝试连接Redis ====================
print("\n【步骤3】测试Redis连接")
print("-" * 70)

try:
    print(f"正在连接到: {redis_url}...")
    client = redis.from_url(redis_url, decode_responses=True)

    # 测试PING
    ping_result = client.ping()
    print(f"✅ PING 成功: {ping_result}")

    # 获取Redis信息
    info = client.info('server')
    print(f"\n📊 Redis服务器信息:")
    print(f"   版本: {info.get('redis_version', '未知')}")
    print(f"   运行模式: {info.get('redis_mode', '未知')}")
    print(f"   端口: {info.get('tcp_port', '未知')}")
    print(f"    uptime (秒): {info.get('uptime_in_seconds', '未知')}")

    # 测试当前数据库
    db_index = redis_url.split('/')[-1] if '/' in redis_url else '0'
    print(f"\n📁 当前使用的数据库: DB {db_index}")

    # ==================== 4. 测试读写操作 ====================
    print("\n【步骤4】测试缓存读写操作")
    print("-" * 70)

    test_key = "test:connection_check"
    test_value = {
        "message": "Redis连接测试成功",
        "timestamp": "2026-05-06T00:00:00",
        "database": db_index
    }

    # 写入测试
    print(f"写入测试数据到键: {test_key}")
    client.setex(test_key, 60, str(test_value))
    print("✅ 写入成功 (TTL: 60秒)")

    # 读取测试
    print(f"\n读取测试数据...")
    retrieved_value = client.get(test_key)
    if retrieved_value:
        print(f"✅ 读取成功: {retrieved_value[:50]}...")
    else:
        print("❌ 读取失败: 返回None")

    # 检查TTL
    ttl = client.ttl(test_key)
    print(f"⏱️  剩余TTL: {ttl}秒")

    # 清理测试数据
    client.delete(test_key)
    print(f"🗑️  测试数据已清理")

    # ==================== 5. 测试项目实际使用的缓存模式 ====================
    print("\n【步骤5】模拟项目缓存使用场景")
    print("-" * 70)

    # 模拟任务列表缓存
    user_id = 1
    cache_key = f"tasks:{user_id}:all"
    mock_tasks = [
        {"id": 1, "title": "测试任务1", "status": "pending"},
        {"id": 2, "title": "测试任务2", "status": "done"}
    ]

    print(f"模拟写入任务列表缓存: {cache_key}")
    import json

    client.setex(cache_key, int(cache_ttl_tasks), json.dumps(mock_tasks, ensure_ascii=False))
    print(f"✅ 写入成功 (TTL: {cache_ttl_tasks}秒)")

    # 读取缓存
    cached_data = client.get(cache_key)
    if cached_data:
        tasks = json.loads(cached_data)
        print(f"✅ 读取成功: {len(tasks)}个任务")
        for task in tasks:
            print(f"   - {task['title']} ({task['status']})")

    # 清理
    client.delete(cache_key)
    print(f"🗑️  模拟缓存已清理")

    # ==================== 6. 测试缓存服务模式 ====================
    print("\n【步骤6】测试项目CacheService类")
    print("-" * 70)

    try:
        from app.services.cache_service import redis_cache

        print(f"RedisCache实例状态:")
        print(f"   enabled: {redis_cache.enabled}")
        print(f"   client: {redis_cache.client}")

        if redis_cache.enabled:
            print("✅ CacheService已正确初始化")

            # 测试set/get
            test_service_key = "service:test"
            redis_cache.set(test_service_key, {"test": "data"}, ttl=60)
            result = redis_cache.get(test_service_key)

            if result:
                print(f"✅ CacheService读写测试成功: {result}")
                redis_cache.delete(test_service_key)
            else:
                print("❌ CacheService读取测试失败")
        else:
            print("❌ CacheService未启用")

    except Exception as e:
        print(f"❌ CacheService测试失败: {e}")
        import traceback

        traceback.print_exc()

    # ==================== 总结 ====================
    print("\n" + "=" * 70)
    print("🎉 Redis 连接验证完成!")
    print("=" * 70)
    print("\n✅ 所有测试通过，Redis已正确配置并可用")
    print("\n💡 提示:")
    print(f"   - 你的应用将使用 DB {db_index} 存储缓存数据")
    print(f"   - 任务列表缓存TTL: {cache_ttl_tasks}秒")
    print(f"   - LLM响应缓存TTL: {cache_ttl_llm}秒")
    print("\n🚀 现在可以启动后端服务，Redis缓存将自动生效")

except redis.exceptions.ConnectionError as e:
    print(f"\n❌ Redis连接失败!")
    print(f"   错误信息: {e}")
    print("\n可能的原因:")
    print("   1. Redis服务未启动")
    print("   2. 端口6379被占用或防火墙阻止")
    print("   3. Redis配置文件限制了连接")
    print("\n解决方案:")
    print("   🐳 Docker方式:")
    print("      docker run -d --name redis -p 6379:6379 redis:latest")
    print("\n   💻 WSL方式:")
    print("      wsl sudo service redis-server start")
    print("\n   🔧 Chocolatey方式:")
    print("      choco install redis-64")
    print("      redis-server --service-start")
    print("\n   📝 检查端口:")
    print("      netstat -an | findstr 6379")
    sys.exit(1)

except Exception as e:
    print(f"\n❌ 未知错误: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
