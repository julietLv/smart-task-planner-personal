"""清空Redis中所有待处理的周报任务"""
import sys
sys.path.insert(0, '.')

from app.services.cache_service import redis_cache

if __name__ == "__main__":
    if not redis_cache.enabled:
        print("❌ Redis 未启用")
        exit(1)
    
    print("🧹 开始清理 Redis 中的遗留任务...")
    
    # 1. 清除所有 pending 状态的任务
    task_keys = redis_cache.client.keys("task:*")
    cleared_count = 0
    
    for key in task_keys:
        status = redis_cache.client.hget(key, "status")
        if status and status in ["pending", "processing"]:
            redis_cache.client.delete(key)
            print(f"  🗑️ 删除任务: {key} (status={status})")
            cleared_count += 1
    
    # 2. 清除所有 report_submitting 标记
    submit_keys = redis_cache.client.keys("report_submitting:*")
    for key in submit_keys:
        redis_cache.client.delete(key)
        print(f"  🗑️ 删除提交标记: {key}")
        cleared_count += 1
    
    # 3. 清除队列中的所有任务
    queue_keys = ["task_queue:high", "task_queue:normal", "task_queue:low"]
    for key in queue_keys:
        length = redis_cache.client.llen(key)
        if length > 0:
            redis_cache.client.delete(key)
            print(f"  🗑️ 清空队列: {key} ({length} 个任务)")
            cleared_count += 1
    
    print(f"\n✅ 清理完成，共清除 {cleared_count} 个键")
    print("💡 现在可以重启后端服务了")
