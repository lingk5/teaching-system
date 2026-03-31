from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, case
from ..models import db, Student, Class
from ..models.data import Attendance, Homework, Quiz, Interaction
from ..services.warning_engine import WarningEngine
from ..services.weight_config import WeightConfig
from ..utils.permissions import (
    can_access_course,
    can_access_class,
    can_access_student,
    course_id_for_student,
)

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/course/<int:course_id>/overview')
@jwt_required()
def course_overview(course_id):
    """课程概览数据"""
    if not can_access_course(course_id):
        return jsonify({'success': False, 'message': '无权访问该课程'}), 403
    class_id = request.args.get('class_id', type=int)
    if class_id:
        if not can_access_class(class_id):
            return jsonify({'success': False, 'message': '无权访问该班级'}), 403
        target_class = Class.query.filter_by(id=class_id, course_id=course_id).first()
        if not target_class:
            return jsonify({'success': False, 'message': '班级不属于该课程'}), 403
        classes = [target_class]
    else:
        classes = Class.query.filter_by(course_id=course_id).all()

    # 1. 基础统计
    class_ids = [c.id for c in classes]
    students = Student.query.filter(Student.class_id.in_(class_ids)).all()
    student_ids = [s.id for s in students]

    if not student_ids:
        return jsonify({
            'success': True,
            'data': {
                'student_count': 0,
                'attendance_rate': 0,
                'homework_completion': 0,
                'avg_quiz_score': 0,
                'score_distribution': [0, 0, 0, 0, 0],
                'class_profile': [],
                'trend': {'labels': [], 'class_avg': [], 'grade_avg': []},
                'student_ranking': []
            }
        })

    # 计算出勤率
    total_attendance = Attendance.query.filter(Attendance.student_id.in_(student_ids), Attendance.course_id == course_id).count()
    present_count = Attendance.query.filter(Attendance.student_id.in_(student_ids), Attendance.status == 'present', Attendance.course_id == course_id).count()
    attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0

    # 计算作业完成率
    total_homework = Homework.query.filter(Homework.student_id.in_(student_ids), Homework.course_id == course_id).count()
    completed_homework = Homework.query.filter(Homework.student_id.in_(student_ids), Homework.status.in_(['submitted', 'graded']), Homework.course_id == course_id).count()
    homework_completion = (completed_homework / total_homework * 100) if total_homework > 0 else 0

    # 计算平均测验分
    avg_quiz_score = db.session.query(func.avg(Quiz.score)).filter(Quiz.student_id.in_(student_ids), Quiz.course_id == course_id).scalar() or 0

    engine = WarningEngine(course_id)
    student_rows = []
    for student in students:
        metrics = engine._calculate_metrics(student.id)
        score_details = WeightConfig.calculate_score_details(metrics)
        student_rows.append({
            'student': student,
            'metrics': metrics,
            'score_details': score_details,
        })

    score_distribution = [0, 0, 0, 0, 0]
    for row in student_rows:
        score = row['score_details']['comprehensive_score']
        if score >= 90:
            score_distribution[0] += 1
        elif score >= 80:
            score_distribution[1] += 1
        elif score >= 70:
            score_distribution[2] += 1
        elif score >= 60:
            score_distribution[3] += 1
        else:
            score_distribution[4] += 1

    class_profile = []
    for key in ('attendance', 'homework', 'quiz', 'interaction'):
        values = [
            row['metrics'][key]
            for row in student_rows
            if row['metrics'][key] is not None
        ]
        if values:
            class_profile.append(round(sum(values) / len(values), 1))

    # 4. 学习趋势 (最近5次测验的平均分)
    recent_quizzes = db.session.query(
        Quiz.title, func.avg(Quiz.score), func.max(Quiz.created_at).label('latest_date')
    ).filter(
        Quiz.student_id.in_(student_ids), Quiz.course_id == course_id
    ).group_by(Quiz.title).order_by(func.max(Quiz.created_at).desc()).limit(5).all()
    
    trend_labels = [q[0] for q in recent_quizzes]
    trend_data = [round(q[1], 1) for q in recent_quizzes]

    ranking_rows = sorted(
        student_rows,
        key=lambda row: row['score_details']['comprehensive_score'],
        reverse=True,
    )[:10]
    student_ranking = [{
        'id': row['student'].id,
        'student_no': row['student'].student_no,
        'name': row['student'].name,
        'score': round(row['score_details']['comprehensive_score'], 1),
        'class_name': row['student'].class_.name if row['student'].class_ else '',
        'coverage': row['score_details']['coverage'],
    } for row in ranking_rows]

    return jsonify({
        'success': True,
        'data': {
            'student_count': len(students),
            'attendance_rate': round(attendance_rate, 1),
            'homework_completion': round(homework_completion, 1),
            'avg_quiz_score': round(float(avg_quiz_score), 1),
            'score_distribution': score_distribution,
            'class_profile': class_profile,
            'trend': {
                'labels': trend_labels,
                'class_avg': trend_data,
                'grade_avg': []
            },
            'student_ranking': student_ranking
        }
    })

@analytics_bp.route('/course/<int:course_id>/students/<int:student_id>/profile')
@jwt_required()
def student_profile(course_id, student_id):
    """学生个人学习档案"""
    if not can_access_course(course_id) or not can_access_student(student_id):
        return jsonify({'success': False, 'message': '无权访问该学生档案'}), 403
    if course_id_for_student(student_id) != course_id:
        return jsonify({'success': False, 'message': '学生不属于该课程'}), 403

    student = Student.query.get_or_404(student_id)
    
    # 重新使用 WarningEngine 计算该生的实时指标
    engine = WarningEngine(course_id)
    metrics = engine._calculate_metrics(student.id)
    score_details = WeightConfig.calculate_score_details(metrics)

    # 趋势数据
    quizzes = Quiz.query.filter_by(student_id=student.id, course_id=course_id).order_by(Quiz.created_at).limit(10).all()
    trend_labels = [q.title for q in quizzes]
    trend_scores = [q.score for q in quizzes]

    return jsonify({
        'success': True,
        'data': {
            'student': {
                'name': student.name,
                'student_no': student.student_no,
                'class_name': student.class_.name if student.class_ else '',
                'score': round(score_details['comprehensive_score'], 1)
            },
            'metrics': {
                'attendance': round(metrics['attendance'], 1) if metrics['attendance'] is not None else None,
                'homework': round(metrics['homework'], 1) if metrics['homework'] is not None else None,
                'quiz': round(metrics['quiz'], 1) if metrics['quiz'] is not None else None,
                'interaction': round(metrics['interaction'], 1) if metrics['interaction'] is not None else None,
            },
            'coverage': score_details['coverage'],
            'trend': {
                'labels': trend_labels,
                'scores': trend_scores
            }
        }
    })
