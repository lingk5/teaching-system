"""
weight_config.py — 全系统唯一权重来源

所有涉及综合评分的模块（预警引擎、成绩导出、分析接口）
必须从此处读取权重，禁止在其他文件中硬编码权重数值。
"""


class WeightConfig:
    """集中管理综合评分权重和预警阈值"""

    # ── 综合评分权重（总和必须为 1.0）──────────────────────────
    # 出勤 30% + 作业 30% + 测验 30% + 互动 10%
    COMPREHENSIVE_WEIGHTS = {
        'attendance':  0.3,
        'homework':    0.3,
        'quiz':        0.3,
        'interaction': 0.1,
    }

    # ── 预警阈值（分数低于对应阈值触发该等级预警）──────────────
    WARNING_THRESHOLDS = {
        'red':    60,   # 综合分 < 60  → 红色（紧急）
        'orange': 75,   # 综合分 < 75  → 橙色（关注）
        'yellow': 85,   # 综合分 < 85  → 黄色（提醒）
    }

    # ────────────────────────────────────────────────────────────

    @classmethod
    def calculate_comprehensive_score(cls, metrics: dict) -> float:
        """
        按权重计算综合评分。

        :param metrics: 包含四个维度得分的字典，每项分值范围 0–100
                        必须包含 'attendance', 'homework', 'quiz', 'interaction'
        :returns: 综合评分，浮点数，范围 0–100
        :raises ValueError: 当 metrics 缺少必要字段时
        """
        score = 0.0
        for key, weight in cls.COMPREHENSIVE_WEIGHTS.items():
            if key not in metrics:
                raise ValueError(f"缺少必要的指标字段: '{key}'")
            score += float(metrics[key]) * weight
        return max(0.0, min(100.0, score))

    @classmethod
    def get_warning_level(cls, score: float):
        """
        根据综合评分返回预警等级。

        :returns: 'red' | 'orange' | 'yellow' | None
        """
        if score < cls.WARNING_THRESHOLDS['red']:
            return 'red'
        if score < cls.WARNING_THRESHOLDS['orange']:
            return 'orange'
        if score < cls.WARNING_THRESHOLDS['yellow']:
            return 'yellow'
        return None

    @classmethod
    def get_score_column_titles(cls) -> dict:
        """
        返回用于 Excel 导出时各维度列标题（含权重百分比）。

        :returns: 例如 {'attendance': '出勤分(30%)', ...}
        """
        label_map = {
            'attendance':  '出勤分',
            'homework':    '作业分',
            'quiz':        '测评分',
            'interaction': '互动分',
        }
        return {
            key: f"{label_map[key]}({int(weight * 100)}%)"
            for key, weight in cls.COMPREHENSIVE_WEIGHTS.items()
        }

    @classmethod
    def get_weight_description(cls) -> str:
        """返回人类可读的权重公式说明"""
        w = cls.COMPREHENSIVE_WEIGHTS
        return (
            f"综合评分 = "
            f"出勤({int(w['attendance']*100)}%) + "
            f"作业({int(w['homework']*100)}%) + "
            f"测验({int(w['quiz']*100)}%) + "
            f"互动({int(w['interaction']*100)}%)"
        )
