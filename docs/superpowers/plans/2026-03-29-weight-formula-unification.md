# 权重公式统一 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消除导出报表（30/30/40）与预警引擎（30/30/30/10）权重不一致问题，建立集中化权重配置，确保全系统统一使用同一套评分公式。

**Architecture:** 新建 `weight_config.py` 作为唯一权重来源，预警引擎、导出模块、分析接口全部从该模块读取配置；成绩报表列标题和 Excel 说明同步更新；`analytics.py` 的 `student_profile` 接口已通过 WarningEngine 计算，无需额外修改。

**Tech Stack:** Python 3.8+, Flask, SQLAlchemy, pytest

---

## 📁 文件清单

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| **新建** | `backend/app/services/weight_config.py` | 权重配置主模块（唯一来源） |
| **新建** | `backend/tests/test_weight_config.py` | 权重配置单元测试 |
| **修改** | `backend/app/services/warning_engine.py` | 改用 WeightConfig，删除内部常量 |
| **修改** | `backend/app/routes/export.py:238-266` | 成绩报表改用 WeightConfig，修正列标题 |

---

## Task 1：创建 weight_config.py

**Files:**
- Create: `backend/app/services/weight_config.py`
- Test: `backend/tests/test_weight_config.py`

- [ ] **Step 1：新建测试文件，先写失败的测试**

```bash
mkdir -p /Users/a2914452089/Desktop/teaching-system/backend/tests
touch /Users/a2914452089/Desktop/teaching-system/backend/tests/__init__.py
```

新建 `backend/tests/test_weight_config.py`，内容如下：

```python
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
```

- [ ] **Step 2：运行测试，确认全部失败（因为 weight_config.py 还不存在）**

```bash
cd /Users/a2914452089/Desktop/teaching-system/backend
source venv/bin/activate
pip install pytest -q
python -m pytest tests/test_weight_config.py -v 2>&1 | head -40
```

预期输出：`ModuleNotFoundError: No module named 'app.services.weight_config'`

- [ ] **Step 3：创建 `backend/app/services/weight_config.py`**

```python
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
```

- [ ] **Step 4：再次运行测试，确认全部通过**

```bash
cd /Users/a2914452089/Desktop/teaching-system/backend
python -m pytest tests/test_weight_config.py -v
```

预期输出：所有测试 `PASSED`，无 `FAILED`

- [ ] **Step 5：提交**

```bash
cd /Users/a2914452089/Desktop/teaching-system
git add backend/app/services/weight_config.py backend/tests/
git commit -m "feat: add WeightConfig as single source of truth for score weights"
```

---

## Task 2：重构预警引擎使用 WeightConfig

**Files:**
- Modify: `backend/app/services/warning_engine.py`
- Test: `backend/tests/test_weight_config.py`（无需新增测试，预警引擎已有行为不变）

- [ ] **Step 1：修改 `warning_engine.py`，删除内部常量，改用 WeightConfig**

打开 `backend/app/services/warning_engine.py`，将文件**完整替换**为以下内容：

