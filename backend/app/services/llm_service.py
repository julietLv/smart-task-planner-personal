"""LLM 服务 - DeepSeek API 集成"""
import os
import json
import re
from typing import Dict, Any
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv

# 确保环境变量已加载
load_dotenv()


def get_deepseek_client() -> OpenAI:
    """
    创建 DeepSeek API 客户端

    Returns:
        OpenAI 客户端实例
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("⚠️ 警告: DEEPSEEK_API_KEY 未设置！请检查 backend/.env 文件")
        raise ValueError("环境变量 DEEPSEEK_API_KEY 未设置")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )
    return client


def parse_user_intent(user_input: str) -> Dict[str, Any]:
    """
    使用 DeepSeek API 解析用户意图（LLM优先 → 规则兜底）

    Args:
        user_input: 用户的自然语言输入

    Returns:
        包含意图和实体的结构化字典
    """
    # ⭐ 预处理：检测 "YYYY/MM/DD HH:MM, task_name" 或 "YYYY-MM-DD HH:MM, task_name" 格式
    # 这种格式LLM容易丢失标题，先提取出来备用
    import re as re_module
    pre_extracted_title = None
    date_prefix_match = re_module.match(
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2}\s+\d{1,2}:\d{2})\s*[,，]\s*(.+)',
        user_input
    )
    if date_prefix_match:
        pre_extracted_title = date_prefix_match.group(2).strip()
        print(f"🔍 预处理提取到标题: '{pre_extracted_title}'")
    # Layer 1: 尝试 LLM 解析
    try:
        result = _parse_with_llm(user_input)
        
        # ⭐ 关键修复：确保返回的是字典而不是字符串
        if isinstance(result, str):
            print(f"⚠️ LLM 返回了字符串，尝试解析...")
            # 清理 Markdown 标记
            result = result.strip()
            if result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()
            
            # 尝试解析 JSON
            try:
                result = json.loads(result)
                print(f"✅ 成功将字符串解析为字典")
            except json.JSONDecodeError as e:
                print(f"❌ JSON 解析失败: {e}")
                print(f" 原始字符串: {result[:200]}")
                # 降级到规则引擎
                return _parse_with_rules(user_input)
        
        # 确保返回的是字典
        if isinstance(result, dict):
            # ⭐ 修正：如果LLM返回的title是"新任务"但预处理提取到了标题，用预处理标题覆盖
            if pre_extracted_title and result.get("entities", {}).get("title") in ("新任务", None, ""):
                result.setdefault("entities", {})["title"] = pre_extracted_title
                print(f"🔧 已修正标题: '新任务' → '{pre_extracted_title}'")
            # ⭐ Phase 1: 数据打通 - 从学习引擎补充缺失信息
            result = _enrich_with_learned_habits(result, user_input)
            return result
        else:
            print(f"️ LLM 返回了非字典类型: {type(result)}")
            return _parse_with_rules(user_input)
            
    except Exception as e:
        print(f"⚠️ LLM 调用失败，降级到规则引擎: {e}")
        import traceback
        traceback.print_exc()
        # Layer 2: 规则兜底
        return _parse_with_rules(user_input)


def _parse_with_llm(user_input: str) -> Dict[str, Any]:
    """LLM 解析（原 parse_user_intent 逻辑）⭐ 已优化：增加 Redis 缓存"""
    from app.services.cache_service import redis_cache
    import hashlib
    
    # ⭐ 生成缓存键（基于用户输入的哈希）
    cache_key = f"llm:parse:{hashlib.md5(user_input.encode('utf-8')).hexdigest()}"
    
    # ⭐ 先尝试从 Redis 获取缓存
    cached_result = redis_cache.get(cache_key)
    if cached_result:
        print(f"✅ LLM 缓存命中，节省 Token: {user_input[:50]}...")
        return cached_result
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_weekday = datetime.now().strftime("%A")
    weekday_map = {
        "Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
        "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"
    }
    current_weekday_cn = weekday_map.get(current_weekday, current_weekday)

    yesterday_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    day_after_tomorrow_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    
    query_range_start = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    query_range_end = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")

    system_prompt = f"""你是一个智能任务规划助手的意图识别引擎。请分析用户输入，识别其意图并提取相关实体。

当前时间: {current_datetime}
今天是: {current_weekday_cn}

