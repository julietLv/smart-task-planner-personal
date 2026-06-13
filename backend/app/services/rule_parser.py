# backend/app/services/intent_engine/rule_parser.py
import re
from datetime import datetime, timedelta
from typing import Dict, Any
from .base import IIntentParser, IntentResult, ParserSource

class RuleIntentParser(IIntentParser):
    """规则意图解析器 - 关键词+正则匹配"""
    
    INTENT_PATTERNS = {
        'add_task': r'(添加|创建|新建|安排).*(任务|会议|提醒|约会)',
        'query_today_tasks': r'(今天|明天|后天|昨天|前天).*(任务|安排|日程|计划)',
        'query_free_time': r'(有空|空闲|有时间|能.*吗)',
        'delete_task': r'(删除|移除|取消|删掉).*(任务)',
        'modify_task': r'(修改|调整|更改|改).*(任务|时间|优先级)',
        'generate_report': r'(生成|查看|给我).*(周报|月报|报告|总结)',
        'analyze_workload': r'(工作量|负载|忙不忙|安排.*满)',
        'set_preference': r'(设置|修改|更改).*(偏好|昵称|城市)',
    }
    
    TIME_KEYWORDS = {
        'today': ['今天', '今日'],
        'tomorrow': ['明天', '明日'],
        'day_after_tomorrow': ['后天'],
        'yesterday': ['昨天', '昨日'],
        'day_before_yesterday': ['前天'],
    }
    
    PRIORITY_KEYWORDS = {
        'high': ['紧急', '重要', '高优先级'],
        'medium': ['普通', '一般'],
        'low': ['不急', '低优先级', '有空再做'],
    }
    
    def parse(self, user_input: str) -> IntentResult:
        # 1. 意图识别
        intent = self._match_intent(user_input)
        
        # 2. 实体提取
        entities = self._extract_entities(user_input, intent)
        
        return IntentResult(
            intent=intent,
            entities=entities,
            confidence=0.7 if intent != 'chat' else 0.3,
            source=ParserSource.RULE
        )
    
    def _match_intent(self, text: str) -> str:
        for intent, pattern in self.INTENT_PATTERNS.items():
            if re.search(pattern, text):
                return intent
        return 'chat'
    
    def _extract_entities(self, text: str, intent: str) -> Dict[str, Any]:
        entities = {}
        
        # 提取时间范围
        for time_range, keywords in self.TIME_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                entities['time_range'] = time_range
                break
        
        # 提取优先级
        for priority, keywords in self.PRIORITY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                entities['priority'] = priority
                break
        
        # 提取时长（如"30分钟"、"1小时"）
        duration_match = re.search(r'(\d+)\s*(分钟|小时|h|min)', text)
        if duration_match:
            value = int(duration_match.group(1))
            unit = duration_match.group(2)
            if unit in ['小时', 'h']:
                entities['duration'] = value * 60
            else:
                entities['duration'] = value
        
        # 提取任务标题（简单启发式）
        if intent == 'add_task':
            title_match = re.search(r'(?:添加|创建|安排)\s*(.+?)(?:，|,|预计|需要|$)', text)
            if title_match:
                entities['title'] = title_match.group(1).strip()
        
        # 提取具体时间点（如"9点"、"下午3点半"）
        time_match = re.search(r'(上午|下午|晚上)?\s*(\d{1,2})[:：]?(\d{2})?', text)
        if time_match:
            period = time_match.group(1) or '上午'
            hour = int(time_match.group(2))
            minute = int(time_match.group(3)) if time_match.group(3) else 0
            
            if period == '下午' and hour < 12:
                hour += 12
            elif period == '晚上' and hour < 12:
                hour += 12
            
            entities['hour'] = hour
            entities['minute'] = minute
        
        return entities