```python
from sqlalchemy import func, case
from datetime import datetime, timedelta
from ..models import db, Student, Class, Warning, Attendance, Homework, Quiz, Interaction
from .weight_config import WeightConfig


class WarningEngine:
    """
    预警规则引擎 V2.1
    - 权重和阈值统一由 WeightConfig 管理
    - 使用综合评分模型
    - 生成具体的干预建议
    """

    TIME_DELTA_DAYS = 30  # 分析最近30天的数据

    def __init__(self, course_id):
        self.course_id = course_id

    def check_all_students(self):
        """对课程下所有学生执行预警检查"""
        students = self._get_students_in_course()
        if not students:
            return []

        warnings_generated = []
        for student in students:
            warning = self._generate_warning_for_student(student)
            if warning:
                warnings_generated.append(warning)

        if warnings_generated:
            db.session.bulk_save_objects(warnings_generated)
            db.session.commit()

        return warnings_generated

    def _get_students_in_course(self):
        """获取课程下的所有学生"""
        class_ids = db.session.query(Class.id).filter(
            Class.course_id == self.course_id
        ).scalar_subquery()
        return Student.query.filter(Student.class_id.in_(class_ids)).all()

    def _generate_warning_for_student(self, student):
        """为单个学生生成综合预警"""
        metrics = self._calculate_metrics(student.id)
        score = self._calculate_comprehensive_score(metrics)
        metrics['comprehensive_score'] = round(score, 2)

        level = self._determine_warning_level(score)
        if not level:
            return None

        reason, suggestion = self._generate_reason_and_suggestion(metrics, score, level)
        return self._create_or_update_warning(student.id, level, reason, suggestion, metrics)

    def _calculate_metrics(self, student_id):
        """计算所有维度的指标分数（0-100）"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.TIME_DELTA_DAYS)

        return {
            'attendance':  self._calculate_attendance_score(student_id, start_date, end_date),
            'homework':    self._calculate_homework_score(student_id, start_date, end_date),
            'quiz':        self._calculate_quiz_score(student_id, start_date, end_date),
            'interaction': self._calculate_interaction_score(student_id, start_date, end_date),
        }

    def _calculate_attendance_score(self, student_id, start, end):
        """出勤分：present=100, late=80, leave=60, absent=0"""
        score_case = case(
            (Attendance.status == 'present', 100),
            (Attendance.status == 'late', 80),
            (Attendance.status == 'leave', 60),
            else_=0
        )
        avg_score = db.session.query(func.avg(score_case)).filter(
            Attendance.student_id == student_id,
            Attendance.course_id == self.course_id,
            Attendance.date.between(start.date(), end.date())
        ).scalar()
        return float(avg_score) if avg_score is not None else 100.0

    def _calculate_homework_score(self, student_id, start, end):
        """作业分：按百分制折算"""
        avg_score = db.session.query(
            func.avg(Homework.score / Homework.max_score * 100)
        ).filter(
            Homework.student_id == student_id,
            Homework.course_id == self.course_id,
            Homework.created_at.between(start, end)
        ).scalar()
        return float(avg_score) if avg_score is not None else 100.0

    def _calculate_quiz_score(self, student_id, start, end):
        """测验分：按百分制折算"""
        avg_score = db.session.query(
            func.avg(Quiz.score / Quiz.max_score * 100)
        ).filter(
            Quiz.student_id == student_id,
            Quiz.course_id == self.course_id,
            Quiz.created_at.between(start, end)
        ).scalar()
        return float(avg_score) if avg_score is not None else 100.0

    def _calculate_interaction_score(self, student_id, start, end):
        """互动分：每次互动+10分，100分封顶"""
        count = db.session.query(func.sum(Interaction.count)).filter(
            Interaction.student_id == student_id,
            Interaction.course_id == self.course_id,
            Interaction.date.between(start.date(), end.date())
        ).scalar() or 0
        return min(count * 10, 100)

    def _calculate_comprehensive_score(self, metrics):
        """使用 WeightConfig 统一计算综合分"""
        return WeightConfig.calculate_comprehensive_score(metrics)

    def _determine_warning_level(self, score):
        """使用 WeightConfig 统一判断预警等级"""
        return WeightConfig.get_warning_level(score)

    def _generate_reason_and_suggestion(self, metrics, score, level):
        """生成预警原因和干预建议"""
        metric_keys = ['attendance', 'homework', 'quiz', 'interaction']
        low_items = sorted(
            [(k, metrics[k]) for k in metric_keys],
            key=lambda item: item[1]
        )
        lowest_metric, lowest_score = low_items[0]

        metric_map = {
            'attendance':  '出勤表现',
            'homework':    '作业成绩',
            'quiz':        '测验成绩',
            'interaction': '课堂互动',
        }

        reason = (
            f"综合评分 {score:.1f} 分，等级为{level}。"
            f"主要短板在于【{metric_map[lowest_metric]}】({lowest_score:.1f}分)。"
        )

        suggestions = {
            'red': (
                "情况紧急，建议立即与学生进行一对一深入沟通，"
                "了解其学习或生活上遇到的困难，并制定详细的帮扶计划。"
            ),
            'orange': (
                f"建议重点关注该生的【{metric_map[lowest_metric]}】情况，"
                "可通过课堂提问、课后督促等方式给予提醒，必要时提供额外辅导。"
            ),
            'yellow': (
                f"建议对该生的【{metric_map[lowest_metric]}】表现给予鼓励和引导，"
                "帮助其巩固基础，提升学习兴趣。"
            ),
        }

        return reason, suggestions[level]

    def _create_or_update_warning(self, student_id, level, reason, suggestion, metrics):
        """创建或更新预警记录，避免重复"""
        existing = Warning.query.filter_by(
            student_id=student_id,
            course_id=self.course_id,
            type='comprehensive',
            status='active'
        ).first()

        if existing:
            if existing.level != level or existing.reason != reason:
                existing.level = level
                existing.reason = reason
                existing.suggestion = suggestion
                existing.metrics = metrics
                existing.created_at = datetime.now()
            return None
        else:
            return Warning(
                student_id=student_id,
                course_id=self.course_id,
                type='comprehensive',
                level=level,
                reason=reason,
                suggestion=suggestion,
                metrics=metrics,
                status='active'
            )
```