##  日期查询范围限制（重要）：
- **可查询范围**: {query_range_start} 至 {query_range_end}（前后3天）
- **支持的自然语言表达**:
  - "今天" → {current_date}
  - "昨天" → {yesterday_date}
  - "前天" → {(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")}
  - "大前天" → {(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")}
  - "明天" → {tomorrow_date}
  - "后天" → {day_after_tomorrow_date}
  - "大后天" → {(datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")}
- **超出范围的表达**（out_of_range: true）:
  - "五天前"、"上周三"、"10天前"等
  - 提示用户使用任务列表搜索功能

##  日期查询核心规则（必须遵守）：
- **对于 query_today_tasks 意图**：
  - ✅ **必须返回** `date_description`（如"昨天"、"明天"）
  - ❌ **禁止返回** `date` 字段（后端会自动解析 date_description）
  - ✅ **必须判断** `out_of_range`（true/false）
  - ✅ **规范化表达**：
    - "前第四天" → "四天前"
    - "前第N天" → "N天前"
    - "后第N天" → "N天后"

## 🚨 核心指令（必须遵守）：
1. **时间提取优先**：如果用户提到了具体时间点（如"明天9点"、"下午3点半"），你**必须**计算出对应的 ISO 8601 格式字符串填入 `start_time` 和 `end_time`。
2. **不要依赖后端排程**：如果用户指定了时间，不要只返回 duration，要返回精确的 start_time/end_time。
3. **时长推断**：如果用户没说时长，根据活动类型推断（开会30-60min，评审60-90min）。

## 📝 实体字段说明：
- title: 任务标题
- **start_time**: 开始时间（ISO 8601，例: "{tomorrow_date}T09:00:00"）⭐ 关键
- **end_time**: 结束时间（ISO 8601，例: "{tomorrow_date}T09:30:00"）⭐ 关键
- duration: 预估时长（分钟，整数）
- priority: 优先级 ("high" | "medium" | "low")
- deadline: 截止日期

## 💡 学习示例（严格按此格式输出）：

用户输入："明天早上9点开个早会，预计30分钟"
返回：
{{
    "intent": "add_task",
    "entities": {{
        "title": "早会",
        "start_time": "{tomorrow_date}T09:00:00",
        "end_time": "{tomorrow_date}T09:30:00",
        "duration": 30,
        "priority": "high"
    }},
    "confidence": 0.99
}}

用户输入："明天早上9点15分产品评审，需要1小时"
返回：
{{
    "intent": "add_task",
    "entities": {{
        "title": "产品评审",
        "start_time": "{tomorrow_date}T09:15:00",
        "end_time": "{tomorrow_date}T10:15:00",
        "duration": 60,
        "priority": "medium"
    }},
    "confidence": 0.99
}}

用户输入："今天下午3点有个面试"
返回：
{{
    "intent": "add_task",
    "entities": {{
        "title": "面试",
        "start_time": "{datetime.now().strftime('%Y-%m-%d')}T15:00:00",
        "end_time": "{datetime.now().strftime('%Y-%m-%d')}T16:00:00",
        "duration": 60,
        "priority": "high"
    }},
    "confidence": 0.99
}}

用户输入："帮我生成周报"
返回：
{{
    "intent": "generate_report",
    "entities": {{
        "time_range": "this_week"
    }},
    "confidence": 0.99
}}

用户输入："生成上周的工作报告"
返回：
{{
    "intent": "generate_report",
    "entities": {{
        "time_range": "last_week"
    }},
    "confidence": 0.99
}}

用户输入："本月的总结报告"
返回：
{{
    "intent": "generate_report",
    "entities": {{
        "time_range": "this_month"
    }},
    "confidence": 0.99
}}

用户输入："昨天有什么任务？"
返回：
{{
    "intent": "query_today_tasks",
    "entities": {{
        "date_description": "昨天",
        "out_of_range": false
    }},
    "confidence": 0.99
}}

用户输入："大前天呢？"
返回：
{{
    "intent": "query_today_tasks",
    "entities": {{
        "date_description": "大前天",
        "out_of_range": false
    }},
    "confidence": 0.99
}}

用户输入："五天前呢"
返回：
{{
    "intent": "query_today_tasks",
    "entities": {{
        "date_description": "五天前",
        "out_of_range": true,
        "reason": "超出前后3天查询范围"
    }},
    "confidence": 0.99
}}

用户输入："上周三的任务"
返回：
{{
    "intent": "query_today_tasks",
    "entities": {{
        "date_description": "上周三",
        "out_of_range": true,
        "reason": "超出前后3天查询范围"
    }},
    "confidence": 0.99
}}

##  支持的意图类型（动作映射）：
1. add_task - 添加任务（含具体时间或自动排程）
2. query_today_tasks - 查询今日/指定日期任务列表 ⭐
   - 示例："今天我有什么任务？"、"明天的任务列表"、"查看本周任务"
3. query_free_time - 查询空闲时间
4. analyze_workload - 分析工作负载
5. modify_task - 修改任务
6. delete_task - 删除任务
7. set_preference - 设置偏好
8. chat - 普通聊天
9. generate_report - 生成报告（周报、月报等）

## 💡 意图映射说明：
- 当用户问"今天我有什么任务？"、"查看任务"时，使用 query_today_tasks
- 当用户问"我有空吗？"、"有时间运动吗？"时，使用 query_free_time
- 当用户说"添加任务"、"安排会议"时，使用 add_task

请只返回 JSON 格式，不要包含 Markdown 标记。
"""

    client = get_deepseek_client()
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        temperature=0.3,
        max_tokens=500,
        timeout=45,
        response_format={"type": "json_object"}
    )
    
    result_text = response.choices[0].message.content.strip()
    
    # ⭐ 清理 Markdown 标记
    if result_text.startswith("```"):
        result_text = result_text[3:]
    if result_text.endswith("```"):
        result_text = result_text[:-3]
    result_text = result_text.strip()
    
    # ⭐ 解析 JSON
    try:
        result = json.loads(result_text)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        print(f"   原始文本: {result_text[:200]}")
        # 降级到规则引擎
        return _parse_with_rules(user_input)
    
    # ⭐ 写入 Redis 缓存（TTL: 10分钟）
    if isinstance(result, dict):
        redis_cache.set(cache_key, result, ttl=600)
        print(f"💾 LLM 响应已缓存: {user_input[:50]}...")
    
    return result


def _parse_with_rules(user_input: str) -> Dict[str, Any]:
    """规则引擎解析（原 parse_user_intent 逻辑）"""
    result = {
        "intent": "chat",
        "entities": {},
        "confidence": 0.0
    }
    
    # ⭐ Phase 1: 数据打通 - 规则引擎也应用习惯增强
    result = _enrich_with_learned_habits(result, user_input)
    return result


def _enrich_with_learned_habits(parsed_result: Dict[str, Any], user_input: str) -> Dict[str, Any]:
    """
    ⭐ Phase 1: 数据打通 - 从学习引擎补充缺失信息
    
    核心逻辑：
    1. 从 NLP 解析结果中提取任务标题
    2. 查询学习引擎中是否有相关习惯
    3. 如果 NLP 结果缺少某些字段，用学习习惯补充
    4. 记录应用的 habit 信息，供前端展示
    
    Args:
        parsed_result: NLP 解析结果（LLM 或规则引擎的输出）
        user_input: 用户原始输入
    
    Returns:
        增强后的解析结果
    """
    try:
        from app.services.scheduler_service import apply_learned_habits, extract_task_keywords
        
        # 只处理 add_task 意图
        if parsed_result.get("intent") != "add_task":
            return parsed_result
        
        entities = parsed_result.get("entities", {})
        task_title = entities.get("title", "")
        
        if not task_title:
            return parsed_result
        
        # 构建临时任务对象，用于调用 apply_learned_habits
        temp_task = {
            "title": task_title,
            "priority": entities.get("priority"),
            "duration": entities.get("duration"),
            "description": entities.get("description", "")
        }
        
        # 调用现有的习惯应用逻辑
        enhanced_task = apply_learned_habits(temp_task, user_id=1)
        
        # 检查是否应用了任何习惯
        applied_habits = enhanced_task.get("applied_habits", [])
        
        if applied_habits:
            print(f"✨ [Phase 1] 应用了 {len(applied_habits)} 个历史习惯:")
            for habit_desc in applied_habits:
                print(f"   - {habit_desc}")
            
            # 将应用的 habit 信息添加到解析结果中
            parsed_result["applied_habits"] = applied_habits
            
            # 更新 entities 中的字段（如果习惯应用了新的值）
            if enhanced_task.get("priority") and not entities.get("priority"):
                entities["priority"] = enhanced_task["priority"]
                print(f"   🔄 补充优先级: {enhanced_task['priority']}")
            
            if enhanced_task.get("duration") and not entities.get("duration"):
                entities["duration"] = enhanced_task["duration"]
                print(f"   🔄 补充时长: {enhanced_task['duration']}分钟")
            
            if enhanced_task.get("description") and not entities.get("description"):
                entities["description"] = enhanced_task["description"]
                print(f"   🔄 补充描述模板")
            
            parsed_result["entities"] = entities
            print(f"✅ [Phase 1] 习惯融合完成")
        
        # ⭐ Phase 2B: 从自然语言中学习新习惯
        _learn_from_natural_language(user_input, task_title, entities)
        
        return parsed_result
        
    except Exception as e:
        # 习惯融合失败不应该阻断主流程，只记录错误
        print(f"⚠️ [Phase 1] 习惯融合失败（不影响主流程）: {e}")
        import traceback
        traceback.print_exc()
        return parsed_result


def _learn_from_natural_language(user_input: str, task_title: str, entities: dict):
    """
    ⭐ Phase 2B: 从自然语言对话中学习新习惯
    
    核心逻辑：
    1. 检测用户输入中的偏好表达（如“我通常...”、“我喜欢...”、“一般...”）
    2. 提取偏好类型和值
    3. 自动记录到学习习惯库
    
    示例：
    - “我通常晚上学习” → 学习“学习”任务的 preferred_time_slot = "evening"
    - “会议一般需要60分钟” → 学习“会议”任务的 preferred_duration = 60
    - “作业都是高优先级” → 学习“作业”任务的 preferred_priority = "high"
    
    Args:
        user_input: 用户原始输入
        task_title: 任务标题
        entities: 解析出的实体
    """
    try:
        from app.services.scheduler_service import remember_user_preference
        import re
        
        # 定义偏好表达模式
        preference_patterns = [
            # 时间段偏好（带捕获组）
            (r"(?:通常|一般|喜欢|习惯).*(?:在|安排)(\d+点|早上|上午|中午|下午|晚上|深夜)", "time_slot", True),
            (r"(早上|上午|中午|下午|晚上|深夜).*?(?:学习|工作|运动|开会|会议)", "time_slot", True),
            
            # 时长偏好（带捕获组）
            (r"(?:需要|预计|大概|一般)(\d+)[\s]*(?:分钟|小时)", "duration", True),
            (r"(?:持续|时长)(\d+)[\s]*(?:分钟|小时)", "duration", True),
            
            # 优先级偏好（无捕获组，只需匹配）
            (r"(?:优先|重要|紧急|高优先级)", "priority_high", False),
            (r"(?:不急|慢慢|低优先级|有空再做)", "priority_low", False),
        ]
        
        # 检测时间段偏好
        time_slot_map = {
            "早上": "morning", "上午": "morning",
            "中午": "noon", "下午": "afternoon",
            "晚上": "evening", "深夜": "night"
        }
        
        for pattern, pref_type, has_group in preference_patterns:
            match = re.search(pattern, user_input)
            if match:
                if pref_type == "time_slot":
                    # 提取时间段
                    if has_group:
                        time_word = match.group(1)
                        time_slot = time_slot_map.get(time_word, time_word)
                    else:
                        # 如果没有捕获组，从整个匹配中提取
                        time_slot = "evening"  # 默认值
                    
                    # 记录学习习惯
                    remember_user_preference(
                        task_title=task_title,
                        adjustment_type="time_period",
                        old_value=None,
                        new_value=time_slot,
                        user_id=1,
                        context={"source": "natural_language", "pattern": pattern}
                    )
                    print(f"🧠 [Phase 2B] 从自然语言学习到: {task_title} → 时间段偏好: {time_slot}")
                
                elif pref_type == "duration":
                    # 提取时长
                    if has_group:
                        duration_str = match.group(1)
                        duration = int(duration_str)
                    else:
                        duration = 60  # 默认值
                    
                    # 如果是“小时”，转换为分钟
                    if has_group and "小时" in match.group(0):
                        duration *= 60
                    
                    # 记录学习习惯
                    remember_user_preference(
                        task_title=task_title,
                        adjustment_type="duration",
                        old_value=None,
                        new_value=duration,
                        user_id=1,
                        context={"source": "natural_language", "pattern": pattern}
                    )
                    print(f"🧠 [Phase 2B] 从自然语言学习到: {task_title} → 时长偏好: {duration}分钟")
                
                elif pref_type == "priority_high":
                    # 记录高优先级偏好
                    remember_user_preference(
                        task_title=task_title,
                        adjustment_type="priority",
                        old_value="medium",
                        new_value="high",
                        user_id=1,
                        context={"source": "natural_language", "pattern": pattern}
                    )
                    print(f"🧠 [Phase 2B] 从自然语言学习到: {task_title} → 优先级偏好: high")
                
                elif pref_type == "priority_low":
                    # 记录低优先级偏好
                    remember_user_preference(
                        task_title=task_title,
                        adjustment_type="priority",
                        old_value="medium",
                        new_value="low",
                        user_id=1,
                        context={"source": "natural_language", "pattern": pattern}
                    )
                    print(f"🧠 [Phase 2B] 从自然语言学习到: {task_title} → 优先级偏好: low")
                
                # 找到一个匹配就退出，避免重复学习
                break
    
    except Exception as e:
        # 学习失败不应该阻断主流程
        print(f"⚠️ [Phase 2B] 从自然语言学习失败（不影响主流程）: {e}")
