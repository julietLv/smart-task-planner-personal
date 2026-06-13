from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import asyncio
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入路由
from app.routers import (
    task_router,
    chat_router_refactored_example as chat_router,
    weather_router,
    holiday_router,
    feedback_router,
    notification_router,
    preference_router,
    smart_scheduling_router,
    websocket_router,
    analytics_router,
    report_router
)


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    
    app = FastAPI(
        title="智能任务规划系统",
        description="基于约束规划的智能任务排程系统",
        version="2.0.0"
    )
    
    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # ⭐ 注册路由时添加 /api 前缀
    app.include_router(task_router.router, prefix="/api")
    app.include_router(chat_router.router, prefix="/api")
    app.include_router(weather_router.router, prefix="/api")
    app.include_router(holiday_router.router, prefix="/api")
    app.include_router(feedback_router.router, prefix="/api")
    app.include_router(notification_router.router, prefix="/api")
    app.include_router(preference_router.router, prefix="/api")
    app.include_router(smart_scheduling_router.router, prefix="/api")
    app.include_router(analytics_router.router, prefix="/api")
    app.include_router(report_router.router, prefix="/api")
    
    # ⭐ WebSocket 路由不需要 /api 前缀（保持原样）
    app.include_router(websocket_router.router)

    # 启动定时任务和异步任务队列
    @app.on_event("startup")
    def startup_event():
        from app.services.scheduler_service import start_scheduler
        start_scheduler()
        
        # ⭐ 新增：初始化异步任务队列
        from app.services.cache_service import redis_cache
        from app.services.task_queue import TaskQueue
        
        if redis_cache.enabled:
            task_queue = TaskQueue(redis_cache.client)
            
            # ⭐ 新增：设置全局实例
            from app.services.task_queue import set_task_queue
            set_task_queue(task_queue)
            
            # 注册任务处理器
            try:
                from app.services.report_generator import generate_weekly_report
                task_queue.register_worker("generate_report", generate_weekly_report)
                print("✅ 已注册周报生成任务处理器")
            except ImportError as e:
                print(f"⚠️ 周报生成器导入失败: {e}")
            
            try:
                from app.services.batch_scheduler import batch_schedule_tasks
                task_queue.register_worker("batch_schedule", batch_schedule_tasks)
                print("✅ 已注册批量排程任务处理器")
            except ImportError as e:
                print(f"⚠️ 批量排程导入失败: {e}")
            
            # 启动后台消费者
            asyncio.create_task(task_queue.start_consumer())
            print("✅ 异步任务队列已启动")
        else:
            print("⚠️ Redis 未启用，异步任务队列未启动")
        
        print("✅ 应用启动完成")
    
    # 停止定时任务
    @app.on_event("shutdown")
    def shutdown_event():
        from app.services.scheduler_service import stop_scheduler
        stop_scheduler()
        print("✅ 应用关闭完成")
    
    @app.get("/")
    def read_root():
        return {
            "message": "智能任务规划系统 API",
            "version": "2.0.0",
            "docs": "/docs"
        }
    
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
