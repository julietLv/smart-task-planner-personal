# backend/app/services/scoring_engine.py

import yaml
from pathlib import Path


class ScoringEngine:
    """评分引擎 - 归一化评分体系"""

    def __init__(self):
        self.config = self.load_config()
        self.validate_config()

    def load_config(self):
        """加载评分配置文件"""
        config_path = Path(__file__).parent.parent.parent / "config" / "scoring_weights.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def validate_config(self):
        """验证配置合法性"""
        total_weight = sum(
            dim['weight']
            for dim in self.config['dimensions'].values()
            if dim.get('enabled', True)
        )

        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"权重总和不等于 1.0: {total_weight}")

    def normalize_score(self, raw_score, dimension_name):
        """
        将原始分数归一化到 0-1

        Args:
            raw_score: 原始分数
            dimension_name: 维度名称

        Returns:
            归一化后的分数 (0-1)
        """
        dim_config = self.config['dimensions'][dimension_name]

        if not dim_config.get('enabled', True):
            return 0.5  # 禁用维度返回中性分

        min_score = dim_config['min_score']
        max_score = dim_config['max_score']

        # 线性归一化
        if max_score == min_score:
            return 0.5  # 避免除零

        normalized = (raw_score - min_score) / (max_score - min_score)

        # 限制在 0-1 范围
        return max(0.0, min(1.0, normalized))

    def calculate_final_score(self, dimension_scores):
        """
        计算最终评分

        Args:
            dimension_scores: {
                'habit_match': 50,
                'date_freshness': 25,
                'urgency': 0,
                ...
            }

        Returns:
            {
                'final_score': 72.5,  # 0-100 分
                'dimension_details': {
                    'habit_match': {
                        'raw': 50,
                        'normalized': 0.77,
                        'weighted': 0.23,
                        'weight': 0.30
                    },
                    ...
                }
            }
        """
        total_score = 0.0
        dimension_details = {}

        for dim_name, raw_score in dimension_scores.items():
            if dim_name not in self.config['dimensions']:
                continue

            dim_config = self.config['dimensions'][dim_name]

            # 归一化
            normalized = self.normalize_score(raw_score, dim_name)

            # 加权
            weight = dim_config['weight']
            weighted_score = normalized * weight

            # 累加
            total_score += weighted_score

            # 记录明细
            dimension_details[dim_name] = {
                'raw': raw_score,
                'normalized': round(normalized, 4),
                'weighted': round(weighted_score, 4),
                'weight': weight
            }

        # 转换为 0-100 分
        final_score = total_score * 100

        return {
            'final_score': round(final_score, 2),
            'dimension_details': dimension_details
        }
