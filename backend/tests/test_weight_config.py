"""
权重配置模块单元测试
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from app.services.weight_config import WeightConfig


class TestWeightConfigConstants:
    """测试权重常量是否正确"""

    def test_weights_sum_to_one(self):
        """所有权重之和必须为1.0"""
        total = sum(WeightConfig.COMPREHENSIVE_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9, f"权重总和应为1.0，实际为{total}"

    def test_weights_have_four_dimensions(self):
        """权重必须包含四个维度"""
        keys = set(WeightConfig.COMPREHENSIVE_WEIGHTS.keys())
        assert keys == {'attendance', 'homework', 'quiz', 'interaction'}

    def test_weights_values(self):
        """验证具体权重值 30/30/30/10"""
        w = WeightConfig.COMPREHENSIVE_WEIGHTS
        assert w['attendance'] == 0.3
        assert w['homework'] == 0.3
        assert w['quiz'] == 0.3
        assert w['interaction'] == 0.1

    def test_thresholds_exist(self):
        """预警阈值必须包含三个等级"""
        assert 'red' in WeightConfig.WARNING_THRESHOLDS
        assert 'orange' in WeightConfig.WARNING_THRESHOLDS
        assert 'yellow' in WeightConfig.WARNING_THRESHOLDS


class TestCalculateScore:
    """测试综合评分计算"""

    def test_full_score(self):
        """满分情况：所有维度100分 → 综合分100"""
        metrics = {'attendance': 100, 'homework': 100, 'quiz': 100, 'interaction': 100}
        result = WeightConfig.calculate_comprehensive_score(metrics)
        assert abs(result - 100.0) < 1e-9

    def test_zero_score(self):
        """零分情况：所有维度0分 → 综合分0"""
        metrics = {'attendance': 0, 'homework': 0, 'quiz': 0, 'interaction': 0}
        result = WeightConfig.calculate_comprehensive_score(metrics)
        assert result == 0.0

    def test_mixed_score(self):
        """混合分数验证计算公式"""
        metrics = {'attendance': 80, 'homework': 70, 'quiz': 90, 'interaction': 60}
        expected = 80 * 0.3 + 70 * 0.3 + 90 * 0.3 + 60 * 0.1
        result = WeightConfig.calculate_comprehensive_score(metrics)
        assert abs(result - expected) < 1e-9

    def test_missing_key_raises_error(self):
        """缺少必要字段时必须抛出 ValueError"""
        incomplete = {'attendance': 80, 'homework': 70, 'quiz': 90}  # 缺 interaction
        with pytest.raises(ValueError, match="interaction"):
            WeightConfig.calculate_comprehensive_score(incomplete)


class TestWarningLevel:
    """测试预警等级判断"""

    def test_red_level(self):
        """分数 < 60 → 红色预警"""
        assert WeightConfig.get_warning_level(59.9) == 'red'
        assert WeightConfig.get_warning_level(0) == 'red'

    def test_orange_level(self):
        """60 <= 分数 < 75 → 橙色预警"""
        assert WeightConfig.get_warning_level(60) == 'orange'
        assert WeightConfig.get_warning_level(74.9) == 'orange'

    def test_yellow_level(self):
        """75 <= 分数 < 85 → 黄色预警"""
        assert WeightConfig.get_warning_level(75) == 'yellow'
        assert WeightConfig.get_warning_level(84.9) == 'yellow'

    def test_no_warning(self):
        """分数 >= 85 → 无需预警"""
        assert WeightConfig.get_warning_level(85) is None
        assert WeightConfig.get_warning_level(100) is None


class TestGetColumnTitle:
    """测试 Excel 列标题生成"""

    def test_column_titles_match_weights(self):
        """列标题中的百分比必须与实际权重一致"""
        titles = WeightConfig.get_score_column_titles()
        assert titles['attendance'] == '出勤分(30%)'
        assert titles['homework'] == '作业分(30%)'
        assert titles['quiz'] == '测评分(30%)'
        assert titles['interaction'] == '互动分(10%)'
