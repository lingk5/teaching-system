from sqlalchemy import func, case
from datetime import datetime, timedelta
from ..models import db, Student, Class, Warning, Attendance, Homework, Quiz, Interaction

class WarningEngine:
    """
    预警规则引擎 V2.0
    - 使用综合评分模型
    - 可配置的权重和阈值
    - 生成更具体的干预建议
    """
    
    # --- 可配置参数 ---
    WEIGHTS = {
        'attendance': 0.3,
        'homework': 0.3,
        'quiz': 0.3,
        'interaction': 0.1
    }
    
    THRESHOLDS = {
        'red': 60,
        'orange': 75,
        'yellow': 85
    }
    
    # --- 内部常量 ---
    TIME_DELTA_DAYS = 30 # 分析最近30天的数据
    MIN_REQUIRED_DIMENSIONS = 2

    def __init__(self, course_id):
        self.course_id = course_id

    def check_all_students(self):
        """对课程下所有学生执行预警检查"""
        students = self._get_students_in_course()
        if not students:
            return []

        warnings_generated = []
        has_changes = False
        for student in students:
            warning = self._generate_warning_for_student(student)
            if warning:
                warnings_generated.append(warning)
                has_changes = True

            if db.session.dirty or db.session.deleted:
                has_changes = True
        
        # 除了新增预警，也要提交已更新或已自动关闭的预警
        if warnings_generated:
            db.session.add_all(warnings_generated)

        if has_changes:
            db.session.commit()
            
        return warnings_generated

    def _get_students_in_course(self):
        """获取课程下的所有学生"""
        class_ids = db.session.query(Class.id).filter(Class.course_id == self.course_id).scalar_subquery()
        return Student.query.filter(Student.class_id.in_(class_ids)).all()

    def _generate_warning_for_student(self, student):
        """为单个学生生成综合预警"""
        
        # 1. 计算各项指标得分 (0-100)
        metrics = self._calculate_metrics(student.id)
        
        available_metrics = self._get_available_metrics(metrics)
        metrics['available_dimensions'] = available_metrics

        if len(available_metrics) < self.MIN_REQUIRED_DIMENSIONS:
            self._clear_active_warning(
                student.id,
                f"系统重新计算后发现有效指标不足 {self.MIN_REQUIRED_DIMENSIONS} 项，已自动关闭综合预警。"
            )
            return None

        # 2. 计算综合分
        score = self._calculate_comprehensive_score(metrics)
        if score is None:
            self._clear_active_warning(
                student.id,
                "系统重新计算后暂无可用于综合评分的有效过程数据，已自动关闭综合预警。"
            )
            return None

        metrics['comprehensive_score'] = round(score, 2)
        
        # 3. 判断预警等级
        level = self._determine_warning_level(score)
        
        if not level:
            self._clear_active_warning(
                student.id,
                "系统重新计算后未达到综合预警阈值，已自动关闭综合预警。"
            )
            return None # 无需预警

        # 4. 生成预警原因和建议
        reason, suggestion = self._generate_reason_and_suggestion(
            metrics, score, level, available_metrics
        )
        
        # 5. 检查并创建/更新预警记录
        return self._create_or_update_warning(student.id, level, reason, suggestion, metrics)

    def _calculate_metrics(self, student_id):
        """计算所有维度的指标分数"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.TIME_DELTA_DAYS)
        
        return {
            'attendance': self._calculate_attendance_score(student_id, start_date, end_date),
            'homework': self._calculate_homework_score(student_id, start_date, end_date),
            'quiz': self._calculate_quiz_score(student_id, start_date, end_date),
            'interaction': self._calculate_interaction_score(student_id, start_date, end_date)
        }

    def _calculate_attendance_score(self, student_id, start, end):
        """计算出勤分 (present=100, late=80, leave=60, absent=0)"""
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
        """计算作业平均分 (按百分制折算)"""
        avg_score = db.session.query(func.avg(Homework.score / Homework.max_score * 100)).filter(
            Homework.student_id == student_id,
            Homework.course_id == self.course_id,
            Homework.created_at.between(start, end)
        ).scalar()
        return float(avg_score) if avg_score is not None else None

    def _calculate_quiz_score(self, student_id, start, end):
        """计算测验平均分 (按百分制折算)"""
        avg_score = db.session.query(func.avg(Quiz.score / Quiz.max_score * 100)).filter(
            Quiz.student_id == student_id,
            Quiz.course_id == self.course_id,
            Quiz.created_at.between(start, end)
        ).scalar()
        return float(avg_score) if avg_score is not None else None

    def _calculate_interaction_score(self, student_id, start, end):
        """计算互动得分 (每次互动+10分，100分封顶)"""
        count = db.session.query(func.sum(Interaction.count)).filter(
            Interaction.student_id == student_id,
            Interaction.course_id == self.course_id,
            Interaction.date.between(start.date(), end.date())
        ).scalar()
        if count is None:
            return None
        return min(count * 10, 100)

    def _get_available_metrics(self, metrics):
        """返回当前可用于综合评分的指标名称"""
        return [key for key in self.WEIGHTS if metrics.get(key) is not None]

    def _calculate_comprehensive_score(self, metrics):
        """仅基于已采集数据计算综合分，并对权重重新归一化"""
        available_metrics = self._get_available_metrics(metrics)
        if not available_metrics:
            return None

        total_weight = sum(self.WEIGHTS[key] for key in available_metrics)
        if total_weight <= 0:
            return None

        score = 0
        for key in available_metrics:
            normalized_weight = self.WEIGHTS[key] / total_weight
            score += metrics[key] * normalized_weight
        return score

    def _determine_warning_level(self, score):
        """根据分数确定预警等级"""
        if score < self.THRESHOLDS['red']:
            return 'red'
        if score < self.THRESHOLDS['orange']:
            return 'orange'
        if score < self.THRESHOLDS['yellow']:
            return 'yellow'
        return None

    def _generate_reason_and_suggestion(self, metrics, score, level, available_metrics):
        """生成预警原因和干预建议"""
        # 找出最低分的项
        low_items = sorted(
            ((key, metrics[key]) for key in available_metrics),
            key=lambda item: item[1]
        )
        lowest_metric, lowest_score = low_items[0]
        
        metric_map = {
            'attendance': '出勤表现',
            'homework': '作业成绩',
            'quiz': '测验成绩',
            'interaction': '课堂互动'
        }
        
        used_metrics = '、'.join(metric_map[key] for key in available_metrics)

        reason = (
            f"基于当前已采集的 {len(available_metrics)} 项指标（{used_metrics}）计算，"
            f"综合评分 {score:.1f} 分，等级为{level}。"
            f"主要短板在于【{metric_map[lowest_metric]}】({lowest_score:.1f}分)。"
        )
        
        suggestions = {
            'red': "情况紧急，建议立即与学生进行一对一深入沟通，了解其学习或生活上遇到的困难，并制定详细的帮扶计划。",
            'orange': "建议重点关注该生的【{}】情况，可通过课堂提问、课后督促等方式给予提醒，必要时提供额外辅导。".format(metric_map[lowest_metric]),
            'yellow': "建议对该生的【{}】表现给予鼓励和引导，帮助其巩固基础，提升学习兴趣。".format(metric_map[lowest_metric])
        }
        suggestion = suggestions[level]
        
        return reason, suggestion

    def _clear_active_warning(self, student_id, note):
        """当学生不再满足综合预警条件时，自动关闭旧的活跃预警"""
        existing_warning = Warning.query.filter_by(
            student_id=student_id,
            course_id=self.course_id,
            type='comprehensive',
            status='active'
        ).first()

        if not existing_warning:
            return

        existing_warning.status = 'ignored'
        existing_warning.handled_at = datetime.now()
        existing_warning.handle_note = note

    def _create_or_update_warning(self, student_id, level, reason, suggestion, metrics):
        """创建或更新预警记录，避免重复"""
        # 查找该学生在该课程下是否已有活跃的综合预警
        existing_warning = Warning.query.filter_by(
            student_id=student_id,
            course_id=self.course_id,
            type='comprehensive',
            status='active'
        ).first()

        if existing_warning:
            # 如果预警等级或原因有变化，则更新
            if existing_warning.level != level or existing_warning.reason != reason:
                existing_warning.level = level
                existing_warning.reason = reason
                existing_warning.suggestion = suggestion
                existing_warning.metrics = metrics
                existing_warning.created_at = datetime.now()
                # 注意：这里直接修改，依赖于最后的批量保存
            return None # 无需创建新对象
        else:
            # 创建新预警对象
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