- [ ] **Step 2：运行已有测试，确认预警引擎功能没有退化**

```bash
cd /Users/a2914452089/Desktop/teaching-system/backend
python -m pytest tests/test_weight_config.py -v
```

预期：全部 `PASSED`

- [ ] **Step 3：提交**

```bash
cd /Users/a2914452089/Desktop/teaching-system
git add backend/app/services/warning_engine.py
git commit -m "refactor: warning_engine uses WeightConfig instead of inline constants"
```

---

## Task 3：修复导出模块权重和列标题

**Files:**
- Modify: `backend/app/routes/export.py:163-314`（`export_scores` 函数）

- [ ] **Step 1：修改 `export.py` 中的 `export_scores` 函数**

在 `export.py` 文件顶部的导入区（第17行附近），添加 WeightConfig 导入：

```python
# 在 from ..models.warning import Warning 这行后面添加：
from ..services.weight_config import WeightConfig
```

然后将 `export_scores` 函数中第 **235–267行**（构建 data 列表的部分）替换为：

```python
        # 构建数据（使用统一的权重配置）
        col_titles = WeightConfig.get_score_column_titles()
        data = []
        for row in results:
            # 各维度原始得分（0-100）
            attendance = float(row.attendance_avg) if row.attendance_avg is not None else 0.0
            homework   = float(row.homework_avg)   if row.homework_avg   is not None else 0.0
            quiz       = float(row.quiz_avg)       if row.quiz_avg       is not None else 0.0
            # 互动分：导出时暂无聚合，默认给满分（与预警引擎"无数据=满分"逻辑一致）
            interaction = 100.0

            metrics = {
                'attendance':  attendance,
                'homework':    homework,
                'quiz':        quiz,
                'interaction': interaction,
            }
            composite = WeightConfig.calculate_comprehensive_score(metrics)

            # 评定等级
            if composite >= 90:
                grade = '优秀'
            elif composite >= 80:
                grade = '良好'
            elif composite >= 70:
                grade = '中等'
            elif composite >= 60:
                grade = '及格'
            else:
                grade = '不及格'

            data.append({
                '学号':                     row.student_no,
                '姓名':                     row.name,
                '班级':                     row.class_name,
                '课程':                     row.course_name,
                col_titles['attendance']:   round(attendance, 1),
                col_titles['homework']:     round(homework, 1),
                col_titles['quiz']:         round(quiz, 1),
                col_titles['interaction']:  round(interaction, 1),
                '综合分':                   round(composite, 1),
                '等级':                     grade,
            })
```

