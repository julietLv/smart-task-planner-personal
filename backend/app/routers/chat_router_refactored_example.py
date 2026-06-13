"""
Chat Router 重构版 v2.0 - 使用 ActionExecutor

设计理念：
1. LLM 负责理解语义 -> 输出动作名+参数
2. ActionExecutor 负责执行动作 -> 返回数据
3. LLM/模板 根据数据生成自然语言回复

核心优势：
- 完全解耦：路由器不包含业务逻辑
- 易于扩展：新增功能只需注册动作
- 智能回复：支持LLM生成个性化回复
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from app.services.intent_engine import HybridIntentParser
from app.services.action_executor import executor
from app.models.task_model import get_user_preferences, get_all_tasks
from app.services.cache_service import redis_cache
from app.services.conflict_detector import conflict_detector
from app.services.or_tools_scheduler import or_scheduler

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    responses={404: {"description": "Not found"}},
)

# ⭐ 全局意图解析器实例（单例）
intent_parser = HybridIntentParser()


class ChatRequest(BaseModel):
    message: str
    user_id: int = 1


class GreetingRequest(BaseModel):
    user_id: int = 1


# ==================== 上下文管理 ====================
class TaskContextManager:

    @staticmethod
    def save(user_id: int, task_info: dict):
        """保存任务创建上下文"""
        redis_key = f"context:task:{user_id}"
        redis_cache.set(redis_key, {
            "task_info": task_info,
            "timestamp": datetime.now().isoformat(),
            "step": "pending_confirmation"
        }, ttl=600)

    @staticmethod
    def save_with_conflict(user_id: int, task_info: dict, conflicts: list, options: dict, alternative_solutions: list = None, original_message: str = None):
        """保存带冲突的任务创建上下文"""
        redis_key = f"context:task:{user_id}"
        context_data = {
            "task_info": task_info,
            "conflicts": conflicts,
            "options": options,
            "timestamp": datetime.now().isoformat(),
            "step": "conflict_resolution"
        }
        
        # 如果有备选方案，也保存到上下文
        if alternative_solutions:
            context_data["alternative_solutions"] = alternative_solutions
        
        # 保存原始消息用于重复检测
        if original_message:
            context_data["original_message"] = original_message
        
        redis_cache.set(redis_key, context_data, ttl=600)

    @staticmethod
    def get(user_id: int) -> Optional[dict]:
        """获取任务创建上下文"""
        redis_key = f"context:task:{user_id}"
        return redis_cache.get(redis_key)

    @staticmethod
    def clear(user_id: int):
        """清除任务创建上下文"""
        redis_key = f"context:task:{user_id}"
        redis_cache.delete(redis_key)


task_context_manager = TaskContextManager()


def _generate_chat_reply(
    user_id: int,
    user_message: str,
    user_nickname: str,
    assistant_nickname: str,
    memory_context: str = ""
) -> str:
    """
    生成日常聊天的回复
    
    对于非任务相关的闲聊，使用 LLM 生成个性化回复
    """
    try:
        from app.services.llm_service import get_deepseek_client
        
        client = get_deepseek_client()
        
        system_prompt = f"""你是用户的私人助理「{assistant_nickname}」，用户叫「{user_nickname}」。
请用亲切自然的语气回应用户的聊天（50字以内）。
可以适当使用emoji，让对话更生动。

