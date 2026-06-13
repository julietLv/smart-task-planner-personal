# D:\demo_plan\backend\app\services\intent_engine\__init__.py
"""意图识别引擎 - 多层架构

架构设计：
  Layer 1: LLM解析器（精准，处理复杂语义）
  Layer 2: 规则解析器（快速，处理高频模式）
  Layer 3: 混合解析器（LLM优先 → 规则兜底 → 统计优化）

使用方式：
  from app.services.intent_engine import HybridIntentParser

  parser = HybridIntentParser()
  result = parser.parse(user_input)
  # result.intent, result.entities, result.confidence, result.source
"""

from .base import IntentResult, IIntentParser, ParserSource
from .llm_parser import LLMIntentParser
from .rule_parser import RuleIntentParser
from .hybrid_parser import HybridIntentParser

__all__ = [
    "IntentResult",
    "IIntentParser",
    "ParserSource",
    "LLMIntentParser",
    "RuleIntentParser",
    "HybridIntentParser",
]
