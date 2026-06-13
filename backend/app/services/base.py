# backend/app/services/intent_engine/base.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional

class ParserSource(Enum):
    LLM = "llm"
    RULE = "rule"
    HYBRID = "hybrid"

@dataclass
class IntentResult:
    intent: str
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    source: ParserSource = ParserSource.RULE
    error: Optional[str] = None

class IIntentParser:
    """意图解析器接口"""
    def parse(self, user_input: str) -> IntentResult:
        raise NotImplementedError