【长期记忆】
{memory_context if memory_context else "无"}
"""
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.8,
            max_tokens=100,
            timeout=15
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"⚠️ 聊天回复生成失败: {e}")
        # 降级到简单回复
        return f"{user_nickname}，我在呢～有什么可以帮你的吗？😊"


def _handle_add_task_conversation(
    message: str,
    user_id: int,
    entities: Dict[str, Any],
    user_nickname: str,
    assistant_nickname: str
) -> Dict[str, Any]:
    """
    处理添加任务的多轮对话

    这是唯一保留状态管理的部分，因为添加任务需要：
    1. 收集信息（标题、时长、截止时间）
    2. 检测冲突
    3. 等待用户确认或解决冲突
    4. 最终执行创建
    """

    # 捕获统一参考时间，避免多处datetime.now()跨天漂移
    current_date = datetime.now().isoformat()

    # 检查是否有未完成的任务创建上下文
    pending_task = task_context_manager.get(user_id)

    if pending_task:
        print(f"🔄 检测到待确认任务: {pending_task}")

        step = pending_task.get('step', 'pending_confirmation')
        
        # ⭐ 新增：重复请求检测
        original_message = pending_task.get('original_message', '')
        if message.strip() == original_message.strip() and step == "conflict_resolution":
            print(f"⚠️ 检测到重复请求，提示用户选择处理方式")
            conflicts = pending_task.get('conflicts', [])
            conflict_titles = [c.get('conflicting_task_title', '未知任务') for c in conflicts[:3]]
            
            reply = f"⚠️ 检测到时间冲突，请在下方可视化方案中选择处理方式～"
            
            return {
                "reply": reply,
                "intent": "chat",
                "success": True,
                "requires_confirmation": True
            }
        
        #  处理冲突解决阶段
        if step == "conflict_resolution":
            print(f"⚠️ 正在处理冲突解决...")
            
            # 用户选择关键词
            ignore_keywords = ["忽略", "强制", "ignore", "force", "直接添加"]
            auto_adjust_keywords = ["调整", "自动", "重新安排", "auto", "adjust", "换时间"]
            cancel_keywords = ["取消", "不要了", "cancel", "删除"]
            
            is_ignore = any(kw in message.lower() for kw in ignore_keywords)
            is_auto_adjust = any(kw in message.lower() for kw in auto_adjust_keywords)
            is_cancel = any(kw in message.lower() for kw in cancel_keywords)
            
            task_info = pending_task.get('task_info', {})
            
            if is_cancel:
                task_context_manager.clear(user_id)
                return {
                    "reply": f"❌ 已取消添加任务「{task_info.get('title')}」",
                    "intent": "add_task",
                    "success": True
                }
            
            elif is_ignore:
                print(f"✅ 用户选择忽略冲突")
                # 移除时间字段，让系统自动排程
                task_info_without_time = {k: v for k, v in task_info.items() 
                                         if k not in ['start_time', 'end_time']}
                
                action_result = executor.execute("add_task", {
                    **task_info_without_time,
                    "user_id": user_id,
                    "user_text": message,
                    "current_date": current_date
                })
                
                if action_result.get('success'):
                    task_context_manager.clear(user_id)
                    task = action_result.get('task', {})
                    scheduled_time = action_result.get('scheduled_time', {})
                    
                    reply = f"✅ 任务「{task.get('title')}」已强制添加！\n"
                    reply += f"⚠️ 注意：存在时间冲突，请手动调整\n"
                    reply += f"加油哦！"
                    
                    return {
                        "reply": reply,
                        "intent": "add_task",
                        "success": True,
                        "data": action_result
                    }
                else:
                    return {
                        "reply": f" 创建任务失败：{action_result.get('error', '未知错误')}",
                        "intent": "add_task",
                        "success": False
                    }
            
            elif is_auto_adjust:
                print(f"🔄 用户选择自动调整")
                # ⭐ 修复：过滤掉不需要的字段
                task_info = pending_task.get('task_info', {})
                task_info_without_time = {k: v for k, v in task_info.items() 
                                         if k not in ['start_time', 'end_time', 'scheduled_start_time', 'scheduled_end_time']}
                
                action_result = executor.execute("add_task", {
                    **task_info_without_time,
                    "user_id": user_id,
                    "user_text": message,
                    "current_date": current_date
                })
                
                if action_result.get('success'):
                    task_context_manager.clear(user_id)
                    task = action_result.get('task', {})
                    scheduled_time = action_result.get('scheduled_time', {})
                    
                    reply = f"✅ 任务「{task.get('title')}」已重新安排！\n"
                    reply += f" 新时间：{scheduled_time['start_time'][11:16]} - {scheduled_time['end_time'][11:16]}\n"
                    
                    # 显示备选方案
                    alt_solutions = action_result.get('alternative_solutions', [])
                    if alt_solutions:
                        reply += f"\n其他可选时间：\n"
                        for idx, alt in enumerate(alt_solutions[:2], 1):
                            reply += f"{idx}. {alt['start_time'][11:16]} - {alt['end_time'][11:16]}\n"
                    
                    reply += "加油哦！"
                    
                    return {
                        "reply": reply,
                        "intent": "add_task",
                        "success": True,
                        "data": action_result
                    }
                else:
                    return {
                        "reply": f"❌ 重新排程失败：{action_result.get('error', '未知错误')}",
                        "intent": "add_task",
                        "success": False
                    }
            else:
                # 用户未明确选择，再次提示
                conflicts = pending_task.get('conflicts', [])
                conflict_titles = [c.get('conflicting_task_title', '未知任务') for c in conflicts[:3]]
                
                reply = f"⚠️ 检测到时间冲突，请在下方可视化方案中选择处理方式～"
                
                return {
                    "reply": reply,
                    "intent": "chat",
                    "success": True,
                    "requires_confirmation": True
                }

        # ⭐ 优化：检测用户是否发送了新的任务创建请求
        # 即使 entities 为空，也要通过消息内容判断是否是新任务
        new_task_keywords = ["创建", "添加", "新建", "安排"]
        time_keywords = ["点", "上午", "下午", "明天", "今天", "后天"]
        duration_keywords = ["分钟", "小时", "时长"]
        
        has_time = any(kw in message for kw in time_keywords)
        has_duration = any(kw in message for kw in duration_keywords)
        
        # 检查是否有新标题（通过 LLM 识别的 entities 或者消息内容推断）
        new_title = entities.get("title")
        old_title = pending_task.get('task_info', {}).get('title', '')
        
        # ⭐ 如果没有 title，尝试从消息中提取（简单启发式：找逗号前后的文字）
        if not new_title:
            # 简单提取：寻找类似 "时间，标题，时长" 的模式
            parts = message.split('，')
            if len(parts) >= 2:
                potential_title = parts[1].strip()
                # 如果第二部分不是时间/时长描述，可能是标题
                if not any(kw in potential_title for kw in ["点", "分钟", "小时", "上午", "下午"]):
                    new_title = potential_title
        
        has_new_title = new_title and new_title != old_title
        
        # ⭐ 判断条件优化：有时间+时长+新标题 = 新任务
        has_new_task_request = has_time and has_duration and has_new_title
        
        print(f"🔍 调试信息: has_time={has_time}, has_duration={has_duration}, has_new_title={has_new_title}")
        print(f"🔍 调试信息: new_title='{new_title}', old_title='{old_title}'")
        print(f"🔍 调试信息: entities={entities}")
        
        # 如果检测到新任务请求，取消待确认任务
        if has_new_task_request:
            print(f"🔄 检测到新任务请求，取消待确认任务: {old_title} -> {new_title}")
            task_context_manager.clear(user_id)
            # 继续处理新任务（走下面的新任务创建流程）
        else:
            print(f"⚠️ 未检测到新任务，继续待确认流程")
            # 用户确认关键词
            confirm_keywords = ["yes", "ok", "好", "可以", "确认", "execute", "do it", "安排", "create", "行", "确认创建"]
            is_confirmed = any(kw in message.lower() for kw in confirm_keywords)

            if is_confirmed:
                print(f"✅ 用户确认，调用 ActionExecutor 创建任务")

                #  关键修复：过滤掉 scheduled_start_time 和 scheduled_end_time
                # 这些字段只用于上下文存储，不应该传递给 ActionExecutor
                task_info = pending_task.get('task_info', pending_task)
                clean_task_info = {
                    k: v for k, v in task_info.items() 
                    if k not in ['scheduled_start_time', 'scheduled_end_time']
                }
                
                action_result = executor.execute("add_task", {
                    **clean_task_info,
                    "user_id": user_id,
                    "user_text": message,
                    "current_date": current_date
                })

                if action_result.get('success'):
                    # 清除上下文
                    task_context_manager.clear(user_id)

                    task = action_result.get('task', {})
                    scheduled_time = action_result.get('scheduled_time', {})
                    
                    # ⭐ 检查是否有冲突需要处理
                    if action_result.get('has_conflict'):
                        conflicts = action_result.get('conflicts', [])
                        recommended_solution = action_result.get('recommendedSolution')
                        alternative_solutions = action_result.get('alternativeSolutions', [])
                        
                        # 保存冲突上下文（包含备选方案）
                        task_context_manager.save_with_conflict(
                            user_id=user_id,
                            task_info=task_info,
                            conflicts=conflicts,
                            options=action_result.get('options', {}),
                            alternative_solutions=alternative_solutions
                        )
                        
                        reply = f"⚠️ 检测到时间冲突，已为您生成智能排程方案，请在下方查看并选择～"
                        
                        return {
                            "reply": reply,
                            "intent": "add_task",
                            "success": True,
                            "requires_confirmation": True,
                            "has_conflict": True,
                            "conflicts": conflicts,
                            "recommendedSolution": recommended_solution,
                            "alternativeSolutions": alternative_solutions,
                            "task_preview": task_info,
                            "can_complete_continuously": action_result.get('can_complete_continuously', True),
                            "split_suggestions": action_result.get('split_suggestions', []),
                            "load_warning": action_result.get('load_warning')  # 负荷警告
                        }
                    
                    # ⭐ 构建回复
                    reply = f"✅ 任务「{task.get('title')}」已创建成功！\n"
                    reply += f"📅 时间：{scheduled_time['start_time'][11:16]} - {scheduled_time['end_time'][11:16]}\n"
                    
                    # P0: 添加连续性标记提示
                    if not action_result.get('can_complete_continuously', True):
                        reply += f"⚠️ 任务无法连续完成，建议查看拆分方案\n"
                    
                    # ⭐ 如果时间被调整，添加说明
                    if action_result.get('time_adjusted'):
                        reply += f" {action_result.get('adjustment_reason', '已自动优化时间安排')}\n"
                    
                    # 显示备选方案
                    alt_solutions = action_result.get('alternativeSolutions', [])
                    if alt_solutions:
                        reply += f"\n其他可选时间：\n"
                        for idx, alt in enumerate(alt_solutions[:2], 1):
                            reply += f"{idx}. {alt['start_time'][11:16]} - {alt['end_time'][11:16]}\n"

                    reply += "加油哦！"

                    response_data = {
                        "reply": reply,
                        "intent": "add_task",
                        "success": True,
                        "data": action_result,
                        "can_complete_continuously": action_result.get('can_complete_continuously', True),
                        "split_suggestions": action_result.get('split_suggestions', []),
                        "load_warning": action_result.get('load_warning')  # 负荷警告
                    }

                    return response_data
                else:
                    return {
                        "reply": f" 创建任务失败：{action_result.get('error', '未知错误')}",
                        "intent": "add_task",
                        "success": False
                    }
            else:
                # 用户可能在调整参数
                task_info = pending_task.get('task_info', {})
                reply = f"📝 当前任务信息：\n"
                reply += f"• 标题：{task_info.get('title', '未命名')}\n"
                reply += f"• 时长：{task_info.get('duration', 60)}分钟\n"
                if task_info.get('deadline'):
                    reply += f"• 截止：{task_info['deadline'][:16]}\n"
                reply += f"\n请回复「确认」来创建，或告诉我需要调整什么～"

                return {
                    "reply": reply,
                    "intent": "chat",
                    "success": True,
                    "requires_confirmation": True
                }

    # ==================== 新任务创建流程 ====================
    print(f"➕ 开始新任务创建流程")

    task_info = {
        "title": entities.get("title"),
        "duration": entities.get("duration", 60),
        "deadline": entities.get("deadline"),
        "priority": entities.get("priority", "medium"),
        "user_text": message,
        "current_date": current_date,
        # ⭐ 新增：保存用户请求的时间，用于后续冲突检测
        "requested_start_time": entities.get("start_time"),
        "requested_end_time": entities.get("end_time")
    }

    # 处理 time_range（使用统一参考时间，避免跨天漂移）
    time_range = entities.get("time_range")
    if time_range and not task_info['deadline']:
        ref_dt = datetime.fromisoformat(current_date)
        target_date = None
        if time_range == "tomorrow":
            target_date = ref_dt + timedelta(days=1)
        elif time_range == "day_after_tomorrow":
            target_date = ref_dt + timedelta(days=2)
        elif time_range == "today":
            target_date = ref_dt

        if target_date:
            task_info['deadline'] = target_date.replace(hour=18, minute=0).isoformat()

    # 如果没有标题，询问用户
    if not task_info.get('title'):
        return {
            "reply": f"好的！请问任务的标题是什么呢？😊",
            "intent": "chat",
            "success": True,
            "requires_input": True
        }

    # ⭐⭐⭐ 关键修复：在首次接收任务时就调用智能排程进行冲突检测 ⭐⭐⭐
    print(f"🧠 步骤1: 调用 OR-Tools 进行智能排程和冲突检测...")

    # 调用 ActionExecutor 执行 add_task（会先检测冲突）
    action_result = executor.execute("add_task", {
        **task_info,
        "user_id": user_id,
        "user_text": message,
        "current_date": current_date
    })

    # 如果检测到冲突，保存上下文并返回冲突信息
    if action_result.get('has_conflict'):
        print(f"️ 检测到时间冲突，保存冲突上下文")

        conflicts = action_result.get('conflicts', [])
        recommended_solution = action_result.get('recommendedSolution')  # ⭐ 修复：使用大驼峰
        alternative_solutions = action_result.get('alternativeSolutions', [])  # ⭐ 修复：使用大驼峰

        # 保存冲突上下文（包含备选方案）
        task_context_manager.save_with_conflict(
            user_id=user_id,
            task_info=task_info,
            conflicts=conflicts,
            options=action_result.get('options', {}),
            alternative_solutions=alternative_solutions
        )

        # ⭐ 修复：不再返回旧版本文字提示，只返回结构化数据供前端可视化
        reply = f"️ 检测到时间冲突，已为您生成智能排程方案，请在下方查看并选择～"

        return {
            "reply": reply,
            "intent": "add_task",
            "success": True,
            "requires_confirmation": True,
            "has_conflict": True,
            "conflicts": conflicts,
            "recommendedSolution": recommended_solution,  # ⭐ 修复
            "alternativeSolutions": alternative_solutions,
            "task_preview": task_info,
            "can_complete_continuously": action_result.get('can_complete_continuously', True),
            "split_suggestions": action_result.get('split_suggestions', []),
            "load_warning": action_result.get('load_warning')  # 负荷警告
        }

    # 如果没有冲突，任务已由 action_add_task 成功创建，直接返回（不再要求确认）
    if action_result.get('success'):
        print(f"✅ 智能排程成功，任务已直接创建")

        scheduled_time = action_result.get('scheduled_time', {})
        task = action_result.get('task', {})

        reply = f"✅ 任务「{task.get('title', task_info['title'])}」已创建！\n"
        if scheduled_time.get('start_time') and scheduled_time.get('end_time'):
            reply += f"📅 时间：{scheduled_time['start_time'][11:16]} - {scheduled_time['end_time'][11:16]}\n"
        reply += f"⏱️ 时长：{task_info['duration']}分钟\n"
        if task_info.get('deadline'):
            reply += f"📌 截止：{task_info['deadline'][:16]}\n"
        reply += "加油哦！"

        return {
            "reply": reply,
            "intent": "add_task",
            "success": True,
            "task_created": True,
            "data": action_result,
            "can_complete_continuously": action_result.get('can_complete_continuously', True),
            "split_suggestions": action_result.get('split_suggestions', []),
            "load_warning": action_result.get('load_warning')
        }

    # 如果排程失败，返回错误信息
    return {
        "reply": f" 排程失败：{action_result.get('error', '未知错误')}",
        "intent": "add_task",
        "success": False,
        "suggestions": action_result.get('suggestions', []),
        "can_complete_continuously": action_result.get('can_complete_continuously', False),
        "split_suggestions": action_result.get('split_suggestions', []),
        "load_warning": action_result.get('load_warning')  # 负荷警告
    }


def _handle_modify_task_conversation(
    message: str,
    user_id: int,
    entities: Dict[str, Any],
    user_nickname: str,
    assistant_nickname: str
) -> Dict[str, Any]:
    """处理修改任务的对话"""

    task_title = entities.get("title")

    if not task_title:
        return {
            "reply": f"{user_nickname}，请告诉我你要修改哪个任务？",
            "intent": "chat",
            "success": False
        }

    # 查找任务
    all_tasks = get_all_tasks(user_id)
    target_task = None

    for task in all_tasks:
        if task.title and task_title.lower() in task.title.lower():
            target_task = task
            break

    if not target_task:
        return {
            "reply": f"{user_nickname}，我没有找到名为「{task_title}」的任务哦～",
            "intent": "chat",
            "success": False
        }

    # 准备修改数据
    update_data = {
        "task_id": target_task.id,
        "user_id": user_id
    }

    # 提取要修改的字段
    if entities.get("start_time") and entities.get("end_time"):
        update_data["start_time"] = entities["start_time"]
        update_data["end_time"] = entities["end_time"]
    elif entities.get("duration"):
        start_dt = datetime.fromisoformat(target_task.start_time)
        end_dt = start_dt.replace(minute=start_dt.minute + entities["duration"])
        update_data["end_time"] = end_dt.isoformat()

    if entities.get("priority"):
        update_data["priority"] = entities["priority"]

    if entities.get("status"):
        update_data["status"] = entities["status"]

    if len(update_data) <= 2:  # 只有 task_id 和 user_id
        return {
            "reply": f"{user_nickname}，请告诉我你要修改任务的什么内容？（时间/优先级/状态等）",
            "intent": "chat",
            "success": False
        }

    # 调用 ActionExecutor 执行修改
    print(f"🔧 调用 ActionExecutor 修改任务: {update_data}")
    action_result = executor.execute("modify_task", update_data)

    if action_result.get('success'):
        task = action_result.get('task', {})
        reply = f"{user_nickname}，已帮你把「{task.get('title')}」"

        if "start_time" in update_data and "end_time" in update_data:
            reply += f"的时间修改为{task.get('start_time', '')[11:16]}-{task.get('end_time', '')[11:16]}"
        elif "priority" in update_data:
            priority_map = {"high": "高", "medium": "中", "low": "低"}
            reply += f"的优先级修改为{priority_map.get(task.get('priority'), task.get('priority'))}"
        elif "status" in update_data:
            status_map = {"pending": "待完成", "done": "已完成", "cancelled": "已取消"}
            reply += f"的状态修改为{status_map.get(task.get('status'), task.get('status'))}"

        reply += "啦！"

        return {
            "reply": reply,
            "intent": "modify_task",
            "success": True,
            "data": action_result
        }
    else:
        return {
            "reply": f"{user_nickname}，修改任务时出错了：{action_result.get('error', '未知错误')}",
            "intent": "modify_task",
            "success": False
        }


def _handle_delete_task_conversation(
    message: str,
    user_id: int,
    entities: Dict[str, Any],
    user_nickname: str,
    assistant_nickname: str
) -> Dict[str, Any]:
    """处理删除任务的对话"""

    task_title = entities.get("title")

    if not task_title:
        return {
            "reply": f"{user_nickname}，请告诉我你要删除哪个任务？",
            "intent": "chat",
            "success": False
        }

    # 查找任务
    all_tasks = get_all_tasks(user_id)
    target_task = None

    for task in all_tasks:
        if task.title and task_title.lower() in task.title.lower():
            target_task = task
            break

    if not target_task:
        return {
            "reply": f"{user_nickname}，我没有找到名为「{task_title}」的任务哦～",
            "intent": "chat",
            "success": False
        }

    # 调用 ActionExecutor 执行删除
    print(f"🗑️ 调用 ActionExecutor 删除任务: {target_task.id}")
    action_result = executor.execute("delete_task", {
        "task_id": target_task.id,
        "user_id": user_id
    })

    if action_result.get('success'):
        deleted_title = action_result.get('deleted_task_title', task_title)
        return {
            "reply": f"{user_nickname}，任务「{deleted_title}」已删除！🗑️",
            "intent": "delete_task",
            "success": True,
            "data": action_result
        }
    else:
        return {
            "reply": f"{user_nickname}，删除任务时出错了：{action_result.get('error', '未知错误')}",
            "intent": "delete_task",
            "success": False
        }


def _generate_reply_from_data(
    action_name: str,
    action_result: Dict[str, Any],
    user_nickname: str,
    assistant_nickname: str,
    memory_context: str = ""
) -> str:
    """
    根据动作执行结果生成自然语言回复
    """
    
    print(f"📊 _generate_reply_from_data 收到 action_result: {action_result.keys()}")

    #  策略 1: 对于简单查询，使用模板（快速）
    if action_name == "query_today_tasks":
        # 检查是否超出范围（不依赖 success 字段）
        out_of_range = action_result.get('out_of_range', False)
        print(f"🔍 检查 out_of_range: {out_of_range}, type: {type(out_of_range)}")
        
        if out_of_range:
            date_desc = action_result.get('date_description', '')
            message = action_result.get('message', '超出查询范围')
            
            print(f"🚫 检测到超出范围: date_description='{date_desc}'")
            print(f" 匹配的 date_desc: '{date_desc}'")
            
            #  个性化超出范围回复
            if "四天前" in date_desc or "4天前" in date_desc:
                print(f"✅ 匹配到'四天前'规则")
                reply = f"{user_nickname}，4天前的任务已经超出我的查询范围啦～\n"
                reply += "我目前支持查询3天内的任务哦（大前天～大后天）\n\n"
                reply += "💡 建议：\n"
                reply += "1. 使用任务列表的搜索功能查找历史记录 🔍\n"
                reply += "2. 问我今天/昨天/明天的任务\n"
                reply += "3. 查看本周的工作报告 📊"
            elif "五天前" in date_desc or "5天前" in date_desc:
                reply = f"{user_nickname}，5天前的任务可能有点久远啦～\n"
                reply += "我目前支持查询3天内的任务哦（大前天～大后天）\n\n"
                reply += "💡 如果想查看更早的任务，可以：\n"
                reply += "1. 使用任务列表的搜索功能 🔍\n"
                reply += "2. 问我今天/昨天/明天的任务\n"
            elif "上周" in date_desc:
                reply = f"{user_nickname}，上周的任务已经超出我的查询范围啦～\n"
                reply += "我目前只能查询前后3天的任务哦\n\n"
                reply += "📌 建议：\n"
                reply += "• 去任务列表用搜索功能查找\n"
                reply += "• 或者查看本周的工作报告 📊"
            elif "10天" in date_desc or "十天前" in date_desc:
                reply = f"{user_nickname}，10天前的任务太久远啦，我查不到哦～\n"
                reply += "🔍 请使用任务列表的搜索功能来查找历史记录吧！"
            elif "上个月" in date_desc or "上月" in date_desc:
                reply = f"{user_nickname}，上个月的任务已经超过我的能力范围啦～\n"
                reply += "💪 试试任务列表的搜索功能，可以找到所有历史记录哦！"
            else:
                # 通用超出范围回复
                print(f"ℹ️ 使用通用超出范围回复")
                reply = f"{user_nickname}，{message}\n\n"
                reply += "我目前支持查询：\n"
                reply += "• 今天、昨天、明天\n"
                reply += "• 前天、大前天\n"
                reply += "• 后天、大后天\n\n"
                reply += "🔍 如需查看更早的任务，请使用任务列表的搜索功能～"
            
            print(f"✅ 生成超出范围回复，长度: {len(reply)}")
            return reply
        
        print(f"ℹ️ 未检测到超出范围，继续正常流程")
        
        task_count = action_result.get('count', 0)
        tasks = action_result.get('tasks', [])
        date_desc = action_result.get('date_description', '今天')
        target_date = action_result.get('date', '')

        #  个性化：无任务时的回复
        if task_count == 0:
            # 根据日期类型给出不同的回复
            if date_desc == "今天":
                return f"{user_nickname}，今天还没有安排任务哦～要不要添加一些计划呢？😊"
            elif date_desc == "明天":
                return f"{user_nickname}，明天还是空白的一天呢～可以好好规划一下！📝"
            elif date_desc == "昨天":
                return f"{user_nickname}，昨天没有任何任务记录，是不是休息了一天呀？"
            elif "前天" in date_desc or "大前天" in date_desc:
                return f"{user_nickname}，{date_desc}没有任务哦，可能数据比较久远啦～"
            else:
                return f"{user_nickname}，{date_desc}这天没有安排任务呢～"

        #  有任务时的回复
        reply = f"{user_nickname}，{date_desc}有 {task_count} 个任务："
        
        # 显示前3个任务的详情
        for idx, task in enumerate(tasks[:3], 1):
            time_str = task.get('start_time', 'N/A')[11:16] if task.get('start_time') else '未安排'
            status_icon = "⚠️ " if task.get('status') == 'overdue' else ""
            reply += f"\n{idx}. {status_icon}{task['title']} ({time_str})"

        # 如果任务超过3个，提示还有更多
        if task_count > 3:
            reply += f"\n...还有 {task_count - 3} 个任务"

        reply += "\n加油哦！"
        return reply

    elif action_name == "analyze_workload":
        analysis = action_result.get('analysis', {})
        density = analysis.get('density_percent', 0)
        task_count = analysis.get('task_count', 0)
        label = analysis.get('day_label', '本周')

        if density < 30:
            return f"{user_nickname}，{label}工作量很轻松呢（{density:.0f}%）！{task_count}个任务，可以适当安排更多事情～"
        elif density < 70:
            return f"{user_nickname}，{label}工作量适中（{density:.0f}%），{task_count}个任务，继续加油！"
        else:
            return f"{user_nickname}，{label}安排得很满（{density:.0f}%）！记得适当休息哦～"

    elif action_name == "query_free_time":
        analysis = action_result.get('analysis', {})
        free_hours = analysis.get('free_hours', 0)
        task_count = analysis.get('task_count', 0)
        label = analysis.get('day_label', '明天')

        if free_hours >= 8:
            return f"{user_nickname}，{label}超闲的诶！{free_hours:.0f}小时空闲，只有{task_count}个任务，可以去放松一下啦～☕"
        elif free_hours >= 4:
            return f"{user_nickname}，{label}有{free_hours:.0f}小时空闲，{task_count}个任务，时间还挺充裕的～"
        else:
            return f"{user_nickname}，{label}比较忙，只有{free_hours:.0f}小时空闲，注意休息哦～"

    elif action_name == "generate_report":
        report_data = action_result.get('report_data', {})
        completion_rate = report_data.get('completion_rate', '0%')
        total = report_data.get('total_tasks', 0)
        completed = report_data.get('completed_tasks', 0)
        overdue = report_data.get('overdue_tasks', 0)
        period = report_data.get('period', '本周')

        reply = f"{user_nickname}，{period}工作报告来啦！"
        reply += f"完成了{completed}/{total}个任务，完成率{completion_rate}。"

        if overdue > 0:
            reply += f"有{overdue}个任务已超时，记得抽空处理哦～"

        reply += "继续加油，完整报告可以随时查看！📊"
        return reply

    # ⭐ 策略 2: 其他复杂情况，调用 LLM 生成
    else:
        try:
            client = get_deepseek_client()

            system_prompt = f"""你是用户的私人助理「{assistant_nickname}」，用户叫「{user_nickname}」。