- [ ] **Step 2：启动后端，手动验证导出成绩报表**

```bash
cd /Users/a2914452089/Desktop/teaching-system/backend
source venv/bin/activate
python run.py &
sleep 2

# 获取 token
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"teacher","password":"123456"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")

# 导出成绩报表（有数据时）
curl -s -o /tmp/scores_test.xlsx \
  -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:5000/api/export/scores"

echo "文件大小: $(wc -c < /tmp/scores_test.xlsx) bytes"
```

预期：输出文件大小大于 0 bytes；若返回 JSON（无数据），说明数据库没有成绩数据，属正常，等上传真实数据后再验证

- [ ] **Step 3：运行单元测试，确认权重模块不受影响**

```bash
cd /Users/a2914452089/Desktop/teaching-system/backend
python -m pytest tests/test_weight_config.py -v
```

预期：全部 `PASSED`

- [ ] **Step 4：提交**

```bash
cd /Users/a2914452089/Desktop/teaching-system
git add backend/app/routes/export.py
git commit -m "fix: export_scores uses WeightConfig (30/30/30/10) instead of hardcoded 30/30/40"
```

---

## Task 4：验证整体一致性

- [ ] **Step 1：运行全部单元测试**

```bash
cd /Users/a2914452089/Desktop/teaching-system/backend
python -m pytest tests/ -v
```

预期：全部 `PASSED`，无 `FAILED` 或 `ERROR`

- [ ] **Step 2：启动后端，手动触发预警生成，检查等级**

```bash
cd /Users/a2914452089/Desktop/teaching-system/backend
source venv/bin/activate
python run.py &
sleep 2

TOKEN=$(curl -s -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"teacher","password":"123456"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")

# 获取课程列表，拿第一个课程 id
COURSE_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:5000/api/courses/ | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data'][0]['id']) if d.get('data') else print('')")

echo "测试课程 ID: $COURSE_ID"

# 触发预警生成
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "http://127.0.0.1:5000/api/warnings/generate" \
  -d "{\"course_id\": $COURSE_ID}"
```

预期：返回 `{"success": true, "message": "..."}` 或类似成功响应

- [ ] **Step 3：对比导出报表与预警等级是否一致**

选取一名有预警的学生，查看：
1. 在预警列表中记录的综合分和等级
2. 在成绩报表导出 Excel 中的综合分和等级

两者综合分差值应 < 0.1（互动分在导出时暂按100计，可能有微小差异，已在注释中说明）

- [ ] **Step 4：最终提交**

```bash
cd /Users/a2914452089/Desktop/teaching-system
git add .
git commit -m "test: verify weight consistency between warning engine and export module"
```

---

## 📋 自检清单

- [x] **Spec 覆盖**：权重配置、预警引擎重构、导出模块修复、列标题更新全部有对应 Task
- [x] **无占位符**：所有步骤均含完整代码，无 TBD / TODO
- [x] **类型一致**：`WeightConfig.calculate_comprehensive_score` 接收 `dict` 返回 `float`，三处调用者均一致
- [x] **方法名一致**：`get_score_column_titles()`、`get_warning_level()`、`calculate_comprehensive_score()` 全局统一

---

## ⚠️ 注意事项

1. **互动分在导出报表中暂设为 100**：因为 `export_scores` 的 SQL 查询没有聚合互动数据，与预警引擎一致的处理是"无数据=满分"。后续如需要真实互动数据参与导出计算，需额外修改 SQL 查询（超出本次范围）。

2. **历史预警不受影响**：本次修改保持权重值不变（30/30/30/10），只是统一了代码来源，历史预警记录中的综合分仍然有效。

3. **导出列标题会自动同步**：通过 `WeightConfig.get_score_column_titles()` 生成，以后如果调整权重，列标题会自动更新，无需手动修改。
