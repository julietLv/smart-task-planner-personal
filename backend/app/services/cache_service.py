"""
数据库连接池和 Redis 缓存服务
"""
import os
import json
import redis
import pymysql
from typing import Optional, Any
from dbutils.pooled_db import PooledDB
from dotenv import load_dotenv

load_dotenv()


# ==================== Redis 缓存配置 ====================

class RedisCache:
    """Redis 缓存服务"""

    def __init__(self):
        self.enabled = False
        self.client: Optional[redis.Redis] = None

        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                self.client = redis.from_url(redis_url, decode_responses=True)
                self.client.ping()
                self.enabled = True
                print(f"[OK] Redis 缓存已启用: {redis_url}")
            except Exception as e:
                print(f"[WARN] Redis 连接失败，缓存功能已禁用: {e}")
        else:
            print("[INFO] 未配置 REDIS_URL，缓存功能已禁用")

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.enabled:
            return None

        try:
            value = self.client.get(key)
            if value:
                print(f"[OK] Redis 缓存命中: {key}")
                # ⭐ 特殊处理：如果是 bytes 类型，直接返回（用于 Word 文档等二进制数据）
                if isinstance(value, bytes):
                    return value
                # 普通数据使用 JSON 反序列化
                return json.loads(value)
            return None
        except Exception as e:
            print(f"[WARN] Redis 读取失败: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        设置缓存
        :param key: 缓存键
        :param value: 缓存值
        :param ttl: 过期时间（秒），默认 5 分钟
        """
        if not self.enabled:
            return False

        try:
            # ⭐ 特殊处理：如果是 bytes 类型，直接存储（用于 Word 文档等二进制数据）
            if isinstance(value, bytes):
                self.client.setex(key, ttl, value)
                print(f"💾 Redis 缓存已保存 (binary): {key} (TTL: {ttl}s, size: {len(value)} bytes)")
                return True
            
            # 普通数据使用 JSON 序列化
            self.client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
            print(f"💾 Redis 缓存已保存: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            print(f"[WARN] Redis 写入失败: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.enabled:
            return False

        try:
            self.client.delete(key)
            return True
        except Exception as e:
            print(f"[WARN] Redis 删除失败: {e}")
            return False

    def clear_pattern(self, pattern: str) -> bool:
        """批量删除匹配模式的缓存"""
        if not self.enabled:
            return False

        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
                print(f"[DEL] 已清除 {len(keys)} 个缓存键 (pattern: {pattern})")
            return True
        except Exception as e:
            print(f"[WARN] Redis 批量删除失败: {e}")
            return False


# 全局 Redis 缓存实例
redis_cache = RedisCache()


# ==================== MySQL 连接池配置 ====================

class DatabasePool:
    """数据库连接池"""
    
    def __init__(self):
        self.pool = None
        self.database_type = os.getenv("DATABASE_TYPE", "mysql").lower()
        
        if self.database_type == "mysql":
            self._init_mysql_pool()
    
    def _init_mysql_pool(self):
        """初始化 MySQL 连接池"""
        try:
            self.pool = PooledDB(
                creator=pymysql,
                maxconnections=int(os.getenv("DB_POOL_MAX", 20)),
                mincached=int(os.getenv("DB_POOL_MIN", 5)),
                maxcached=int(os.getenv("DB_POOL_MAX_CACHED", 10)),
                maxshared=int(os.getenv("DB_POOL_MAX_SHARED", 0)),
                blocking=True,
                maxusage=None,
                setsession=[],
                ping=1,
                host=os.getenv("MYSQL_HOST", "localhost"),
                port=int(os.getenv("MYSQL_PORT", 3306)),
                user=os.getenv("MYSQL_USER", "root"),
                password=os.getenv("MYSQL_PASSWORD", ""),
                database=os.getenv("MYSQL_DATABASE", "task_planner"),
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
            print(f"[OK] MySQL 连接池已初始化 (max: {os.getenv('DB_POOL_MAX', 20)}, min: {os.getenv('DB_POOL_MIN', 5)})")
        except Exception as e:
            print(f"[ERROR] MySQL 连接池初始化失败: {e}")
            raise
    
    def get_connection(self):
        """从连接池获取连接"""
        if self.database_type == "mysql":
            if self.pool:
                return self.pool.connection()
            else:
                # 降级到普通连接
                return pymysql.connect(
                    host=os.getenv("MYSQL_HOST", "localhost"),
                    port=int(os.getenv("MYSQL_PORT", 3306)),
                    user=os.getenv("MYSQL_USER", "root"),
                    password=os.getenv("MYSQL_PASSWORD", ""),
                    database=os.getenv("MYSQL_DATABASE", "task_planner"),
                    charset="utf8mb4",
                    cursorclass=pymysql.cursors.DictCursor
                )
        else:
            # SQLite 不需要连接池
            import sqlite3
            database_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data",
                "schedule.db"
            )
            os.makedirs(os.path.dirname(database_path), exist_ok=True)
            conn = sqlite3.connect(database_path)
            conn.row_factory = sqlite3.Row
            return conn


# 全局数据库连接池实例
db_pool = DatabasePool()
