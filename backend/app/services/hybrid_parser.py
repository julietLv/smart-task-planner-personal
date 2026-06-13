# backend/app/services/intent_engine/hybrid_parser.py
from .base import IIntentParser, IntentResult, ParserSource
from .llm_parser import LLMIntentParser
from .rule_parser import RuleIntentParser

class HybridIntentParser(IIntentParser):
    """混合解析器 - LLM优先 → 规则兜底 → 统计优化"""
    
    def __init__(self):
        self.llm_parser = LLMIntentParser()
        self.rule_parser = RuleIntentParser()
        self.fallback_count = 0
    
    def parse(self, user_input: str) -> IntentResult:
        # 策略1: 优先使用 LLM
        llm_result = self.llm_parser.parse(user_input)
        
        # ⭐ 调整：只要有 intent 且没有 error，就接受 LLM 结果
        if llm_result.intent != 'chat' and not llm_result.error:
            print(f"✅ LLM 识别成功: {llm_result.intent} (confidence={llm_result.confidence})")
            return llm_result
        
        # 如果是 chat 意图，也接受（可能是真正的闲聊）
        if llm_result.intent == 'chat' and not llm_result.error:
            print(f"💬 LLM 判断为闲聊")
            return llm_result
        
        # 策略2: LLM 失败时降级到规则
        print(f"⚠️ LLM 解析失败({llm_result.error})，降级到规则引擎")
        rule_result = self.rule_parser.parse(user_input)
        
        # 统计降级频率（用于后续优化）
        self.fallback_count += 1
        if self.fallback_count % 100 == 0:
            print(f"📊 LLM 降级次数: {self.fallback_count}")
        
        return rule_result
