# D:\demo_plan\backend\clear_report_cache.py
"""清除周报生成缓存标记"""
import sys

sys.path.insert(0, 'D:\\demo_plan\\backend')

from app.services.cache_service import redis_cache

if __name__ == '__main__':
    if not redis_cache.enabled:
        print("❌ Redis 未启用")
        exit(1)

    # 清除所有用户的周报提交标记
    keys = redis_cache.client.keys("report_submitting:*")
    if keys:
        for key in keys:
            redis_cache.client.delete(key)
            print(f"✅ 已删除: {key}")
    else:
        print("ℹ️ 没有需要清除的缓存")

    print("\n🎉 缓存清理完成，现在可以重新生成周报了！")
