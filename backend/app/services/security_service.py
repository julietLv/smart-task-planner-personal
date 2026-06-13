"""恶意命令检测与安全恢复服务"""
import re
import random
from typing import Dict, Any, List, Tuple


class MaliciousCommandDetector:
    """恶意命令检测器"""

    # SQL 注入关键词（支持大小写和变体）
    SQL_INJECTION_PATTERNS = [
        r'(?i)\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE)\s+(TABLE|DATABASE|INDEX|VIEW)\b',
        r'(?i)\bSELECT\s+.*\s+FROM\b.*\bWHERE\b.*[\'";]',
        r'(?i)UNION\s+(ALL\s+)?SELECT\b',
        r'(?i);\s*(DROP|DELETE|INSERT|UPDATE|ALTER)\b',
        r'(?i)--\s*(DROP|DELETE|INSERT|UPDATE)',
        r"(?i)'\s*OR\s+'1'\s*=\s*'1",
        r"(?i)'\s*OR\s+1\s*=\s*1",
        r'(?i)\bEXEC\s*\(',
        r'(?i)\bxp_cmdshell\b',
        r'(?i)\bWAITFOR\s+DELAY\b',
    ]

    # XSS 攻击模式
    XSS_PATTERNS = [
        r'(?i)<script[^>]*>.*?</script>',
        r'(?i)javascript\s*:',
        r'(?i)on(load|error|click|mouseover|focus|blur)\s*=',
        r'(?i)<iframe[^>]*>',
        r'(?i)<object[^>]*>',
        r'(?i)<embed[^>]*>',
        r'(?i)document\.(cookie|location|write)',
        r'(?i)eval\s*\(',
        r'(?i)alert\s*\(',
    ]

    # 命令注入模式
    COMMAND_INJECTION_PATTERNS = [
        r'(?i)[;|&`]\s*(rm|del|rmdir|chmod|chown|sudo|su)\s',
        r'(?i)\$\{.*\}',
        r'(?i)`[^`]+`',
        r'(?i)\|\s*(cat|ls|dir|pwd|whoami|id)',
        r'(?i)>>\s*/etc/',
    ]

    # 可疑意图检测
    SUSPICIOUS_INTENT_PATTERNS = [
        r'(?i)删除所有',
        r'(?i)清空.*任务',
        r'(?i)重置.*数据库',
        r'(?i)初始化.*系统',
        r'(?i)绕过.*验证',
        r'(?i)提权|root|admin',
        r'(?i)获取.*密码|密钥|token',
    ]

    def __init__(self):
        self.sql_patterns = [re.compile(p) for p in self.SQL_INJECTION_PATTERNS]
        self.xss_patterns = [re.compile(p) for p in self.XSS_PATTERNS]
        self.cmd_patterns = [re.compile(p) for p in self.COMMAND_INJECTION_PATTERNS]
        self.suspicious_patterns = [re.compile(p) for p in self.SUSPICIOUS_INTENT_PATTERNS]

    def detect(self, message: str) -> Dict[str, Any]:
        """检测恶意命令

        Args:
            message: 用户输入的消息

        Returns:
            检测结果字典
        """
        threats = []

        # 检测 SQL 注入
        for pattern in self.sql_patterns:
            matches = pattern.findall(message)
            if matches:
                threats.append({
                    "type": "sql_injection",
                    "severity": "high",
                    "matches": matches,
                    "pattern": pattern.pattern
                })

        # 检测 XSS
        for pattern in self.xss_patterns:
            matches = pattern.findall(message)
            if matches:
                threats.append({
                    "type": "xss_attack",
                    "severity": "medium",
                    "matches": matches,
                    "pattern": pattern.pattern
                })

        # 检测命令注入
        for pattern in self.cmd_patterns:
            matches = pattern.findall(message)
            if matches:
                threats.append({
                    "type": "command_injection",
                    "severity": "high",
                    "matches": matches,
                    "pattern": pattern.pattern
                })

        # 检测可疑意图
        for pattern in self.suspicious_patterns:
            matches = pattern.findall(message)
            if matches:
                threats.append({
                    "type": "suspicious_intent",
                    "severity": "low",
                    "matches": matches,
                    "pattern": pattern.pattern
                })

        is_malicious = len(threats) > 0
        max_severity = self._get_max_severity(threats)

        return {
            "is_malicious": is_malicious,
            "severity": max_severity,
            "threat_count": len(threats),
            "threats": threats,
            "message": message
        }

    def _get_max_severity(self, threats: List[Dict]) -> str:
        """获取最高威胁等级"""
        severity_order = {"high": 3, "medium": 2, "low": 1}
        if not threats:
            return "none"

        max_level = 0
        for threat in threats:
            level = severity_order.get(threat["severity"], 0)
            if level > max_level:
                max_level = level

        severity_map = {3: "high", 2: "medium", 1: "low"}
        return severity_map.get(max_level, "none")