请根据以下数据生成一段亲切的回复（80字以内）。

【长期记忆】
{memory_context if memory_context else "无"}
"""

            user_message = f"数据：{str(action_result)}"

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=100,
                timeout=15
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"⚠️ LLM 回复生成失败: {e}")
            return f"{user_nickname}，我已经处理了你的请求，请查看结果。"


def _adapt_params_for_action(action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    参数适配器：将 LLM 的输出转换为动作所需的参数格式
    
    这是因为 LLM 可能返回不同的字段名，需要统一映射
    """
    adapted = params.copy()
    
    if action_name == "query_free_time":
        # 如果 LLM 返回了 date，转换为 time_range
        if adapted.get('date'):
            date_str = adapted['date']
            today = datetime.now().strftime("%Y-%m-%d")
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            day_after = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
            
            if date_str == today:
                adapted['time_range'] = 'today'
            elif date_str == tomorrow:
                adapted['time_range'] = 'tomorrow'
            elif date_str == day_after:
                adapted['time_range'] = 'day_after_tomorrow'
            else:
                # 默认使用 tomorrow
                adapted['time_range'] = 'tomorrow'
            
            # 移除 date 字段
            adapted.pop('date', None)
        
        # 确保有默认值
        if not adapted.get('time_range'):
            adapted['time_range'] = 'tomorrow'
        if not adapted.get('activity'):
            adapted['activity'] = 'rest'
    
    elif action_name == "query_today_tasks":
        # ⭐ 修复：强制移除 LLM 错误设置的 date 字段
        if adapted.get('date'):
            print(f"️ 检测到 LLM 错误设置了 date='{adapted['date']}'，将被移除")
            adapted.pop('date', None)
        
        # 使用 date_description 解析日期
        if not adapted.get('date'):
            date_description = adapted.get('date_description')
            
            if date_description:
                # 导入 parse_relative_date 函数
                from app.services.action_executor import parse_relative_date
                adapted['date'] = parse_relative_date(date_description)
                print(f"🔧 参数适配：date_description='{date_description}' → date='{adapted['date']}'")
            else:
                # 没有 date_description 才使用今天
                adapted['date'] = datetime.now().strftime("%Y-%m-%d")
                print(f"🔧 参数适配：无 date_description，使用今天")
    
    elif action_name == "analyze_workload":
        # 确保有 time_range
        if not adapted.get('time_range'):
            adapted['time_range'] = 'this_week'
    
    return adapted


