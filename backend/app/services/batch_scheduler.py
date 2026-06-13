# backend/app/services/batch_scheduler.py
from typing import Dict, Any


async def batch_schedule_tasks(payload: Dict[str, Any]) -> Dict[str, Any]:
    """异步批量排程"""
    user_id = payload['user_id']
    task_ids = payload['task_ids']
    
    from app.services.or_tools_scheduler import ORToolsScheduler
    scheduler = ORToolsScheduler()
    
    result = scheduler.schedule_multiple(user_id, task_ids)
    
    # 推送排程结果
    from app.services.websocket_service import push_schedule_change
    await push_schedule_change({
        "message": f"已为 {len(task_ids)} 个任务重新排程",
        "scheduled_tasks": result.get('scheduled', [])
    }, user_id)
    
    return result
