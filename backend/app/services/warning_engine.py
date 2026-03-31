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
        score_details = WeightConfig.calculate_score_details(metrics)
        score = score_details['comprehensive_score']
        metrics['comprehensive_score'] = score
        metrics['coverage'] = score_details['coverage']

        if not score_details['eligible_for_warning']:
            self._clear_active_warning(student.id, metrics)
            return None

        level = self._determine_warning_level(score)
        if not level:
            self._clear_active_warning(student.id, metrics)
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
        return float(avg_score) if avg_score is not None else None

    def _calculate_homework_score(self, student_id, start, end):
        """作业分：按百分制折算"""
        avg_score = db.session.query(
            func.avg(Homework.score / Homework.max_score * 100)
        ).filter(
            Homework.student_id == student_id,
            Homework.course_id == self.course_id,
            Homework.created_at.between(start, end)
        ).scalar()
        return float(avg_score) if avg_score is not None else None

    def _calculate_quiz_score(self, student_id, start, end):
        """测验分：按百分制折算"""
        avg_score = db.session.query(
            func.avg(Quiz.score / Quiz.max_score * 100)
        ).filter(
            Quiz.student_id == student_id,
            Quiz.course_id == self.course_id,
            Quiz.created_at.between(start, end)
        ).scalar()
        return float(avg_score) if avg_score is not None else None

    def _calculate_interaction_score(self, student_id, start, end):
        """互动分：每次互动+10分，100分封顶"""
        count = db.session.query(func.sum(Interaction.count)).filter(
            Interaction.student_id == student_id,
            Interaction.course_id == self.course_id,
            Interaction.date.between(start.date(), end.date())
        ).scalar()
        if count is None:
            return None
        return min(count * 10, 100)

    def _calculate_comprehensive_score(self, metrics):
        """使用 WeightConfig 统一计算综合分"""
        return WeightConfig.calculate_comprehensive_score(metrics)

    def _determine_warning_level(self, score):
        """使用 WeightConfig 统一判断预警等级"""
        return WeightConfig.get_warning_level(score)

    def _generate_reason_and_suggestion(self, metrics, score, level):
        """生成预警原因和干预建议"""
        metric_keys = metrics.get('coverage', {}).get('covered_fields', [])
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

    def _clear_active_warning(self, student_id, metrics):
        existing = Warning.query.filter_by(
            student_id=student_id,
            course_id=self.course_id,
            type='comprehensive',
            status='active'
        ).first()
        if existing:
            existing.status = 'cleared'
            existing.metrics = metrics
            existing.created_at = datetime.now()