@router.post("/send", response_model=dict)
async def send_message(request: ChatRequest):
    """
    重构版聊天接口 - 使用 ActionExecutor
    
    流程：
    1. LLM 识别意图 -> 得到 action_name + params
    2. ActionExecutor 执行动作 -> 得到 result_data
    3. LLM 根据 result_data 生成回复 -> 返回给用户
    """
    message = request.message
    user_id = request.user_id
    
    print(f"\n{'=' * 60}")
    print(f"📨 [V2] 收到消息: '{message}' (user_id={user_id})")
    print(f"{'=' * 60}\n")
    
    try:
        # 获取用户偏好
        prefs = get_user_preferences(user_id)
        prefs_dict = prefs.to_dict() if prefs else {}
        user_nickname = prefs_dict.get("user_nickname", "你")
        assistant_nickname = prefs_dict.get("assistant_nickname", "助手")
        
        # 获取长期记忆上下文（简化版）
        memory_context = ""
        
        # ⭐ 优先检查：是否有待处理的任务创建上下文
        pending_task = task_context_manager.get(user_id)
        if pending_task:
            print(f"🔄 检测到待处理任务上下文")
            
            # ⭐ 优化：先调用意图引擎识别意图，判断是否是新任务
            print(f"🤖 调用意图引擎识别用户意图...")
            intent_result = intent_parser.parse(message)
            action_name = intent_result.intent
            params = intent_result.entities
            
            print(f"🔍 意图引擎识别结果: action={action_name}, entities={params}, source={intent_result.source}")
            
            # 如果 LLM 识别到是新任务（add_task），且标题不同，清除旧上下文
            if action_name == "add_task" and params.get("title"):
                old_title = pending_task.get('task_info', {}).get('title', '')
                new_title = params.get("title")
                
                if new_title != old_title:
                    print(f"🔄 检测到新任务请求，清除旧上下文: {old_title} -> {new_title}")
                    task_context_manager.clear(user_id)
                    # 继续处理新任务（走下面的新任务创建流程）
                else:
                    print(f"⚠️ 同一任务，继续待确认流程")
                    result = _handle_add_task_conversation(
                        message=message,
                        user_id=user_id,
                        entities=params,  #  使用 LLM 识别的 entities
                        user_nickname=user_nickname,
                        assistant_nickname=assistant_nickname
                    )
                    return result
            else:
                #  关键修复：如果不是 add_task 意图，清除旧上下文，执行新意图
                print(f"🔄 检测到其他意图 ({action_name})，清除旧任务上下文")
                task_context_manager.clear(user_id)
                # 不 return，继续走下面的正常流程处理新意图


        # ==================== 步骤 1: 意图引擎识别意图 ====================
        print(f"🤖 步骤1: 意图引擎识别...")
        intent_result = intent_parser.parse(message)
        action_name = intent_result.intent
        params = intent_result.entities
        
        print(f"✅ 识别结果: action={action_name}, confidence={intent_result.confidence}, source={intent_result.source}")
        
        # ⭐ 特殊处理：chat 意图不需要执行动作
        if action_name == "chat":
            print(f"💬 检测到日常聊天，直接生成回复")
            reply = _generate_chat_reply(
                user_id=user_id,
                user_message=message,
                user_nickname=user_nickname,
                assistant_nickname=assistant_nickname,
                memory_context=memory_context
            )
            return {
                "reply": reply,
                "intent": "chat",
                "success": True
            }
        
        # ⭐ 特殊处理：add_task 需要多轮对话管理
        if action_name == "add_task":
            print(f"➕ 检测到添加任务，进入多轮对话模式")
            result = _handle_add_task_conversation(
                message=message,
                user_id=user_id,
                entities=params,
                user_nickname=user_nickname,
                assistant_nickname=assistant_nickname
            )
            return result
        
        # ⭐ 特殊处理：modify_task 需要先查找任务
        if action_name == "modify_task":
            print(f"✏️ 检测到修改任务，进入任务查找流程")
            result = _handle_modify_task_conversation(
                message=message,
                user_id=user_id,
                entities=params,
                user_nickname=user_nickname,
                assistant_nickname=assistant_nickname
            )
            return result
        
        # ⭐ 特殊处理：delete_task 需要先查找任务
        if action_name == "delete_task":
            print(f"️ 检测到删除任务，进入任务查找流程")
            result = _handle_delete_task_conversation(
                message=message,
                user_id=user_id,
                entities=params,
                user_nickname=user_nickname,
                assistant_nickname=assistant_nickname
            )
            return result
        
        # ⭐ 特殊处理：generate_report 使用异步任务队列
        if action_name == "generate_report":
            print(f"📊 检测到生成周报，使用异步任务队列...")
            
            # 导入任务队列
            from app.services.cache_service import redis_cache
            from app.services.task_queue import task_queue
            
            if redis_cache.enabled:
                # ⭐ 防止重复提交：检查是否已有正在处理的周报任务
                report_submit_key = f"report_submitting:{user_id}:{params.get('time_range', 'this_week')}"
                is_submitting = redis_cache.get(report_submit_key)
                
                if is_submitting:
                    print(f"⚠️ 该用户的{params.get('time_range', 'this_week')}周报正在生成中，跳过重复提交")
                    return {
                        "reply": f"{user_nickname}，你的周报正在生成中，请稍等片刻～",
                        "intent": "generate_report",
                        "success": True,
                        "already_processing": True
                    }
                
                # 标记为正在生成（5分钟过期，防止任务卡死）
                redis_cache.set(report_submit_key, True, ttl=300)
                
                # 提交异步任务
                task_id = task_queue.enqueue("generate_report", {
                    "user_id": user_id,
                    "time_range": params.get('time_range', 'this_week')
                })
                
                print(f"✅ 周报生成任务已提交 (task_id={task_id})")
                
                # 立即返回提示消息
                return {
                    "reply": f"{user_nickname}，周报生成任务已提交～\n"
                             f"完整报告（包含图表和详细分析）将通过 WebSocket 推送给你，请稍等片刻！",
                    "intent": "generate_report",
                    "success": True,
                    "task_id": task_id,
                    "async": True
                }
            else:
                print(f"⚠️ Redis 未启用，降级为同步模式")
                # 降级：使用原有的同步逻辑（不做修改）
        
        # 参数适配：将 LLM 输出转换为动作所需格式

        params = _adapt_params_for_action(action_name, params)


        # 添加 user_id 到参数中
        params['user_id'] = user_id

        print(f"✅ 识别结果: action={action_name}, params={params}")

        # ==================== 步骤 2: ActionExecutor 执行动作 ====================
        print(f" 步骤2: 执行动作 '{action_name}'...")
        action_result = executor.execute(action_name, params)

        if not action_result.get('success'):
            print(f"❌ 动作执行失败: {action_result.get('error')}")
            return {
                "reply": f"{user_nickname}，抱歉，处理你的请求时出错了：{action_result.get('error', '未知错误')}",
                "intent": action_name,
                "success": False
            }

        print(f"✅ 动作执行成功")

        # ==================== 步骤 3: LLM 生成自然语言回复 ====================
        print(f"💬 步骤3: LLM 生成回复...")

        # 根据动作结果生成回复
        reply = _generate_reply_from_data(
            action_name=action_name,
            action_result=action_result,
            user_nickname=user_nickname,
            assistant_nickname=assistant_nickname,
            memory_context=memory_context
        )

        print(f"✅ 回复生成完成，长度: {len(reply)}")

        return {
            "reply": reply,
            "intent": action_name,
            "success": True,
            "data": action_result  # 前端可以使用结构化数据
        }

    except Exception as e:
        print(f"⚠️ 聊天处理总异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "reply": f"系统出了点小问题，请稍后再试～",
            "intent": "error",
            "success": False
        }