class RecoveryResponseGenerator:
    """恢复响应生成器 - 生成可变的恢复回复"""

    # SQL 注入恢复回复模板
    SQL_INJECTION_REPLIES = [
        "🛡️ 检测到可疑的数据库操作请求。为了保护您的数据安全，此类操作已被阻止。\n\n💡 建议：如需管理任务，请使用正常的任务管理功能。",
        "⚠️ 您的请求包含潜在的 SQL 命令。系统已启用安全保护，阻止了该操作。\n\n📋 如需删除任务，请告诉我具体要删除哪个任务。",
        "🚫 安全警告：检测到 SQL 注入尝试。此操作已被安全机制拦截。\n\n✅ 您可以安全地告诉我：「删除明天的会议」或「取消写作业的任务」。",
        "🔒 系统检测到非正常的数据库操作请求。数据安全已得到保护。\n\n💬 如需操作任务，请使用自然语言描述，如「删除第三个任务」。",
    ]

    # XSS 攻击恢复回复
    XSS_REPLIES = [
        "🛡️ 检测到潜在的脚本注入。为保护您的账户安全，此操作已被阻止。\n\n💡 建议：请勿在消息中嵌入 HTML 或 JavaScript 代码。",
        "⚠️ 安全提示：您的消息包含可疑的脚本内容。系统已自动过滤。\n\n📝 请重新输入正常的文字内容。",
        "🚫 检测到 XSS 攻击特征。安全防护已生效。\n\n✅ 您可以直接告诉我您的需求，无需使用特殊代码。",
        "🔒 内容安全检查未通过。请避免在消息中使用 HTML 标签或脚本代码。",
    ]

    # 命令注入恢复回复
    COMMAND_INJECTION_REPLIES = [
        "🛡️ 检测到潜在的系统命令注入。安全机制已阻止该操作。\n\n💡 建议：本系统仅支持任务管理功能，不支持执行系统命令。",
        "⚠️ 安全警告：您的请求包含系统命令特征。此操作已被拦截。\n\n📋 如需帮助，请描述您的任务需求。",
        "🚫 检测到命令注入尝试。系统安全已得到保障。\n\n✅ 您可以告诉我：「添加一个学习任务」或「查看明天的日程」。",
    ]

    # 可疑意图恢复回复
    SUSPICIOUS_INTENT_REPLIES = [
        "🤔 我理解您想执行某项操作，但为了数据安全，我需要更明确的指示。\n\n💡 例如：「删除明天下午的会议」或「清空已完成的任务」。",
        "⚠️ 检测到模糊的操作请求。请提供更具体的任务信息。\n\n📋 您可以告诉我具体要操作的任务名称或时间。",
        "🛡️ 为避免误操作，请明确告知要处理的任务。\n\n✅ 例如：「删除编号为3的任务」或「取消所有待办」。",
        "🔒 安全提示：请具体描述您想要执行的操作。\n\n💬 我会帮您安全地完成任务管理。",
    ]

    # 通用安全提示
    GENERAL_SAFE_TIPS = [
        "\n\n🔐 **安全提示**：本系统已启用多重安全防护，包括参数化查询、输入验证、意图识别等，您的数据安全有保障。",
        "\n\n🛡️ **安全机制**：系统自动检测和阻止恶意操作，您可以放心使用自然语言管理任务。",
        "\n\n✅ **安全保障**：所有数据库操作都经过安全验证，防止 SQL 注入、XSS 等攻击。",
        "\n\n🔒 **隐私保护**：您的数据通过多层安全机制保护，不会被未授权访问。",
    ]

    def generate_response(self, detection_result: Dict) -> str:
        """生成恢复响应

        Args:
            detection_result: 检测结果

        Returns:
            恢复响应文本
        """
        if not detection_result["is_malicious"]:
            return None

        severity = detection_result["severity"]
        threats = detection_result["threats"]

        # 根据威胁类型选择回复模板
        reply_templates = self._select_templates(threats)

        # 随机选择一条回复
        base_reply = random.choice(reply_templates)

        # 添加安全提示
        if severity == "high":
            safe_tip = random.choice(self.GENERAL_SAFE_TIPS)
            base_reply += safe_tip

        # 记录日志
        self._log_detection(detection_result)

        return base_reply

    def _select_templates(self, threats: List[Dict]) -> List[str]:
        """根据威胁类型选择回复模板"""
        template_map = {
            "sql_injection": self.SQL_INJECTION_REPLIES,
            "xss_attack": self.XSS_REPLIES,
            "command_injection": self.COMMAND_INJECTION_REPLIES,
            "suspicious_intent": self.SUSPICIOUS_INTENT_REPLIES,
        }

        # 优先处理高等级威胁
        severity_order = {"high": 0, "medium": 1, "low": 2}
        sorted_threats = sorted(threats, key=lambda t: severity_order.get(t["severity"], 3))

        if sorted_threats:
            threat_type = sorted_threats[0]["type"]
            return template_map.get(threat_type, self.SUSPICIOUS_INTENT_REPLIES)

        return self.SUSPICIOUS_INTENT_REPLIES

    def _log_detection(self, detection_result: Dict):
        """记录检测日志（仅打印，不存储敏感信息）"""
        severity = detection_result["severity"]
        threat_count = detection_result["threat_count"]

        emoji_map = {"high": "🚨", "medium": "⚠️", "low": "💡"}
        emoji = emoji_map.get(severity, "ℹ️")

        print(f"\n{emoji} 安全检测: 发现 {threat_count} 个威胁 (等级: {severity})")
        print(f"   原始消息: {detection_result['message'][:50]}...")

        for threat in detection_result["threats"]:
            print(f"   - {threat['type']} ({threat['severity']})")


# 全局实例
detector = MaliciousCommandDetector()
recovery_generator = RecoveryResponseGenerator()


def check_and_handle_malicious(message: str) -> Tuple[bool, str]:
    """检查并处理恶意命令（便捷函数）

    Args:
        message: 用户输入

    Returns:
        (是否恶意, 恢复回复或 None)
    """
    result = detector.detect(message)

    if result["is_malicious"]:
        reply = recovery_generator.generate_response(result)
        return True, reply

    return False, None
