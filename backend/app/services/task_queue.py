# backend/app/services/task_queue.py
import json
import asyncio
from typing import Callable, Dict, Any
from redis import Redis
from datetime import datetime

class TaskQueue:
    """基于 Redis 的异步任务队列"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.queue_name = "task_queue"
        self.workers = []
    
    def enqueue(self, task_type: str, payload: Dict[str, Any], priority: int = 0):
        """将任务加入队列"""
        task = {
            "id": f"{task_type}_{datetime.now().timestamp()}",
            "type": task_type,
            "payload": payload,
            "priority": priority,
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        # 使用 Redis List 作为队列（简单场景）
        self.redis.lpush(self.queue_name, json.dumps(task))
        print(f"✅ 任务已入队: {task['id']} ({task_type})")
        return task['id']
    
    def dequeue(self, timeout: int = 5) -> Dict:
        """从队列取出任务（阻塞等待）"""
        result = self.redis.brpop(self.queue_name, timeout=timeout)
        if result:
            _, task_json = result
            return json.loads(task_json)
        return None
    
    def register_worker(self, task_type: str, handler: Callable):
        """注册任务处理器"""
        self.workers.append({"type": task_type, "handler": handler})
    
    async def start_consumer(self):
        """启动后台消费者"""
        print("🚀 任务消费者已启动")
        while True:
            task = self.dequeue()
            if task:
                await self._process_task(task)
            await asyncio.sleep(0.1)
    
    async def _process_task(self, task: Dict):
        """处理单个任务"""
        task_id = task['id']
        task_type = task['type']
        
        print(f"⚙️ 开始处理任务: {task_id} ({task_type})")
        
        # 查找对应的处理器
        handler = next((w['handler'] for w in self.workers if w['type'] == task_type), None)
        
        if not handler:
            print(f"❌ 未找到任务处理器: {task_type}")
            return
        
        try:
            # 执行任务
            result = await handler(task['payload'])
            
            # ⭐ 检查任务是否真正成功
            if isinstance(result, dict) and result.get('success') == False:
                print(f"❌ 任务执行失败: {task_id} - {result.get('error', '未知错误')}")
                # ⭐ 特殊处理：移除 bytes 类型的字段（如 word_content），避免 JSON 序列化失败
                result_copy = result.copy()
                for key in list(result_copy.keys()):
                    if isinstance(result_copy[key], bytes):
                        del result_copy[key]
                        print(f"⚠️ 移除 bytes 字段: {key}")
                
                # 标记为失败，不重试
                self.redis.hset(f"task:{task_id}", "status", "failed")
                self.redis.hset(f"task:{task_id}", "result", json.dumps(result_copy, ensure_ascii=False))
                self.redis.hset(f"task:{task_id}", "completed_at", datetime.now().isoformat())
                return
            
            # ⭐ 标记完成（使用兼容的 hset 写法）
            # ⭐ 特殊处理：移除 bytes 类型的字段（如 word_content），避免 JSON 序列化失败
            result_copy = result.copy() if isinstance(result, dict) else result
            if isinstance(result_copy, dict):
                for key in list(result_copy.keys()):
                    if isinstance(result_copy[key], bytes):
                        del result_copy[key]
                        print(f"⚠️ 移除 bytes 字段: {key}")
            
            self.redis.hset(f"task:{task_id}", "status", "completed")
            self.redis.hset(f"task:{task_id}", "result", json.dumps(result_copy, ensure_ascii=False))
            self.redis.hset(f"task:{task_id}", "completed_at", datetime.now().isoformat())
            
            print(f"✅ 任务完成: {task_id}")
            
        except Exception as e:
            print(f"❌ 任务异常: {task_id} - {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 重试逻辑（最多3次）
            retry_count = self.redis.hincrby(f"task:{task_id}", "retry_count", 1)
            if retry_count < 3:
                print(f"🔄 任务将重试 ({retry_count}/3): {task_id}")
                self.enqueue(task_type, task['payload'], priority=1)
            else:
                print(f"❌ 任务重试次数耗尽，标记为失败: {task_id}")
                self.redis.hset(f"task:{task_id}", "status", "failed")


# ⭐ 全局单例（供其他模块导入使用）
task_queue = None  # 将在 main.py 启动时赋值

def set_task_queue(instance: TaskQueue):
    """设置全局任务队列实例"""
    global task_queue
    task_queue = instance
    print(f"✅ 全局任务队列实例已设置")
# ⭐ 创建全局单例实例（延迟初始化）
_task_queue_instance = None

def get_task_queue() -> TaskQueue:
    """获取任务队列单例"""
    global _task_queue_instance
    if _task_queue_instance is None:
        from app.services.cache_service import redis_cache
        if redis_cache.enabled:
            _task_queue_instance = TaskQueue(redis_cache.client)
        else:
            raise RuntimeError("Redis 未启用，无法创建任务队列")
    return _task_queue_instance