# ==================== 助手精灵问候接口 ====================
@router.post("/assistant/daily-greeting", response_model=dict)
async def get_daily_greeting(request: GreetingRequest):
    """生成每日助手精灵问候语"""
    try:
        from datetime import date

        user_id = request.user_id
        today = date.today().isoformat()
        hour = datetime.now().hour

        prefs = get_user_preferences(user_id)
        user_nickname = prefs.user_nickname if prefs and prefs.user_nickname else "彦祖"

        all_tasks = get_all_tasks(user_id)
        today_tasks = [t for t in all_tasks if t.start_time and t.start_time[:10] == today]

        total = len(today_tasks)
        done = len([t for t in today_tasks if t.status == 'done'])
        pending = total - done

        # 优化问候语逻辑
        if total == 0:
            # 没有任务
            if hour < 12:
                message = f"早上好 {user_nickname}！今天还没有安排任务呢，要不要先规划一下？☀️"
            elif hour < 18:
                message = f"{user_nickname}下午好！今天还没有任务安排，要添加一些吗？☕"
            else:
                message = f"{user_nickname}晚上好！今天还没安排任务呢，明天要加油哦~🌙"
            sprite_emoji = "🤔"

        elif done == 0:
            # 有任务但还没开始
            if hour < 12:
                message = f"{user_nickname}早上好！今天有 {total} 个任务等你完成，开始行动吧！🚀"
            elif hour < 18:
                message = f"{user_nickname}下午好！今天还有 {total} 个任务，抓紧时间哦～⏰"
            else:
                message = f"{user_nickname}晚上好！今天还有 {total} 个任务没完成，要加油啦～💪"
            sprite_emoji = "💪"

        elif done == total:
            # 全部完成
            if hour < 12:
                message = f"哇塞 {user_nickname}！一上午就搞定所有任务了，效率超高~ 🎉"
            elif hour < 18:
                message = f"{user_nickname}太棒了！所有任务都完成了，可以好好放松啦~ ✨"
            else:
                message = f"{user_nickname}今天真厉害，所有任务都完成啦！晚安~😴"
            sprite_emoji = "😄"

        else:
            # 部分完成
            progress = int(done / total * 100)

            if progress < 30:
                message = f"{user_nickname}加油！已完成 {done}/{total} 个任务 ({progress}%)，下午继续努力哦～💪"
                sprite_emoji = "💪"
            elif progress < 70:
                message = f"{user_nickname}不错哦！已完成 {done}/{total} 个任务 ({progress}%)，继续保持～✨"
                sprite_emoji = "😊"
            else:
                message = f"{user_nickname}太棒了！已完成 {done}/{total} 个任务 ({progress}%)，马上就能全部完成啦！"
                sprite_emoji = "🎉"

        return {
            "success": True,
            "message": message,
            "stats": {
                "total": total,
                "done": done,
                "pending": pending,
                "progress": int(done / total * 100) if total > 0 else 0
            },
            "sprite_emoji": sprite_emoji
        }

    except Exception as e:
        print(f"❌ 生成问候语失败: {e}")
        return {
            "success": False,
            "message": "精灵好像睡着了...请稍后再试~",
            "stats": {"total": 0, "done": 0, "pending": 0, "progress": 0},
            "sprite_emoji": "😴"
        }

