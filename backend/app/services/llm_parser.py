# backend/app/services/intent_engine/llm_parser.py
import json
from .base import IIntentParser, IntentResult, ParserSource
from app.services.llm_service import _parse_with_llm  # 复用现有逻辑

class LLMIntentParser(IIntentParser):
    """LLM 意图解析器"""
    def parse(self, user_input: str) -> IntentResult:
        try:
            result = _parse_with_llm(user_input)
            
            # ⭐ 关键修复：LLM 返回的可能是 JSON 字符串，需要解析
            if isinstance(result, str):
                print(f"🔍 LLM 返回字符串，尝试解析 JSON...")
                # 清理 Markdown 标记
                result = result.strip()
                if result.startswith("``"):
                    result = result[2:-2]
                try:
                    result = json.loads(result)
                except json.JSONDecodeError as e:
                    print(f"❌ JSON 解析异常: {e}")
                    import traceback
                    traceback.print_exc()
                    return IntentResult(
                        intent='chat',
                        entities={},
                        confidence=0.0,
                        source=ParserSource.LLM,
                        error=str(e)
                    )

            # ⭐ 调试日志：打印 LLM 原始返回
            print(f"🔍 LLM 原始返回: {result}")
            
            return IntentResult(
                intent=result.get('intent', 'chat'),
                entities=result.get('entities', {}),
                confidence=result.get('confidence', 0.9),  # 默认高置信度
                source=ParserSource.LLM
            )
        except Exception as e:
            print(f"❌ LLM 解析异常: {e}")
            import traceback
            traceback.print_exc()
            return IntentResult(
                intent='chat',
                entities={},
                confidence=0.0,
                source=ParserSource.LLM,
                error=str(e)
            )
